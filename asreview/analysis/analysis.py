# Copyright 2019 The ASReview Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Analysis of log files.
'''

import itertools
import os
import numpy as np
from scipy import stats

from asreview.logging.utils import loggers_from_dir
from asreview.analysis.statistics import _get_labeled_order
from asreview.analysis.statistics import _get_limits
from asreview.analysis.statistics import _find_inclusions
from asreview.analysis.statistics import _get_last_proba_order


class Analysis():
    """ Analysis object to do statistical analysis on log files. """
    def __init__(self, loggers, key=None):
        """
        Arguments
        ---------
        loggers: list, BaseLogger
            Either a list of loggers (opened files) or a single logger.
        key: str
            Give a name to the analysis.
        """
        if isinstance(loggers, list):
            loggers = {i: logger for i, logger in enumerate(loggers)}

        # Sometimes an extra dataset is present in the log_file(s).
        # These signify not the labels on which the model was trained, but the
        # ones that were included in the end (or some other intermediate step.
        self.final_labels = None
        self.labels = None
        self.empty = True

        self.key = key
        self.loggers = loggers
        self.num_runs = len(self.loggers)
        if self.num_runs == 0:
            return

        self._first_file = list(self.loggers.keys())[0]
        self.labels = self.loggers[self._first_file].get('labels')
        try:
            self.final_labels = self.loggers[self._first_file].get(
                'final_labels')
        except KeyError:
            pass
        self.empty = False
        self.inc_found = {}

    @classmethod
    def from_dir(cls, data_dir):
        """Create an Analysis object from a directory."""
        key = os.path.basename(os.path.normpath(data_dir))
        loggers = loggers_from_dir(data_dir)
        analysis_inst = Analysis(loggers, key=key)
        if analysis_inst.empty:
            return None

        analysis_inst.data_dir = data_dir
        return analysis_inst

    def inclusions_found(self, result_format="fraction", final_labels=False,
                         **kwargs):
        """Get the number of inclusions at each point in time.

        Caching is used to prevent multiple calls being expensive.

        Arguments
        ---------
        result_format: str
            The format % or # of the returned values.
        final_labels: bool
            If true, use the final_labels instead of labels for analysis.

        Returns
        -------
        tuple:
            Three numpy arrays with x, y, error_bar.
        """
        if final_labels:
            labels = self.final_labels
        else:
            labels = self.labels

        fl = final_labels
        if fl not in self.inc_found:
            # Compute the comclusions if not found in cache.
            self.inc_found[fl] = {}
            avg, err, iai, ninit = self._get_inc_found(**kwargs, labels=labels)
            self.inc_found[fl]["avg"] = avg
            self.inc_found[fl]["err"] = err
            self.inc_found[fl]["inc_after_init"] = iai
            self.inc_found[fl]["n_initial"] = ninit
        dx = 0
        dy = 0
        x_norm = len(labels)-self.inc_found[fl]["n_initial"]
        y_norm = self.inc_found[fl]["inc_after_init"]

        if result_format == "percentage":
            x_norm /= 100
            y_norm /= 100
        elif result_format == "number":
            x_norm /= len(labels)
            y_norm /= self.inc_found[fl]["inc_after_init"]

        norm_xr = (np.arange(len(self.inc_found[fl]["avg"]))-dx)/x_norm
        norm_yr = (np.array(self.inc_found[fl]["avg"])-dy)/y_norm
        norm_y_err = np.array(self.inc_found[fl]["err"])/y_norm

        return norm_xr, norm_yr, norm_y_err

    def _get_inc_found(self, labels=False):
        """Get the number of inclusions (without formatting)."""
        inclusions_found = []

        for logger in self.loggers.values():
            inclusions, inc_after_init, n_initial = _find_inclusions(
                logger, labels)
            inclusions_found.append(inclusions)

        inc_found_avg = []
        inc_found_err = []
        for i_instance in itertools.count():
            cur_vals = []
            for i_file in range(self.num_runs):
                try:
                    cur_vals.append(inclusions_found[i_file][i_instance])
                except IndexError:
                    pass
            if len(cur_vals) == 0:
                break
            if len(cur_vals) == 1:
                err = cur_vals[0]
            else:
                err = stats.sem(cur_vals)
            avg = np.mean(cur_vals)
            inc_found_avg.append(avg)
            inc_found_err.append(err)

        if self.num_runs == 1:
            inc_found_err = np.zeros(len(inc_found_err))

        return inc_found_avg, inc_found_err, inc_after_init, n_initial

    def wss(self, val=100, x_format="percentage", **kwargs):
        """Get the WSS (Work Saved Sampled) value.

        Arguments
        ---------
        val:
            At which recall, between 0 and 100.
        x_format:
            Format for position of WSS value in graph.

        Returns
        -------
        tuple:
            Tuple consisting of WSS value, x_positions, y_positions of WSS bar.
        """
        norm_xr, norm_yr, _ = self.inclusions_found(
            result_format="percentage", **kwargs)

        if x_format == "number":
            x_return, y_result, _ = self.inclusions_found(
                result_format="number", **kwargs)
            y_max = self.inc_found[False]["inc_after_init"]
            y_coef = y_max/(len(self.labels) -
                            self.inc_found[False]["n_initial"])
        else:
            x_return = norm_xr
            y_result = norm_yr
            y_max = 1.0
            y_coef = 1.0

        for i in range(len(norm_yr)):
            if norm_yr[i] >= val - 1e-6:
                return (norm_yr[i] - norm_xr[i],
                        (x_return[i], x_return[i]),
                        (x_return[i]*y_coef, y_result[i]))
        return (None, None, None)

    def rrf(self, val=10, x_format="percentage", **kwargs):
        """Get the RRF (Relevant References Found).

        Arguments
        ---------
        val:
            At which recall, between 0 and 100.
        x_format:
            Format for position of RRF value in graph.

        Returns
        -------
        tuple:
            Tuple consisting of RRF value, x_positions, y_positions of RRF bar.

        """
        norm_xr, norm_yr, _ = self.inclusions_found(
            result_format="percentage", **kwargs)

        if x_format == "number":
            x_return, y_return, _ = self.inclusions_found(
                result_format="number", **kwargs)
        else:
            x_return = norm_xr
            y_return = norm_yr

        for i in range(len(norm_yr)):
            if norm_xr[i] >= val - 1e-6:
                return (norm_yr[i],
                        (x_return[i], x_return[i]),
                        (0, y_return[i]))
        return None

    def avg_time_to_discovery(self):
        """Get the best/last estimate on how long it takes to find a paper.

        Returns
        -------
        dict:
            For each inclusion, key=paper_id, value=avg time.
        """
        labels = self.labels

        one_labels = np.where(labels == 1)[0]
        time_results = {label: [] for label in one_labels}
        n_initial = []

        for i_file, logger in enumerate(self.loggers.values()):
            label_order, n = _get_labeled_order(logger)
            proba_order = _get_last_proba_order(logger)
            n_initial.append(n)

            for i_time, idx in enumerate(label_order):
                if labels[idx] == 1:
                    time_results[idx].append(i_time)

            for i_time, idx in enumerate(proba_order):
                if labels[idx] == 1 and len(time_results[idx]) <= i_file:
                    time_results[idx].append(i_time + len(label_order))

            for idx in time_results:
                if len(time_results[idx]) <= i_file:
                    time_results[idx].append(
                        len(label_order) + len(proba_order))

        results = {}
        for label in time_results:
            trained_time = []
            for i_file, time in enumerate(time_results[label]):
                if time >= n_initial[i_file]:
                    trained_time.append(time)
            if len(trained_time) == 0:
                results[label] = 0
            else:
                results[label] = np.average(trained_time)
        return results

    def limits(self, prob_allow_miss=[0.1]):
        """For each query, compute the number of papers for a criterium.

        A criterium is the average number of papers missed. For example,
        with 0.1, the criterium is that after reading x papers, there is
        (about) a 10% chance that one paper is not included. Another example,
        with 2.0, there are on average 2 papers missed after reading x papers.
        The value for x is returned for each query and probability by the
        function.

        Arguments
        ---------
        prob_allow_miss: list, float
            Sets the criterium for how many papers can be missed.

        returns
        -------
        dict:
            One entry, "x_range" with the number of papers read.
            List, "limits" of results for each probability and
            at # papers read.
        """
        if not isinstance(prob_allow_miss, list):
            prob_allow_miss = [prob_allow_miss]
        logger = self.loggers[self._first_file]
        n_queries = logger.n_queries()
        results = {
            "x_range": [],
            "limits": [[] for _ in range(len(prob_allow_miss))],
        }

        n_train = 0
        for query_i in range(n_queries):
            new_limits = _get_limits(self.loggers, query_i, self.labels,
                                     proba_allow_miss=prob_allow_miss)

            try:
                new_train_idx = logger.get("train_idx", query_i)
            except KeyError:
                new_train_idx = None

            if new_train_idx is not None:
                n_train = len(new_train_idx)

            if new_limits is not None:
                results["x_range"].append(n_train)
                for i_prob in range(len(prob_allow_miss)):
                    results["limits"][i_prob].append(new_limits[i_prob])

        results["x_range"] = np.array(results["x_range"], dtype=np.int)
        for i_prob in range(len(prob_allow_miss)):
            results["limits"][i_prob] = np.array(
                results["limits"][i_prob], np.int)
        return results

    def close(self):
        "Close loggers."
        for logger in self.loggers.values():
            logger.close()

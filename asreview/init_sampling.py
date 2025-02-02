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

"""Initial sample.

This module is used to draw an initial sample. This sample is the
so-called 'pre-knowledge' of the researcher.
"""
import numpy as np


def sample_prior_knowledge(
        labels, n_prior_included=10,
        n_prior_excluded=10, random_state=None):
    """Function to sample prelabelled articles.

    Arguments
    ---------
    labels: np.ndarray
        Labels in a 2d numpy array (the result of
        keras.utils.to_categorical).
    n_included: int
        The number of positive labels.
    n_excluded: int
        The number of negative labels.
    random_state : int, RandomState instance or None, optional (default=None)
        If int, random_state is the seed used by the random number generator;
        If RandomState instance, random_state is the random number generator;
        If None, the random number generator is the RandomState instance used
        by `np.random`.

    Returns
    -------
    np.ndarray:
        An array with n_included and n_excluded indices.

    """

    # set random state
    r = np.random.RandomState(random_state)

    # retrieve the index of included and excluded papers
    included_indexes = np.where(labels == 1)[0]
    excluded_indexes = np.where(labels == 0)[0]

    if len(included_indexes) < n_prior_included:
        print(f"Found only {len(included_indexes)}, "
              f"when I need {n_prior_included}.")
    # select randomly from included and excluded papers
    included_indexes_sample = r.choice(
        included_indexes, n_prior_included, replace=False)
    excluded_indexes_sample = r.choice(
        excluded_indexes, n_prior_excluded, replace=False)

    init = np.append(included_indexes_sample, excluded_indexes_sample)

    return init

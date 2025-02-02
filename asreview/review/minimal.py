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

import numpy as np

from asreview.review import BaseReview


class MinimalReview(BaseReview):
    """ Minimal review class, can be used to do reviewing in a granularly. """

    def __init__(self, *args, **kwargs):
        super(MinimalReview, self).__init__(*args, **kwargs)

    def _prior_knowledge(self):
        return np.array([], dtype=np.int), np.array([], dtype=np.int)

    def _get_labels(self, ind):
        raise NotImplementedError

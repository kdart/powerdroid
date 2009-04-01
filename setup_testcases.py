#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab

# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os

os.umask(022)

from distutils.core import setup
from glob import glob

setup(name="droid_testcases",
    version="0.10",
    url="http://psyche.corp.google.com/",
    maintainer="Keith Dart",
    maintainer_email="dart@google.com",
    description="Android lab automation test cases.",
    package_dir = {'': 'src'},
    packages = [
        "testcases",
        "testcases.android",
        "testcases.android.measure",
        "testcases.android.radio",
        "testcases.android.battery",
        "testcases.currentdraw",
        ],
    package_data = {
        'testcases': ['*.conf'],
        'testcases.android': ['*.conf'],
        'testcases.android.measure': ['*.conf'],
        'testcases.android.radio': ['*.conf'],
        'testcases.android.battery': ['*.conf'],
        'testcases.currentdraw': ['*.conf'],
        },
)


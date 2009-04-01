#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
# 

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


"""Same as Python's stock random module, except use better system entropy
source.
"""

__author__ = 'dart@google.com (Keith Dart)' # Takes the blame for this.

from random import SystemRandom

_inst = SystemRandom()

# integer functions
getrandbits = _inst.getrandbits
randint = _inst.randint
randrange = _inst.randrange
# sequence functions
choice = _inst.choice
sample = _inst.sample
shuffle = _inst.shuffle
# generator functions
random = _inst.random
uniform = _inst.uniform
normalvariate = _inst.normalvariate
lognormvariate = _inst.lognormvariate
expovariate = _inst.expovariate
vonmisesvariate = _inst.vonmisesvariate
gammavariate = _inst.gammavariate
gauss = _inst.gauss
betavariate = _inst.betavariate
paretovariate = _inst.paretovariate
weibullvariate = _inst.weibullvariate

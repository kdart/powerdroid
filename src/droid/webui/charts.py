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



"""Plotting handlers.

"""

__author__ = 'dart@google.com (Keith Dart)'


import os
import glob

from pycopia.WWW import json


HOSTNAME = os.uname()[1]

def testing(*args, **kwargs):
  return args, kwargs

def listing():
  return glob.glob("/var/www/%s/media/images/charts/*.png" % HOSTNAME)

def powerprofile():
  pass


_EXPORTED = [testing, listing]

handler = json.JSONDispatcher(_EXPORTED)

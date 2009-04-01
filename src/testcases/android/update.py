#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab

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


#
# The docstring headings map to testcase fields, so the names should not
# be changed.


"""Update the device.

This module just provides a suite with the DeviceUpdate test case added.
"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"


from droid.qa import core

from testcases.android import common


def GetSuite(conf):
  # create the suite with the passed-in configuration object.
  suite = core.TestSuite(conf)
  suite.addTest(common.DeviceUpdate)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


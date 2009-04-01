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


# Copyright Google Inc. All Rights Reserved.
#

"""Droid reporting interface.

"""

__author__ = 'dart@google.com (Keith Dart)'



class Report(object):
  """Abstrace base class for measurement reporting."""

  def __init__(self, **kwargs):
    self.Initialize(**kwargs)

  def close(self):
    pass

  def fileno(self):
    return None

  def Initialize(self, **kwargs):
    pass

  def Finalize(self, **kwargs):
    pass

  def SetColumns(self, *args):
    """Sets the column headings."""
    raise NotImplementedError

  def WriteRecord(self, *args):
    """Write a record from objects."""
    raise NotImplementedError

  def WriteTextRecord(self, *args):
    """Write a record where all arguments are strings (faster)."""
    raise NotImplementedError

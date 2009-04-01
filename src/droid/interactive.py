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



"""Functions to make interactive demos easier. Use with ipython/pylab like
this:

from droid.interactive import *
"""

__author__ = 'dart@google.com (Keith Dart)'


from droid.analyze import *
import pylab


def Plot(filename, timemarkstring="0s,5d", ylim=None, columns=1):
  """Plot from ipython."""
  timemarks = TimeMarksGenerator(timemarkstring)
  MakeCharts(filename, timemarks, interactive=True, ylim=ylim,
      columns=columns)

def Histogram(filename, columns=None):
  """Histogram from data."""
  PlotHistogram(filename, interactive=True, columns=columns)

def Clear():
  pylab.cla()



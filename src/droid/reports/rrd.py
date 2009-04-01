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


# Copyright 2006 Google Inc. All Rights Reserved.
#

"""Reports that generate RRD databases.

"""

__author__ = 'dart@google.com (Keith Dart)'


import os
import time

import rrdtool
from pycopia.textutils import identifier

from droid.reports import Report

class RRDReport(Report):

  def Initialize(self, filename=None, interval=1, **kwargs):
    if filename:
      self._filename = filename + ".rrd"
      self._interval = str(interval)
      self._doclose = False
    else:
      raise ValueError("Must supply filename parameters.")

  def Finalize(self):
    self.RRDGraph()

  def SetColumns(self, *args):
    dsargs = [
      ("DS:%s:GAUGE:2:-20:500" % identifier(name)[:19]) for name in args[1:]]
    rraargs = [
      "RRA:LAST:0:1:3600",
      "RRA:AVERAGE:0.1:3600:24",
      "RRA:MIN:0.2:3600:24",
      "RRA:MAX:0.2:3600:24",
      ]
    rrdtool.create(self._filename, "--start", str(long(time.time())),
        "--step", self._interval, *tuple(dsargs + rraargs))

  def WriteRecord(self, *args):
    rrdtool.update(self._filename, ":".join(map(repr, args)))

  def RRDGraph(self):
    lasttime = rrdtool.last(self._filename)
    gfilename = os.path.splitext(self._filename)[0] + ".png"
    rrdtool.graph(gfilename,
      '--imgformat', 'PNG', '--width', '1024', '--height', '480',
      '--end', str(lasttime), '--start', 'end-500s', 
      '-u', '500', '-l', '-20', 
      'DEF:avg=%s:Current__ma_:LAST' % self._filename,
      'DEF:low=%s:Low__ma_:LAST' % self._filename,
      'DEF:high=%s:High__ma_:LAST' % self._filename,
      'DEF:maxi=%s:Maximum__ma_:LAST' % self._filename,
      'DEF:mini=%s:Minimum__ma_:LAST' % self._filename,
      'LINE:mini#88000033',
      'LINE:low#FF000044', 
      'LINE:avg#0000FF', 
      'LINE:high#00FF0044',
      'LINE:maxi#00880033')



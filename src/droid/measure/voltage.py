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



"""Measurers for voltage.
"""

__author__ = 'dart@google.com (Keith Dart)'

import sys
import time

from droid.measure import core
from droid.reports import flatfile


class VoltageMeasurer(core.BaseMeasurer):
  def __init__(self, ctx):
    self._device = ctx.environment.voltmeter
    self.measuretime = self._device.Prepare(ctx)

  def Initialize(self, ctx):
    self.datafile = flatfile.GetReport(ctx.datafiles.name, "G")
    headings = ("timestamp (s)",) + self._device.GetVoltageHeadings()
    self.datafile.SetColumns(*headings)

  def Finalize(self):
    df = self.datafile
    del self.datafile
    name = df.name
    df.Finalize()
    df.close()
    return name

  def __call__(self, timestamp, oldvalue):
    val = self._device.MeasureDCVoltage()
    self.datafile.WriteRecord(timestamp, val.value)
    return val




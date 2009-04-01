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



"""Current (I) measurers.
"""

import sys
import time

from pycopia import scheduler

from droid.measure import core
from droid.reports import flatfile


class SpecialCurrentMeasurer(core.OldMeasurer):

  def _Setup(self):
    inst = self._device
    ctx = self._context
    inst.clear()
    inst.write('SENS:FUNC "CURR"')
    inst.write('SENS:CURR:RANG 3.0; DET ACDC')
    inst.write("SENS:SWE:POIN %s" % ctx.samples)
    inst.write("SENS:SWE:TINT %.2E" % ctx.interval)
    if ctx.triggered:
      trigctx = ctx.trigger
      inst.write("SENS:SWE:OFFS:POIN %d" % trigctx.offsetpoint)
      inst.write("TRIG:ACQ:SOUR INT")
      inst.write("TRIG:ACQ:COUN:CURR %d" % trigctx.count)
      inst.write("TRIG:ACQ:SLOP:CURR %s" % trigctx.slope)
      inst.write("TRIG:ACQ:LEV:CURR %.2E" % trigctx.level)
      inst.write("TRIG:ACQ:HYST:CURR %.2E" % trigctx.hysteresis)

  def Single(self):
    inst = self._device
    report = self._report
    ctx = self._context
    self._Setup()
    if ctx.triggered:
      ot = inst.timeout
      inst.timeout = inst.T300s
      inst.write("INIT:IMM:NAME ACQ")
      curr = inst.FetchACDCCurrent()
      inst.timeout = ot
    else:
      curr = inst.MeasureACDCCurrent()
    report.WriteRecord(curr)
    return curr

  def Raw(self, N, timeout=0.0):
    """Fetch raw sample data points. """
    report = self._report
    inst = self._device
    ctx = self._context
    interval = ctx.interval
    report.SetColumns("timestamp (s)", "Current (A)")
    self._Setup()
    old_timeout = inst.timeout
    try:
      if ctx.triggered:
        inst.timeout = inst.T300s
        inst.write("INIT:IMM:NAME ACQ")
        inst.write("FETC:ARR:CURR?")
        timestamp = time.time()
        array = inst.read_values()
        for samp in array:
          report.WriteRecord(timestamp, samp)
          timestamp += interval
      else:
        inst.timeout = inst.T30s
        for i in xrange(N):
          timestamp = time.time()
          curr = inst.MeasureACDCCurrent()
          inst.write("FETC:ARR:CURR?")
          array = inst.read_values()
          for samp in array:
            report.WriteRecord(timestamp, samp)
            timestamp += interval
    finally:
      inst.timeout = old_timeout

  def Triggered(self, N, timeout=0.0):
    report = self._report
    inst = self._device


class PowerCurrentMeasurer(core.BaseMeasurer):

  def __init__(self, ctx):
    if ctx.datafiles.name:
      ctx.datafiles.name = "%s-%s-%s" % (ctx.datafiles.name,
          ctx.powersupplies.subsamples,
          int(ctx.powersupplies.voltage * 100))
    self._device = ctx.environment.powersupply
    self.measuretime = self._device.Prepare(ctx)

  def Initialize(self, ctx):
    assert ctx.powersupplies.voltage < 5.0 # we don't want to "smoke" the DUT.
    self.datafile = flatfile.GetReport(ctx.datafiles.name, "G")
    instrument = self._device
    self._chargerstate = instrument.GetChargerOutputState()
    instrument.SetChargerOutputState(False)
    instrument.write('SENS:FUNC "CURR"')
    instrument.write('SENS:CURR:RANG 3.0; DET ACDC')
    instrument.write("SENS:SWE:POIN %s" % ctx.powersupplies.subsamples)
    instrument.write("SENS:SWE:TINT %.2E" % ctx.powersupplies.subsampleinterval)
    headings = ("timestamp (s)",) + self._device.GetAllCurrentTextHeadings()
    self.datafile.SetColumns(*headings)

  def Finalize(self):
    self._device.SetChargerOutputState(self._chargerstate)
    df = self.datafile
    del self.datafile
    df.Finalize()
    df.close()

  def __call__(self, timestamp, oldvalue):
    rec = [repr(timestamp)]
    rec.extend(self._device.MeasureAllCurrentAsText())
    self.datafile.WriteTextRecord(*rec)
    return rec[1]



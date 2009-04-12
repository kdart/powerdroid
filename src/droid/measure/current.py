#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Current (I) measurers.
"""

import time

from droid.measure import core
from droid.reports import core as reportcore


class SpecialCurrentMeasurer(core.OldMeasurer):

  def _Setup(self):
    inst = self._device
    ctx = self._context
    inst.clear()
    inst.write('SENS:FUNC "CURR"')
    inst.write('SENS:CURR:RANG %.2E; DET ACDC' % ctx.maxcurrent)
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
    super(PowerCurrentMeasurer, self).__init__(ctx)
    self._device = ctx.environment.powersupply
    self.measuretime = self._device.Prepare(ctx)
    self.datafile = reportcore.GetDatafile(ctx)

  def Initialize(self):
    instrument = self._device
    instrument.write('SENS:FUNC "CURR"')
    self.datafile.Initialize()
    headings = ("timestamp (s)",) + instrument.GetAllCurrentTextHeadings()
    self.datafile.SetColumns(*headings)

  def Finalize(self):
    self.datafile.Finalize()

  def __call__(self, timestamp, oldvalue):
    rec = [repr(timestamp)]
    rec.extend(self._device.MeasureAllCurrentAsText())
    self.datafile.WriteTextRecord(*rec)
    return rec[1]


class PowerSupplyChargeCurrentMeasurer(core.BaseMeasurer):

  def __init__(self, ctx):
    super(PowerSupplyChargeCurrentMeasurer, self).__init__(ctx)
    self._device = ctx.environment.powersupply
    ctx.powersupplies.voltage = 0.0
    ctx.powersupplies.detector = "DC"
    self.measuretime = self._device.Prepare(ctx)
    self.datafile = reportcore.GetDatafile(ctx)

  def Initialize(self):
    instrument = self._device
    instrument.write('SENS:FUNC "CURR"')
    self.datafile.Initialize()
    headings = ("timestamp (s)",) + instrument.GetAllCurrentTextHeadings()
    self.datafile.SetColumns(*headings)

  def Finalize(self):
    self.datafile.Finalize()

  def __call__(self, timestamp, oldvalue):
    rec = [repr(timestamp)]
    rec.extend(self._device.MeasureAllDCCurrentAsText())
    self.datafile.WriteTextRecord(*rec)
    return rec[1]


class PowerVoltageMeasurer(core.BaseMeasurer):

  def __init__(self, ctx):
    super(PowerVoltageMeasurer, self).__init__(ctx)
    self._device = ctx.environment.powersupply
    self.datafile = reportcore.GetDatafile(ctx)

  def Initialize(self):
    instrument = self._device
    #instrument.write('SENS:FUNC "VOLT"')
    self.datafile.Initialize()
    headings = ("timestamp (s)",) + instrument.GetVoltageHeadings()
    self.datafile.SetColumns(*headings)

  def Finalize(self):
    self.datafile.Finalize()

  def __call__(self, timestamp, oldvalue):
    value = self._device.MeasureDCVoltage().value
    self.datafile.WriteRecord(timestamp, value)
    return value


class CurrentMeasurer(core.BaseMeasurer):

  def __init__(self, ctx):
    super(CurrentMeasurer, self).__init__(ctx)
    self._device = ctx.environment.currentmeter
    self.measuretime = self._device.Prepare(ctx)
    self.datafile = reportcore.GetDatafile(ctx)

  def Initialize(self):
    instrument = self._device
    self.datafile.Initialize()
    headings = ("timestamp (s)",) + instrument.GetCurrentHeadings()
    self.datafile.SetColumns(*headings)

  def Finalize(self):
    self.datafile.Finalize()

  def __call__(self, timestamp, oldvalue):
    value = self._device.MeasureDCCurrent().value
    self.datafile.WriteRecord(timestamp, value)
    return value


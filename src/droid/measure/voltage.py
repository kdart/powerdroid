#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Measurers for voltage.
"""

__author__ = 'dart@google.com (Keith Dart)'

import sys
import time

from droid.measure import core
from droid.reports import core as reportcore


class VoltageMeasurer(core.BaseMeasurer):
  def __init__(self, ctx):
    super(VoltageMeasurer, self).__init__(ctx)
    self._device = ctx.environment.voltmeter
    self.measuretime = self._device.Prepare(ctx)
    self.datafile = reportcore.GetDatafile(ctx)

  def Initialize(self):
    instrument = self._device
    self.datafile.Initialize()
    headings = ("timestamp (s)",) + instrument.GetVoltageHeadings()
    self.datafile.SetColumns(*headings)

  def Finalize(self):
    self.datafile.Finalize()

  def __call__(self, timestamp, oldvalue):
    val = self._device.MeasureDCVoltage().value
    self.datafile.WriteRecord(timestamp, val)
    return val




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



"""Measure battery run-down. Measures both current and voltage using a
special appuratus attached to the Agilent power supply. That jig must be
attached and the battery fully charged before running this measurement.

"""

__author__ = 'dart@google.com (Keith Dart)'

import time

from pycopia import scheduler

from droid.measure import core



class BatteryRundownMeasurer(object):
  """Measure the discharge of a real battery. Record current and voltage.
  """
  def __init__(self, ctx):
    ctx.voltage = 0.0 # we don't want to "smoke" the power supply.
    self._context = ctx
    self._device = ctx.device
    self._creport = ctx.reports[0]
    self._vreport = ctx.reports[1]

  def Setup(self):
    inst = self._device
    ctx = self._context
    inst.clear()
    measuretime = inst.Prepare(ctx)
    if measuretime > 0.125:
      raise core.AbortMeasurements, "measurement longer than time slice"

    headings = ("timestamp (s)",) + inst.GetVoltageHeadings()
    self._vreport.SetColumns(*headings)
    headings = ("timestamp (s)",) + inst.GetAllCurrentTextHeadings()
    self._creport.SetColumns(*headings)

    inst.write('SENS:FUNC "CURR"')
    inst.write('SENS:CURR:RANG 3.0; DET ACDC')
    inst.write("SENS:SWE:POIN %s" % ctx.subsamples)
    inst.write("SENS:SWE:TINT %.2E" % ctx.subsampleinterval)

    mc = core.MeasurementController()
    mc.AddMeasurement(self._MeasureCurrent, 1)
    mc.AddMeasurement(self._MeasureVoltage, 256)
    mc.AddMeasurement(core.StopMeasurements, int(ctx.timespan * 8))
    inst.ChargerOff()
    return mc

  def Teardown(self):
    self._creport.Finalize()
    self._creport.close()
    self._vreport.Finalize()
    self._vreport.close()

  def _MeasureCurrent(self, t):
    rec = self._device.MeasureAllCurrentAsText()
    self._creport.WriteTextRecord(repr(t), *rec)

  def _MeasureVoltage(self, t):
    val = self._device.MeasureDVMDCVoltage()
    self._vreport.WriteRecord(t, val)

  def Run(self):
    controller = self.Setup()
    self._MeasureVoltage(time.time())
    try:
      try:
        controller.Run()
      except core.AbortMeasurements:
        pass
    finally:
      controller.close()
      self.Teardown()


class BatteryChargeMeasurer(object):
  """Measure the recharge of a battery.
  """
  def __init__(self, ctx):
    ctx.voltage = 0.0 # we don't want to "smoke" the power supply.
    self._context = ctx
    self._device = ctx.device
    self._creport = ctx.reports[0]
    self._vreport = ctx.reports[1]

  def Setup(self):
    inst = self._device
    ctx = self._context
    inst.clear()
    measuretime = inst.Prepare(ctx)
    if measuretime > 0.125:
      raise core.AbortMeasurements, "measurement longer than time slice"

    headings = ("timestamp (s)",) + inst.GetVoltageHeadings()
    self._vreport.SetColumns(*headings)
    headings = ("timestamp (s)", inst.GetAllCurrentHeadings()[0])
    self._creport.SetColumns(*headings)

    inst.write('SENS:FUNC "CURR"')
    inst.write('SENS:CURR:RANG 3.0; DET DC')
    inst.write("SENS:SWE:POIN %s" % ctx.samples)
    inst.write("SENS:SWE:TINT %.2E" % ctx.interval)

    mc = core.MeasurementController()
    mc.AddMeasurement(self._MeasureCurrent, 1)
    mc.AddMeasurement(self._MeasureVoltage, 256)
    mc.AddMeasurement(core.StopMeasurements, int(ctx.timespan * 8))
    inst.ChargerOn()
    return mc

  def Teardown(self):
    self._creport.Finalize()
    self._creport.close()
    self._vreport.Finalize()
    self._vreport.close()

  def _MeasureCurrent(self, t):
    val = self._device.MeasureDCCurrent()
    self._creport.WriteRecord(t, val)

  def _MeasureVoltage(self, t):
    val = self._device.MeasureDVMDCVoltage()
    self._vreport.WriteRecord(t, val)

  def Run(self):
    controller = self.Setup()
    self._MeasureVoltage(time.time())
    try:
      try:
        controller.Run()
      except core.AbortMeasurements:
        pass
    finally:
      controller.close()
      self.Teardown()



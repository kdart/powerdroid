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



"""Interfaces to multimeters.

"""

__author__ = 'dart@google.com (Keith Dart)'


from droid.instruments import core
from droid.instruments import serial

# measurment modes

AAC = "AAC"      # AC current
AACDC = "AACDC"  # AC plus DC rms current.
ADC = "ADC"      # DC current
CONT = "CONT"    # Continuity test.
DIODE = "DIODE"  # Diode test
FREQ = "FREQ"    # Frequency
OHMS = "OHMS"    # Resistance
VAC = "VAC"      # AC volts
VACDC = "VACDC"  # AC plus DC rms volts. Available in the primary display only.
VDC = "VDC"      # DC volts


class Fluke45(serial.SerialInstrument):

  def Initialize(self, devspec, **kwargs):
    self._exp._fo.stty("-crtscts") # No flow control lines on Fluke interface.
    self.clear()
    self.GetMode()
    self.write("RATE M")

  def SetMode(self, mode):
    if mode != self._mode:
      self.write(mode)
      self._mode = mode

  def GetMode(self):
    mode =  self.ask("FUNC1?")
    self._mode = mode
    return mode

  def GetVoltageHeadings(self):
    return ("Voltage (V)",)

  def MeasureDCVoltage(self):
    self.SetMode(VDC)
    return core.GetUnit(self.ask("MEAS?"), "V")

  def MeasureACDCVoltage(self):
    self.SetMode(VACDC)
    return core.GetUnit(self.ask("MEAS?"), "V")

  def MeasureACVoltage(self):
    self.SetMode(VAC)
    return core.GetUnit(self.ask("MEAS?"), "V")

  def MeasureDCCurrent(self):
    self.SetMode(ADC)
    return core.GetUnit(self.ask("MEAS?"), "A")

  def MeasureACCurrent(self):
    self.SetMode(AAC)
    return core.GetUnit(self.ask("MEAS?"), "A")

  def MeasureACDCCurrent(self):
    self.SetMode(AACDC)
    return core.GetUnit(self.ask("MEAS?"), "A")

  def MeasureFrequency(self):
    self.SetMode(FREQ)
    return core.GetUnit(self.ask("MEAS?"), "Hz")

  def MeasureResistance(self):
    self.SetMode(OHMS)
    return core.GetUnit(self.ask("MEAS?"), "ohm")

  def MeasureContinuity(self):
    self.SetMode(CONT)
    return core.ValueCheck(self.ask("MEAS?"))



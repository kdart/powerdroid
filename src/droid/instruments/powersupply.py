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



"""Power supply type of instruments.
"""


from droid.instruments import gpib
from droid.instruments import core


class PowerSupply(gpib.GpibInstrument):
  """Generic SCPI power supply."""

  def Reset(self):
    self.clear()
    self.write("*RST; :STATUS:PRESET; *CLS; *SRE 0; *ESE 0")

  def SetVoltage(self, voltage):
    self.write("SOUR:VOLT %sV" % float(voltage))

  def GetVoltage(self):
    return core.GetUnit(self.ask("SOUR:VOLT?"), "V")

  voltage = property(GetVoltage, SetVoltage)

  def SetChargerVoltage(self, voltage):
    self.write("SOUR:VOLT2 %sV" % float(voltage))

  def GetChargerVoltage(self):
    return core.GetUnit(self.ask("SOUR:VOLT2?"), "V")

  charger_voltage = property(GetChargerVoltage, SetChargerVoltage)

  def On(self):
    self.write("OUTP1:STAT 1")

  def Off(self):
    self.write("OUTP1:STAT 0")

  def GetOutputState(self):
    return bool(int(self.ask("OUTP1:STAT?")))

  def SetOutputState(self, val):
    if core.GetBoolean(val):
      self.On()
    else:
      self.Off()

  outputstate = property(GetOutputState, SetOutputState)

  def ChargerOn(self):
    self.write("OUTP2:STAT 1")

  def ChargerOff(self):
    self.write("OUTP2:STAT 0")

  def GetChargerOutputState(self):
    return bool(int(self.ask("OUTP2:STAT?")))

  def SetChargerOutputState(self, val):
    if core.GetBoolean(val):
      self.ChargerOn()
    else:
      self.ChargerOff()

  charger_outputstate = property(GetChargerOutputState, SetChargerOutputState)

  def GetVoltageHeadings(self):
    return ("Voltage (V)",)

  ### Measurement methods.
  def MeasureDCVoltage(self):
    return core.GetUnit(self.ask("MEAS:VOLT?"), "V")

  def MeasureDCCurrent(self):
    return core.GetUnit(self.ask("MEAS:CURR?"), "A")

  def MeasureACDCCurrent(self):
    return core.GetUnit(self.ask("MEAS:CURR:ACDC?"), "A")

  dccurrent = property(MeasureDCCurrent)
  acdccurrent = property(MeasureACDCCurrent)

  def FetchDCVoltage(self):
    """Fetch DC voltage, in V."""
    return core.GetUnit(self.ask("FETC:VOLT?"), "V")

  def FetchDCCurrent(self):
    """Fetch avg current measurement."""
    return core.GetUnit(self.ask("FETC:CURR?"), "A")

  def FetchACDCCurrent(self):
    """Fetch avg current measurement."""
    return core.GetUnit(self.ask("FETC:CURR:ACDC?"), "A")

  def FetchMaxCurrent(self):
    """Fetch maximum point current measurement."""
    return core.GetUnit(self.ask("FETC:CURR:MAX?"), "A")

  def FetchMinCurrent(self):
    """Fetch minimum point current measurement."""
    return core.GetUnit(self.ask("FETC:CURR:MIN?"), "A")

  def FetchHighCurrent(self):
    """Fetch high average point current measurement."""
    return core.GetUnit(self.ask("FETC:CURR:HIGH?"), "A")

  def FetchLowCurrent(self):
    """Fetch low average point current measurement."""
    return core.GetUnit(self.ask("FETC:CURR:LOW?"), "A")

  def FetchAllCurrent(self):
    """Return electric current reading.

    Returns:
      (ACDCaverge, HIGH, LOW, MAXimum, MINimum) in mA.
    """
    resp = self.ask('FETC:CURR:ACDC?; HIGH? ;LOW?; MAX?; MIN? ')
    return [core.ValueCheck(x) for x in resp.split(";")]

  def MeasureAllCurrent(self):
    """Return electric current reading.

    Also initiates a measurement cycle.

    Returns:
      (ACDCaverge, LOW, HIGH, MINimum, MAXimum).
    """
    resp = self.ask('MEAS:CURR:ACDC?;:FETC:CURR:LOW?;HIGH?;MIN?;MAX?')
    return [core.ValueCheck(x) for x in resp.split(";")]

  def MeasureAllCurrentAsText(self):
    """Return electric current reading.

    Also initiates a measurement cycle. This method is fastest.

    Returns:
      (ACDCaverge, LOW, HIGH, MINimum, MAXimum) in mA.
    """
    resp = self.ask('MEAS:CURR:ACDC?;:FETC:CURR:LOW?;HIGH?;MIN?;MAX?')
    return resp.split(";")

  ### Reporting support
  def GetAllCurrentHeadings(self):
    return ("Average (A)", "Low (A)", "High (A)", 
        "Minimum (A)", "Maximum (A)")

  def GetAllCurrentTextHeadings(self):
    return ("Average (A)", "Low (A)", "High (A)", 
        "Minimum (A)", "Maximum (A)")


class Ag66319D(PowerSupply):
  """An Agilent 66319D Mobile Communications DC Source."""

  def Reset(self):
    super(Ag66319D, self).Reset()
    # OUTP command not joined for two supplies.
    self.write("INST:COUP:OUTP:STAT NONE")
    self.SetOutputState(False)
    self.SetChargerOutputState(False)
    self.SetVoltage(0.0)
    self.SetChargerVoltage(5.0)

  def Prepare(self, measurecontext):
    myctx = measurecontext.powersupplies
    assert myctx.subsampleinterval >= 15.6e-6
    self.clear()
    self.SetVoltage(myctx.voltage)
    self.On()
    samps = myctx.subsamples
    # XXX needs work. non-linear. calibrated to 4096 samples.
    return (samps * myctx.subsampleinterval) + (samps * 1.85e-5)

  def GetDVM(self):
    return self.Clone(Ag66319dDVM)

  def MeasureDVMDCVoltage(self):
    return core.GetUnit(self.ask("MEAS:DVM:DC?"), "V")


class Ag66319dDVM(gpib.GpibInstrument):
  """The built-in DVM of the Agilent 66319D.

  May be used as a separate instrument.
  """

  def GetVoltageHeadings(self):
    return ("Voltage (V)",)

  def MeasureDCVoltage(self):
    return core.GetUnit(self.ask("MEAS:DVM:DC?"), "V")

  def MeasureACDCVoltage(self):
    return core.GetUnit(self.ask("MEAS:DVM:ACDC?"), "V")



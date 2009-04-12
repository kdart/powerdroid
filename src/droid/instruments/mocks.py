#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Mock instruments used for unit testing.

"""


from pycopia import scheduler

from droid.instruments import core


class MockGpibDevice(object):
  def __init__(self, ctx, logfile=None):
    self._timeout = 0
    self._output = 1
    self._voltage = 0.0
    self._callstate = 0
    self._chargerstate = False

  def clear(self):
    pass

  def wait(self):
    pass

  def poll(self):
    pass

  def trigger(self):
    pass

  def ask(self, string):
    return string

  def identify(self):
    return core.Identity("Mock,Mock,Mock,Mock")

  def GetError(self):
    return core.DeviceError(0, "Mock Error")

  def Errors(self):
    return []

  def close(self):
    pass

  status = property(lambda self: core.Status(0))

  def _get_timeout(self):
    return self._timeout

  def _set_timeout(self,  value):
    self._timeout = value

  timeout = property(_get_timeout, _set_timeout)

  def write(self, string):
    return len(string)

  def writebin(self, string, length):
    return length

  def read(self, len=4096):
    return ""

  def readbin(self, len=4096):
    return ""


class MockDevice(MockGpibDevice):
  """Combined mock device. Provides mock methods for all types of devices."""
  def MeasureAllCurrent(self):
    scheduler.sleep(0.1)
    return [3.22272, 2.66412, 16.4231, 1.06339, 16.4231]

  def MeasureAllCurrentAsText(self):
    scheduler.sleep(0.1)
    return ["3.22272E-3", "2.66413E-3", "1.64231E-2", "1.06339E-3", "1.64231E-2\n"]

  def GetAllCurrentHeadings(self):
    return ("Average (mA)", "Low (mA)", "High (mA)", 
        "Minimum (mA)", "Maximum (mA)")

  def GetAllCurrentTextHeadings(self):
    return ("Average (A)", "Low (A)", "High (A)", 
        "Minimum (A)", "Maximum (A)")

  def GetVoltageHeadings(self):
    return ("Voltage (V)",)

  def MeasureDCVoltage(self):
    if self._output:
      return self._voltage
    else:
      return 4.2 # simulate charger connection.

  def MeasureCurrent(self):
    return 1.22272

  def MeasureDCCurrent(self):
    return 0.0

  def SetVoltage(self, voltage):
    self._voltage = voltage

  def GetVoltage(self):
    return self._voltage

  voltage = property(GetVoltage, SetVoltage)

  def On(self):
    self._output = 1

  def Off(self):
    self._output = 0

  def Call(self):
    self._callstate = 1

  def Hangup(self):
    self._callstate = 0

  def IsCallActive(self):
    return self._callstate

  def Prepare(self, measurecontext):
    return 0.001

  def GetOutputState(self):
    self._output

  def SetOutputState(self, val):
    if isinstance(val, str):
      state = (val.lower() == "on" or val == "1")
    else:
      state = bool(val)
    if state:
      self.On()
    else:
      self.Off()

  outputstate = property(GetOutputState, SetOutputState)

  def ChargerOn(self):
    self._chargerstate = True

  def ChargerOff(self):
    self._chargerstate = False

  def GetChargerOutputState(self):
    return self._chargerstate

  def SetChargerOutputState(self, val):
    if isinstance(val, str):
      state = (val.lower() == "on" or val == "1")
    else:
      state = bool(val)
    if state:
      self.ChargerOn()
    else:
      self.ChargerOff()

  charger_outputstate = property(GetChargerOutputState, SetChargerOutputState)

  def ClearErrors(self):
    pass

  def MeasureDVMDCVoltage(self):
    return 3.3


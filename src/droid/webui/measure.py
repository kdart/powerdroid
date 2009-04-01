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



"""Invoke measurements.
"""

__author__ = 'dart@google.com (Keith Dart)'


import sys
from datetime import datetime

from pycopia.WWW import json

from droid.instruments import powersupply


def SetVoltage(name, voltage):
  ps = _GetPowerSupply(name)
  if voltage < 5.0 and voltage > 0.0:
    voltagenow = ps.GetVoltage()
    if voltagenow != voltage:
      ps.SetVoltage(voltage)
    return True
  else:
    return False

def GetVoltage(name):
  ps = _GetPowerSupply(name)
  return ps.GetVoltage()

def On(name):
  ps = _GetPowerSupply(name)
  ps.On()
  return True

def Off(name):
  ps = _GetPowerSupply(name)
  ps.Off()
  return True

def MeasureCurrent(name):
  ps = _GetPowerSupply(name)
  return ps.MeasureCurrent()

def _GetPowerSupply(name):
  return powersupply.PowerSupply(name.encode("ascii"))


class WebReport(object):
  def SetColumns(self, *args):
    pass

  def WriteRecord(self, *args):
    pass



_EXPORTED = [SetVoltage, GetVoltage, On, Off, MeasureCurrent]

handler = json.JSONDispatcher(_EXPORTED)

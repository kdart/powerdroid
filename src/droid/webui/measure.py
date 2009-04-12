#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright 2007 The Android Open Source Project

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

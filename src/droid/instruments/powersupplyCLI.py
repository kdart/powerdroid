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



"""Command line interface for power supplies.
"""

from pycopia import timelib

from droid.instruments import gpibCLI


class PowerSupplyCLI(gpibCLI.GenericInstrument):
  pass


class Ag66319D_CLI(PowerSupplyCLI):

  def powercycle(self, argv):
    """powercycle
  Cycles the main and charger output.
    """
    ps = self._obj
    voltage = ps.GetVoltage()
    ps.Reset()
    timelib.sleep(2)
    ps.SetVoltage(voltage)
    ps.outputstate = "on"
    timelib.sleep(3)
    ps.charger_outputstate = "on"


  def usb(self, argv):
    """usb [on|off]
  Set the DUT's USB connection to on or off by controlling the charger
  supply output connected to the USB solid state relay."""
    ps = self._obj
    if len(argv) >= 2:
      ps.charger_outputstate = argv[1]
    if ps.charger_outputstate:
      self._print("USB ON")
      return 0
    else:
      self._print("USB OFF")
      return 1


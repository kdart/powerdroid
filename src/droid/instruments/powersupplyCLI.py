#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

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

  def currentrange(self, argv):
    """currentrange [high | medium | low | <float>]
  Set the current detector range to given value.
  Display current max value if no parameter supplied."""
    if len(argv) > 1:
      self._obj.SetCurrentRange(argv[1])
    else:
      self._print(self._obj.GetCurrentRange())


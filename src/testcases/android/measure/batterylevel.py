#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#
# Copyright The Android Open Source Project
#
# Note that docstrings are in RST format:
# <http://docutils.sourceforge.net/rst.html>.
#
# The docstring headings map to testcase fields, so the names should not
# be changed.


"""
Measure battery levels.
-----------------------

Module contains tests to measure various battery levels.

"""

__version__ = "$Revision$"


from pycopia import aid
from pycopia import timelib
from droid import adb
from droid.qa import core

from testcases.android import interactive


class MeasureLevelAdjustment(interactive.AndroidInteractiveMixin, core.Test):
  """
Purpose
+++++++

Measure relation between battery voltage and reported battery level.

Pass criteria
+++++++++++++

None

Start Condition
+++++++++++++++

None

End Condition
+++++++++++++

No change

Reference
+++++++++

None

Prerequisites
+++++++++++++

None

Procedure
+++++++++

Start at maximum battery voltage (4.2 volts). 
Step down voltage in 0.01 volt increments until it reaches minimum value
(2.8 volts)
For each increment:
  Press the back key to make sure the backlight is on.
  let the device settle for a few seconds.
  get the "capacity" attribute from the battery power interface.
  record the voltage, charge capacity, and LCD backlight brightness setting.

"""

  def Initialize(self):
    cf = self.config
    env = cf.environment
    self.Info("Setting maximum battery and rebooting.")
    env.powersupply.SetVoltage(4.2)
    env.DUT.Reboot()
    self.Sleep(60)
    self.WaitForRuntime()

  def Execute(self):
    self.Info("Starting.")
    cf = self.config
    env = cf.environment

    fo = self.GetFile("voltage_batt_lcd", "dat")
    self.Info("Data file path: %r" % (fo.name,))
    fo.write("# Time\tVoltage (V)\tMeasured (V)\tLevel\tLCD Brightness\n")
    try:
      for v in aid.frange(4.19, 2.79, -0.01):
        env.DUT.BackKey()
        t = timelib.now()
        batt = env.DUT.GetBatteryInfo()
        led = env.DUT.GetLEDInfo()
        self.Info("Set voltage: %s, level: %s, measured: %s V, LCD: %s" % (
            v, batt.capacity, batt.voltage, led.lcd_brightness))
        fo.write("%s\t%s\t%s\t%s\t%s\n" % (
            t, v, batt.voltage, batt.capacity, led.lcd_brightness))
        env.powersupply.SetVoltage(v)
        self.Sleep(10)
    except adb.AdbError:
      self.Info("Device powered off.")

    fo.close()
    return self.Passed("Done.")

  def Finalize(self, outcome):
    cf = self.config
    env = cf.environment
    env.powersupply.SetVoltage(3.8)


class BatteryLevelSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = BatteryLevelSuite(conf)
  suite.addTest(MeasureLevelAdjustment)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab

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


class MeasureLevelAdjustment(core.Test):
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
  def Execute(self):
    self.Info("Starting.")
    cf = self.config
    env = cf.environment

    fo = self.GetFile("voltage_batt_lcd", "dat")
    self.Info("Data file path: %r" % (fo.name,))
    fo.write("Time\tVoltage (V)\tLevel\tLCD Brightness\n")

    try:
      for v in aid.frange(4.2, 2.8, -0.01):
        env.DUT.BackKey()
        env.powersupply.SetVoltage(v)
        self.Sleep(5)
        t = timelib.now()
        batt = env.DUT.GetBatteryInfo()
        led = env.DUT.GetLEDInfo()
        self.Info("Voltage: %s  level: %s  LCD: %s" % (
            v, batt.capacity, led.lcd_brightness))
        fo.write("%s\t%s\t%s\t%s\n" % (t, v, batt.capacity, led.lcd_brightness))
    except adb.AdbError:
      self.Info("Device powered off.")

    fo.close()
    return self.Passed("Done.")



class BatteryLevelSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = BatteryLevelSuite(conf)
  suite.addTest(MeasureLevelAdjustment)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


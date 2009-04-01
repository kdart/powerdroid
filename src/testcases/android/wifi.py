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



"""Wifi related tests.

"""

import os
import shutil

from droid.storage import datafile
from droid.qa import core

from testcases.android import interactive
from testcases.android import measurements



class WifiBaseTest(interactive.AndroidInteractiveMixin, core.Test):
  pass


class WifiSignalStrength(WifiBaseTest):
  """
Purpose
+++++++

Verify signal strength indicator updates at regular intervals.

Pass criteria
+++++++++++++


Start Condition
+++++++++++++++


End Condition
+++++++++++++

No change.

Reference
+++++++++

http://b/issue?id=1165470

Prerequisites
+++++++++++++


Procedure
+++++++++

1. Raise wifi access point to highest transmit power.
2. Give some time to settle, and then record the DUT RSSI.
3. Lower the the wifi access point transmit power to lowest point (1 mW). 
4. Give some time to settle, get DUT RSSI reading. 
5. Verify that the RSSI reading is significantly less than the first
   reading.


"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    return self.Incomplete("Not implemented.") 


class WifiPowerComparison(measurements.MeasurementsMixin, WifiBaseTest):
  """
Purpose
+++++++

Determine difference in power levels between wifi turned on, and wifi
turned off.

Pass criteria
+++++++++++++

None, measurement.

Start Condition
+++++++++++++++

Wifi is enabled, and attached to a lab AP.
Airplane mode is off.

End Condition
+++++++++++++

Wifi is disabled.

Reference
+++++++++


Prerequisites
+++++++++++++


Procedure
+++++++++

1. Set airplane mode.
1. Measure current draw.
2. Toggle wifi state.
3. Measure current draw.
4. Repeat steps 2 and 3 10 times.


"""
  def Finalize(self, result):
    pass # don't run super Finalize.

  def MeasureWifi(self, round):
    cf = self.config
    DUT = cf.environment.DUT
    cf.datafiles.name = "/var/tmp/current_wifi" 
    self.DisconnectDevice()
    self.Sleep(45)
    try:
      self.TakeCurrentMeasurements()
    finally:
      self.ConnectDevice()
      self.Sleep(1)
      DUT.ActivateUSB()
    self.SaveResult(round)
    self.Info(DUT.GetTimeInfo())

  def SaveResult(self, round):
    cf = self.config
    fpdir = datafile.GetDirectoryName(cf)
    fpname = datafile.GetFileName(self, round=round)
    tmpfile = cf.datafiles.name + ".dat"
    dest = "%s/%s" % (fpdir, fpname)
    if tmpfile and os.path.exists(tmpfile):
      shutil.move(tmpfile, dest)
      self.Info("Created data file %r." % (dest,))
      os.chmod(dest, 0440)
    else:
      self.Diagnostic("Where is temp file %r?" % tmpfile)

  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT

    cf.UI.printf(
        "%IMake sure DUT has Airplane mode off, "
        "and wifi ON and connected to 'android-lab'.%N\n "
        "Answer yes when done.")
    if not cf.UI.yes_no("All set?", default=False):
      return self.Incomplete("Start condition not set.")
    DUT.StateON("wifi")
    DUT.StateOFF("airplane")
    DUT.StateOFF("bluetooth")
    DUT.StateOFF("call")
    DUT.StateOFF("audio")
    DUT.StateOFF("sync")
    DUT.StateOFF("xmpp")
    DUT.ToggleAirplaneMode()
    try:
      for i in range(8):
        self.Info("Measuring round %d." % i)
        self.MeasureWifi(i)
        DUT.ToggleWifiState()
    finally:
      DUT.ToggleAirplaneMode()
    return self.Passed("Collections complete.") 



class WifiSuite(core.TestSuite):
  pass

def GetSuite(conf):
  suite = WifiSuite(conf)
  suite.AddTest(WifiSignalStrength)
  suite.AddTest(WifiPowerComparison)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


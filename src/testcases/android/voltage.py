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
VoltageDrop
-----------

Determine battery life by measuring voltage on battery directly.

"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"


from droid.qa import core
from testcases.android import measurements
from testcases.android import interactive


class DeviceSetup(core.Test, interactive.AndroidInteractiveMixin):
  """
Purpose
+++++++

This is a utility test case that does the initial setup of an Android
deviced in a stand-along configuration.

Pass criteria
+++++++++++++

Device and environment setup completes without throwing an exception.

Start Condition
+++++++++++++++

None.

End Condition
+++++++++++++

Device is powered on. It also has sync featured turned on, phone is
inactive (hung up), no audio signal is being applies.

Reference
+++++++++

None

Prerequisites
+++++++++++++

None

Procedure
+++++++++


"""

  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    self.ConnectDevice()
    self.PowerOnDevice()
    # Do a manual build info entry if it could not be obtained from USB.
    if not DUT.IsUSBActive():
      self.Info("COuld not get working USB connection. Entered build info manually.")
      self.GetBuildInfoFromUser()
    self.DisconnectDevice()
    self.Info("\nProduct: %s\nType: %s\nBuild id: %s\n" % (
        DUT.build.product, 
        DUT.build.type, 
        DUT.build.id))
    self.ExternalAudioOff()
    self.HangupCall()
    self.DeviceSyncOn()
    return self.Passed("Device set up.")


class VoltageDropTest(interactive.AndroidInteractiveMixin, 
        measurements.MeasurementsMixin, core.Test):
  """
Purpose
+++++++

This is a measurement test. It takes periodic voltage readings for a user
specificied amount of time (usually several days), and records them to a
report time.

Pass criteria
+++++++++++++

VoltageDrop What is required to indicate passing?

Start Condition
+++++++++++++++

VoltageDrop Conditions needed to begin.

End Condition
+++++++++++++

VoltageDrop State the test leaves the Unit Under Test in.

Reference
+++++++++

VoltageDrop Reference to design spec. section (could be URL).

Prerequisites
+++++++++++++

testcases.android.voltage.DeviceSetup

Procedure
+++++++++

Call TakeVoltageMeasurements which records voltage readings from a
multimeter.

"""

  def execute(self):
    self.Info("Starting voltage measurments.")
    self.TakeVoltageMeasurements()
    return self.Passed("Voltage readings complete.")

# TODO(dart) fixme: monkey patch for now, this should be automatic.
core.InsertOptions(VoltageDropTest)
VoltageDropTest.OPTIONS.prerequisites = [
    core.PreReq("testcases.android.voltage.DeviceSetup"),
  ]


class VoltageDropSuite(core.TestSuite):
  pass

def GetSuite(conf):
  suite = VoltageDropSuite(conf)

  suite.AddTest(DeviceSetup)
  suite.AddTest(VoltageDropTest)

  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


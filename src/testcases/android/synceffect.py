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
Sync Effect
-----------

Measure power consumption effects related to the sync feature.

"""

__author__ = 'dart@google.com (Keith Dart)'


from testcases.android import common


class SyncEffectTest(common.DroidBaseTest):
  """
Purpose
+++++++

Measure the power consumption of syncing in various sync on/off states.
Determine if sync function leaves "orphaned" resources such as wake locks. 

Pass criteria
+++++++++++++

None, measurement test.

Start Condition
+++++++++++++++

Normal state (sync is ON)

End Condition
+++++++++++++

No change.

Reference
+++++++++

None

Prerequisites
+++++++++++++

testcases.android.common.DeviceSetup

Procedure
+++++++++

Phase 1 (normal, sync ON, fresh boot [from DeviceSetup]):
  Make sure sync is enabled (as in other tests).
  Measure current draw.

Phase 2 (sync off from fresh boot):
  Disable sync (turn it off)
  Power cycle device. Now its booted with sync OFF.
  Measure current draw, report average.

Phase 3 (sync freshly turned on, but no updates):
  Enable sync.
  Measure current draw, report average.

Phase 4 (active email updates):
  Send some emails, wait for sync to happen.
  Measure current draw, report average.

Phase 5 (post sync, post update, sync OFF current draw):
  Disable sync.
  Measure current draw, report average.

"""
  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def MeasureCurrentDraw(self, phase):
    cf = self.config
    self.StartIPCounters()
    self.TakeCurrentMeasurements(metadata={"phase": phase})
    self.Info("IP Traffic during measurement cycle:")
    self.EndIPCounters()
    self.Info(cf.environment.DUT.GetTimeInfo())
    cf.logfile.note("Phase: %s" % phase)
    cf.logfile.note(str(cf.environment.DUT))
    cf.environment.DUT.BugReport(cf.logfile)

  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    self.assertTrue(DUT.IsStateON("sync"))
    self.MeasureCurrentDraw(1)
    self.Info("Set syncing OFF.")
    DUT.SetSyncOFF()
    self.PowerCycle()
    self.PowerOnDevice()
    DUT.UpdateAllStates()
    DUT.UpdateSharedSettings()
    DUT.CallInactive()
    self.assertTrue(DUT.IsStateOFF("sync"))
    self.Info("Waiting for DUT to settle down.")
    self.Sleep(60)
    self.MeasureCurrentDraw(2)
    self.Info("Set syncing ON.")
    DUT.SetSyncON()
    self.MeasureCurrentDraw(3)
    self.TurnUpdatesOn()
    self.MeasureCurrentDraw(4)
    self.TurnUpdatesOff()
    self.Info("Set syncing OFF.")
    DUT.SetSyncOFF()
    self.MeasureCurrentDraw(5)
    DUT.SetSyncON()
    return self.Passed("Measurements complete.")


class SyncEffectSuite(common.DroidBaseSuite):
  pass


def GetSuite(conf):
  suite = SyncEffectSuite(conf)
  suite.AddTest(SyncEffectTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


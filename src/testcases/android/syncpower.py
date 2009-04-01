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
Sync Power
----------

Measure power consumption related the sync activity.

"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"


from droid.qa import core
from testcases.android import measurements
from testcases.android import interactive


class SyncPowerTest(interactive.AndroidInteractiveMixin, 
        measurements.MeasurementsMixin, core.Test):
  """
Purpose
+++++++

Measure power consumption when setting up an existing account with a large
number of emails and update activity.

Pass criteria
+++++++++++++

None (measurement test)

Start Condition
+++++++++++++++

Fresh build with no account configured on the DUT.

End Condition
+++++++++++++

DUT has account set up and mail synced.

Reference
+++++++++

None

Prerequisites
+++++++++++++

DeviceSetup

Procedure
+++++++++

Start device.
Add account using initial setup wizard.
Measure current draw for one hour.

"""

  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    name = cf.account
    password = cf.account_password
    self.Info("Setting account %r." % (name,))
    DUT.SetupWizard(name, password)
    self.Sleep(2)
    self.DisconnectDevice()
    try:
      self.TakeCurrentMeasurements()
    finally:
      self.ConnectDevice()
      DUT.ActivateUSB()

    return self.Passed("Measuring done.")


class SyncPowerSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = SyncPowerSuite(conf)
  suite.AddTest(SyncPowerTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


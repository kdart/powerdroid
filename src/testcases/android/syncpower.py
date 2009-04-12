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
Sync Power
----------

Measure power consumption related the sync activity.

"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"


from testcases.android import common


class SyncPowerTest(common.DroidBaseTest):
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

testcases.android.common.DeviceSetup

Procedure
+++++++++

Start device.
Add account using initial setup wizard.
Measure current draw for one hour.

"""
  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    name = cf.account
    password = cf.account_password
    self.Info("Setting account %r." % (name,))
    DUT.SetupWizard(name, password)
    self.TakeCurrentMeasurements()
    return self.Passed("Measuring done.")


class SyncPowerSuite(common.DroidBaseSuite):
  pass


def GetSuite(conf):
  suite = SyncPowerSuite(conf)
  suite.AddTest(SyncPowerTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


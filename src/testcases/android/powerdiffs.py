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
Power difference tests.
----------------

"""

__version__ = "$Revision$"


from droid.qa import core
from testcases.android import common
from testcases.android import interactive



class PowerDiffBaseTest(interactive.AndroidInteractiveMixin, core.Test):
  pass


class WifiPowerDiff(BluetoothBaseTest):
  """
Purpose
+++++++


Pass criteria
+++++++++++++


Start Condition
+++++++++++++++


End Condition
+++++++++++++


Reference
+++++++++



Prerequisites
+++++++++++++

testcases.android.common.DeviceSetup

Procedure
+++++++++

Prerequisite will boot the device. Verify Wifi feature is off.
Take current measurements.
Turn wifi on, verify connected. 
Take current measurements.
Turn wifi off.
Take current measurements.
Verify median and mean current draw for the first and last measurement set
are withing X% of each other.

"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT

    return self.incomplete("Not implemented.") 
    #return self.passed("Bluetooth enabled and verified activated.") 





class PowerDiffSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = PowerDiffSuite(conf)
  suite.addTest(common.DeviceSetup)
  suite.addTest(WifiPowerDiff)
  suite.addTest(common.DeviceSetup)
  suite.addTest(BluetoothPowerDiff)
  return suite


def run(conf):
  suite = GetSuite(conf)
  suite()


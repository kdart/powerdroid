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
VoltageDrop
-----------

Determine battery life by measuring voltage on battery directly.

"""

__version__ = "$Revision$"


from testcases.android import common


class VoltageDropTest(common.DroidBaseTest):
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

testcases.android.common.DeviceSetup

Procedure
+++++++++

Call TakeVoltageMeasurements which records voltage readings from a
multimeter.

"""
  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def execute(self):
    self.Info("Starting voltage measurments.")
    self.TakeVoltageMeasurements()
    return self.Passed("Voltage readings complete.")


class VoltageDropSuite(common.DroidBaseSuite):
  pass


def GetSuite(conf):
  suite = VoltageDropSuite(conf)
  suite.AddTest(VoltageDropTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project


"""

"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"



from droid.qa import core


class BatteryRundownTest(core.Test):
  """
Purpose
+++++++

Measure voltage and current of an actual battery discharging.

Pass criteria
+++++++++++++

None

Start Condition
+++++++++++++++

Test bed is set up to use the battery run-down test jig, and a fully
charged battery is connected to it.

End Condition
+++++++++++++

Battery is depleted.

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
    env = cf.environment
    self.Info("Starting battery rundown.")

    return self.Passed("Done.")



class BatteryRundownSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = BatteryRundownSuite(conf)
  suite.AddTest(BatteryRundownTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


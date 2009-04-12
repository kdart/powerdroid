#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright Google Inc. All Rights Reserved.


"""Test network transistions.

"""

from droid.qa import core

from testcases.android import common



class NetworkChangeTest(common.DroidBaseTest):
  """
Purpose
+++++++

Verify timely transition between GPRS and EGPRS networks.

Pass Criteria
+++++++++++++

Transitions each way between operating modes takes less than 10 seconds to
re-establish PDP contexts.

Start Condition
+++++++++++++++

Network is operational in EDGE/EGPRS mode.

End Condition
+++++++++++++

No change.

Prerequisites
+++++++++++++

  testcases.android.common.DeviceSetup

Procedure
+++++++++

1. Establish PDP connection in EGPRS.
2. Change operating mode to GPRS.
3. Verify DUT re-establishes PDP context in GPRS mode in less than 10
   seconds.
4. Change operating mode to EGPRS.
5. Verify DUT re-establishes PDP context in EGPRS mode in less than 10
   seconds.
6. Repeat steps 2 through 5 for 50 iterations.

"""
  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def Execute(self):
    cf = self.config
    env = cf.environment
    testset = env.testset
    for i in xrange(50):
      testset.SetOperatingMode(testset.GPRS)
      self.Sleep(10)
      if not testset.IsPDPAttached():
        return self.Failed("PDP did not re-attach after switch to GPRS.")
      testset.SetOperatingMode(testset.EGPRS)
      self.Sleep(10)
      if not testset.IsPDPAttached():
        return self.Failed("PDP did not re-attach after switch to EGPRS.")
    return self.Passed("Successful GPRS/EGPRS after 50 tries.")


class NetworkSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = CallHandlingSuite(conf)
  suite.AddTest(NetworkChangeTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


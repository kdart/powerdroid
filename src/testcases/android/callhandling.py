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
Call handling module.
---------------------

Tests related to handling calls.

"""

__version__ = "$Revision$"


from droid.qa import core

from testcases.android import common



class CallHandlingTest(common.DroidBaseTest):
  """
Purpose
+++++++

Verify call handling reliability in the face of simultaneous user
operations. Also measure current draw during call time.

Pass Criteria
+++++++++++++

Call is made and answered, without errors, and did not drop.

Start Condition
+++++++++++++++

None

End Condition
+++++++++++++

No change.


Prerequisites
+++++++++++++

  testcases.android.common.DeviceSetup

Procedure
+++++++++

- Activate a call from test set or DUT.
- Optionally change lid state on DUT.
- Answer call from DUT or test set.
- Optionally change lid state on DUT.
- Verify call is established.
- Measure current draw and verify that it is consistent with an active call
  and display on.
- Hang up call.

"""
  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  DIRECTION_STRINGS = {
    # usercall, userhang
    (False, False): "net originated, net hang",
    (False, True): "net originated, mobile hang",
    (True, False): "mobile originated, net hang",
    (True, True): "mobile originated, mobile hang",
  }

  def HoldCall(self):
    cf = self.config
    env = cf.environment
    self.TakeCurrentMeasurements([self.CallChecker])
    for errcode in cf.environment.testset.Errors():
      self.Diagnostic(errcode)
    self.Info(env.DUT.GetTimeInfo())

  def CheckCall(self):
    cf = self.config
    if not cf.environment.testset.callcondition.connected:
      self.Diagnostic("Call is not active.")
      cf.environment.DUT.CallInactive()
      for errcode in cf.environment.testset.Errors():
        self.Diagnostic(errcode)
      raise core.TestFailError("Call dropped after measurement.")

  def Execute(self, usercall, userhang, fliplid):
    cf = self.config
    env = cf.environment
    self.Info(
        "usercall: %s, userhang: %s, fliplid: %s" % (
        usercall, userhang, fliplid))
    # do a lid open and close to see it that effects call handling.
    if fliplid:
      self.Info("Open lid.")
      env.DUT.OpenLid()
      self.Sleep(5)
    self.MakeACall(user=usercall)
    if fliplid:
      self.Info("Close lid.")
      env.DUT.CloseLid()
    self.HoldCall()
    self.CheckCall()
    self.HangupCall(user=userhang)
    return self.Passed("Call: %s passed." %
        self.DIRECTION_STRINGS[(usercall, userhang)])


class CallHandlingSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = CallHandlingSuite(conf)
  suite.AddTest(CallHandlingTest, False, False, False)
  suite.AddTest(CallHandlingTest, False, True, False)
  suite.AddTest(CallHandlingTest, True, False, False)
  suite.AddTest(CallHandlingTest, True, True, True)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


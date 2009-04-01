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
Call handling module.
---------------------

Tests related to handling calls.

"""

__version__ = "$Revision$"

import os

from droid.qa import core
from droid.qa import constants
from droid.storage import datafile

from testcases.android import interactive
from testcases.android import common


class CallHandlingTest(interactive.AndroidInteractiveMixin, 
        core.Test):
  """
Purpose
+++++++

Verify call handling reliability in the face of simultaneous user
operations.

Pass Criteria
+++++++++++++

Call is made and answered, without errors.

Start Condition
+++++++++++++++

None

End Condition
+++++++++++++

No change.


Prerequisites
+++++++++++++

None

Procedure
+++++++++

- Activate a call from test set.
- Change lid state on DUT.
- Answer call from DUT.
- Verify call is established.
- Measure current draw and verify that it is consistent with an active call
  and display on.
- Hang up call.
- Measure current draw and verify that it is consistent with no active
  call.

"""

  def CurrentDrawInfo(self, msg=""):
    cf = self.config
    env = cf.environment
    self.DisconnectDevice()
    try:
      currentdraw = env.powersupply.MeasureACDCCurrent()
      self.Info("%s Current draw is %s." % (msg, currentdraw))
    finally:
      self.ConnectDevice()
      env.DUT.ActivateUSB()
    self.Sleep(8)

  def CheckCall(self):
    cf = self.config
    self.Info("Checking if call active.")
    if not cf.environment.testset.callcondition.connected:
      cf.environment.DUT.CallInactive()
      for errcode in cf.environment.testset.Errors():
        self.Diagnostic(errcode)
      raise core.TestFailError("Call dropped.")

  def Execute(self):
    cf = self.config
    env = cf.environment

    self.CurrentDrawInfo("Initial state, no call active.")
    # do a lid open and close to see it that effects call handling.
    self.Info("Open lid.")
    env.DUT.OpenLid()
    self.Sleep(5)
    self.MakeACall(user=False)
    self.Sleep(5)
    self.Info("Close lid.")
    env.DUT.CloseLid()
    self.CurrentDrawInfo("In call ES call, ES hang.")
    self.Sleep(cf.calltime)
    self.CheckCall()
    self.HangupCall(user=False)
    self.Sleep(5)
    self.CurrentDrawInfo("After call.")

    self.MakeACall(user=True)
    self.CurrentDrawInfo("In call MS call, MS hang.")
    self.Sleep(cf.calltime)
    self.CheckCall()
    self.HangupCall(user=True)
    self.Sleep(5)
    self.CurrentDrawInfo("After call.")

    self.MakeACall(user=True)
    self.Sleep(5)
    self.CurrentDrawInfo("In call MS call, ES hang.")
    self.Sleep(cf.calltime)
    self.CheckCall()
    self.HangupCall(user=False)
    self.Sleep(5)
    self.CurrentDrawInfo("After call.")

    self.MakeACall(user=False)
    self.Sleep(5)
    self.CurrentDrawInfo("In call ES call, MS hang.")
    self.Sleep(cf.calltime)
    self.CheckCall()
    self.HangupCall(user=True)
    self.Sleep(5)
    self.CurrentDrawInfo("After call.")

    return self.Passed("Call handling pass.") 


  def Finalize(self, result):
    cf = self.config
    if cf.environment.DUT.build and not cf.flags.DEBUG:
      fdir = datafile.GetDirectoryName(cf)
      datafile.MakeDataDir(fdir)
      os.symlink(cf.resultsdir, os.path.join(fdir, 
          os.path.basename(cf.resultsdir)))
      self.Info("Collecting bug report.")
      if result == constants.FAILED:
        cf.environment.DUT.BugReport(cf.logfile)


class CallHandlingSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = CallHandlingSuite(conf)
  if not conf.get("skipsetup", False):
    suite.AddTest(common.DeviceSetup)

    # TODO(dart) fixme: monkey patch for now, this should be automatic.
    core.InsertOptions(CallHandlingTest)
    opts = CallHandlingTest.OPTIONS
    opts.prerequisites = [core.PreReq("testcases.android.common.DeviceSetup")]

  suite.AddTest(CallHandlingTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


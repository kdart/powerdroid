#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab

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



"""The Power Droid Current Draw Test. 

Does all the stuff to take measurements and store results.
"""

__version__ = "$Revision: #1 $"

import os

from droid import constants
from droid.qa import core
from droid.storage import datafile
from droid.measure import core as measurecore

# mixin and utility tests
from testcases.android import common
from testcases.android import interactive
from testcases.android import measurements

ON = constants.ON
OFF = constants.OFF


class CollectCurrentDraw(interactive.AndroidInteractiveMixin, 
        measurements.MeasurementsMixin, 
        core.Test):
  """
Purpose
+++++++

Collect current draw measurements for various states of the device.

Precondition
++++++++++++

Device is has a mock-battery adapter connected to a power supply.
Device radio antenna connected to an Agilent 8960 test set.

Procedure
+++++++++

Alter device state according to parameters.
Take current draw measurements.

Prerequisites
+++++++++++++

testcases.android.common.DeviceSetup

  """

  def Execute(self, updatestate, syncstate, audiostate, callstate):
    self.StartIPCounters()
    self.Info(
        "updatestate: %s, syncstate: %s, audiostate: %s, callstate: %s" % (
        updatestate, syncstate, audiostate, callstate))
    cf = self.config
    DUT = cf.environment.DUT

    self.assertTrue(DUT.IsPoweredOn(), "DUT not in power-on state.")

    if syncstate == ON and not DUT.IsSyncingOn():
      self.DeviceSyncOn()
    if syncstate == OFF and DUT.IsSyncingOn():
      self.DeviceSyncOff()

    if updatestate == ON and not DUT.IsUpdatesOn():
      self.TurnUpdatesOn()
    if updatestate == OFF and DUT.IsUpdatesOn():
      self.TurnUpdatesOff()

    if callstate == ON and not DUT.IsCallActive():
      self.MakeACall(cf.usercall)
    if callstate == OFF and DUT.IsCallActive():
      self.HangupCall(cf.usercall)

    if audiostate == ON and not DUT.IsAudioOn():
      self.ExternalAudioOn()
    if audiostate == OFF and DUT.IsAudioOn():
      self.ExternalAudioOff()

    if callstate == ON:
      checkers = [self.CallChecker]
    else:
      checkers = None

    self.DisconnectDevice()

    self.Info("IP Traffic during state change:")
    self.EndIPCounters()
    self.StartIPCounters()
    try:
      self.TakeCurrentMeasurements(checkers)
    finally:
      self.ConnectDevice()
      DUT.ActivateUSB()
      self.Info(DUT.GetTimeInfo())
      self.Info(cf.environment.testset.GetUSFBler())
      for errcode in cf.environment.testset.Errors():
        self.Diagnostic(errcode)
      self.Info("IP Traffic during measurement cycle:")
      self.EndIPCounters()

    return self.Passed("Collection complete.")


class CurrentDrawSuite(core.TestSuite):

  def Initialize(self):
    cf = self.config
    cf.environment.testset.ResetCounters()
    cf.startipcounters = cf.environment.testset.GetIPCounters()

  def Finalize(self):
    cf = self.config
    self.Info("Total OTA IP traffic:")
    self.Info(cf.environment.testset.GetIPCounters() - cf.startipcounters)
    if cf.environment.DUT.build:
      fdir = datafile.GetDirectoryName(self.config)
      fname = datafile.GetFileName(self)
      os.symlink(
          cf.resultsdir, os.path.join(fdir, os.path.basename(cf.resultsdir)))


def StateFilter(updatestate, syncstate, audiostate, callstate):
  """Filters out invalid or unwanted combinations from the series generator.
  """
  if callstate == ON and updatestate == ON:
    return False
  # Don't care about audio signal if there is no call.
  if callstate == OFF and audiostate == ON:
    return False
  # updates don't matter if not syncing.
  if syncstate == OFF and updatestate == ON:
    return False
  return True


def GetSuite(conf):
  # Adjusted for more efficient testing. Radio state varies least often,
  # call state second least, etc. Starting state is first column.
  updatestates = [OFF, ON]
  syncstates = [ON, OFF]
  audiostates = [OFF, ON]
  callstates = [OFF, ON]

  suite = CurrentDrawSuite(conf)

  if not conf.get("skipsetup", False):
    suite.AddTest(common.DeviceSetup)

    # TODO(dart) fixme: monkey patch for now, this should be automatic.
    core.InsertOptions(CollectCurrentDraw)
    opts = CollectCurrentDraw.OPTIONS
    opts.prerequisites = [core.PreReq("testcases.android.common.DeviceSetup")]

  suite.AddTestSeries(CollectCurrentDraw, 
      # Note: leftmost argument varies fastest.
      args=(updatestates, syncstates, audiostates, callstates),
      filter=StateFilter)
  # one last combination that is the same as the first one. This is to
  # test if the device "settles" back into a mode similar to a fresh boot.
  suite.AddTest(CollectCurrentDraw, OFF, ON, OFF, OFF)
  return suite

def Run(conf):
  suite = GetSuite(conf)
  suite.Run()


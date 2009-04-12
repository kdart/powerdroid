#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""The Power Droid Current Draw Test. 

Does all the stuff to take measurements and store results.
"""

__version__ = "$Revision: #1 $"

import os

from testcases.android import common
from droid import constants

ON = constants.ON
OFF = constants.OFF


class CollectCurrentDraw(common.DroidBaseTest):
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

  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def Execute(self, updatestate, syncstate, wifistate, audiostate, callstate,
        airplanestate):
    self.StartIPCounters()
    self.Info(
        "updatestate: %s, syncstate: %s, wifistate: %s, audiostate: %s, callstate: %s" % (
        updatestate, syncstate, wifistate, audiostate, callstate))
    cf = self.config
    DUT = cf.environment.DUT

    self.assertTrue(DUT.IsPoweredOn(), "DUT not in power-on state.")

    if airplanestate == ON and not DUT.IsStateOFF("airplane"):
      self.SetAirplaneON()
    if airplanestate == OFF and DUT.IsStateON("airplane"):
      self.SetAirplaneOFF()

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
      self.DownlinkAudioOn()
    if audiostate == OFF and DUT.IsAudioOn():
      self.DownlinkAudioOff()

    if wifistate == ON and DUT.IsStateOFF("wifi"):
      self.EnableWifi()
    if wifistate == OFF and DUT.IsStateON("wifi"):
      self.DisableWifi()

    if callstate == ON:
      checkers = [self.CallChecker]
    else:
      checkers = None

    self.Info("IP Traffic during state change:")
    self.EndIPCounters()
    self.StartIPCounters()

    self.TakeCurrentMeasurements(checkers)

    self.Info(DUT.GetTimeInfo())
    self.Info(cf.environment.testset.GetUSFBler())
    for errcode in cf.environment.testset.Errors():
      self.Diagnostic(errcode)
    self.Info("IP Traffic during measurement cycle:")
    self.EndIPCounters()

    return self.Passed("Collection complete.")


class CurrentDrawSuite(common.DroidBaseSuite):
  pass


def StateFilter(updatestate, syncstate, wifistate, audiostate, callstate,
      airplanestate):
  """Filters out invalid or unwanted combinations from the series generator.
  """
  if callstate == ON and updatestate == ON and wifistate == OFF:
    return False
  if callstate == ON and syncstate == OFF:
    return False
  # Don't care about audio signal if there is no call.
  if callstate == OFF and audiostate == ON:
    return False
  # updates don't matter if not syncing.
  if syncstate == OFF and updatestate == ON:
    return False
  if airplanestate == ON and (callstate == ON or wifistate == ON or
        syncstate == OFF):
    return False
  return True


def GetSuite(conf):
  # Adjusted for more efficient testing. Radio state varies least often,
  # call state second least, etc. Starting state is first column.
  updatestates = [OFF, ON]
  syncstates = [ON, OFF]
  wifistates = [OFF]
  audiostates = [OFF, ON]
  callstates = [OFF, ON]
  airplanestates = [OFF]

  suite = CurrentDrawSuite(conf)

  suite.AddTestSeries(CollectCurrentDraw, 
      # Note: leftmost argument varies fastest.
      args=(updatestates, syncstates, wifistates, audiostates, callstates, 
          airplanestates),
      filter=StateFilter)
  # One last combination that is the same as the first one. This is to
  # test if the device "settles" back into a mode similar to a fresh boot.
  suite.AddTest(CollectCurrentDraw, OFF, ON, OFF, OFF, OFF, OFF)
  return suite

def Run(conf):
  suite = GetSuite(conf)
  suite.Run()


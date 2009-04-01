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



"""One-line documentation for XXX module.

A detailed description of XXX.
"""

__author__ = 'dart@google.com (Keith Dart)'


from droid.qa import core
from testcases.android import interactive
from testcases.android import common



class DownlinkAudioSINAD(interactive.AndroidInteractiveMixin, core.Test):

  """
Purpose
+++++++

Verify GSM decoded audio quality combined with bluetooth.
This is a full path (uplink, downlink combined) test.


Pass criteria
+++++++++++++

The audio quality is better than 12 dB.

Start Condition
+++++++++++++++

Bluetooth is enabled and bluetooth test set is paired.

End Condition
+++++++++++++

No change.

Reference
+++++++++



Prerequisites
+++++++++++++


Procedure
+++++++++

Set testset MS audio path to ECHO.
Set bluetooth test set audio path to INOUT



"""
  def Execute(self):
    cf = self.config
    if not cf.bttestsets.use:
      return self.Incomplete("Bluetooth not in use.")
    DUT = cf.environment.DUT
    testset = cf.environment.testset
    bttestset = cf.environment.bttestset
    afanalyzer = cf.environment.afanalyzer
    afgenerator = cf.environment.afgenerator
    afgenerator.SetOutputState(False) # remove any uplink noise

    self.Info("Preparing instruments.")
    freq = cf.get("frequency", 1000.0)
    # override necessary config for this measurement test.

    if freq == 1000.0:
      testset.downlinkaudio = "sin1000"
    elif freq == 3000.0:
      testset.downlinkaudio = "sin3000"
    else:
      return self.Incomplete("Invalid frequency setting. Use 1000 or 3000.")

    cf.audioanalyzer.dosinad = True
    cf.audioanalyzer.frequency = freq
    bttestset.audiopath = "inout"

    afanalyzer.Prepare(cf)

    self.MakeACall()
    self.Sleep(3)
    self.Info("Taking SINAD measurement.")
    try:
      disp = afanalyzer.Perform()
      self.Sleep(3)
    finally:
      self.HangupCall()

    if disp:
      self.Info(" Frequency: %s" % afanalyzer.GetFrequency())
      self.Info("   Voltage: %s" % afanalyzer.GetVoltage())
      self.Info("Distortion: %s %%" % afanalyzer.GetDistortion())
      sinad = afanalyzer.GetSINAD()
      self.Info("     SINAD: %s dB" % sinad)
      if float(sinad) >= 12.0:
        return self.Passed("SINAD is 12 dB or better")
      else:
        return self.Failed("SINAD NOT greater than 12 dB")
    else:
      self.Diagnostic(disp)
      return self.Incomplete("Did not get good reading.")


class AudioSuite(core.TestSuite):
  pass

def GetSuite(conf):
  suite = AudioSuite(conf)
  if not conf.get("skipsetup", False):
    suite.AddTest(common.DeviceSetup)
    # TODO(dart) fixme: monkey patch for now, this should be automatic.
    core.InsertOptions(DownlinkAudioSINAD)
    opts = DownlinkAudioSINAD.OPTIONS
    opts.prerequisites = [core.PreReq("testcases.android.common.DeviceSetup")]
  suite.AddTest(DownlinkAudioSINAD)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


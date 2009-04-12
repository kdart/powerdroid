#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""One-line documentation for XXX module.

A detailed description of XXX.
"""

__author__ = 'dart@google.com (Keith Dart)'


from testcases.android import common


class BasicBluetooth(common.DroidBaseTest):

  """
Purpose
+++++++

Verify basic bluetooth headset connectivity.

Pass criteria
+++++++++++++

A phone call is made and bluetooth headset can answer call.


Start Condition
+++++++++++++++

No voice call is active.


End Condition
+++++++++++++

No change.


Reference
+++++++++


Prerequisites
+++++++++++++

testcases.android.common.DeviceSetup

Procedure
+++++++++

Initiate a voice call from the network (simulator). 
Verify call is active.

"""

  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def Execute(self):
    cf = self.config
    if not cf.bttestsets.use:
      return self.Incomplete("Bluetooth not in use.")
    DUT = cf.environment.DUT
    bttestset = cf.environment.bttestset
    self.MakeACall(user=False)
    if not bttestset.IsCallActive():
      return self.Failed("Bluetooth headset indicates no active call.")
    self.HangupCall()
    return self.Passed("Bluetooth headset was active.")


class DownlinkAudioSINAD(common.DroidBaseTest):

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

  PREREQUISITES = ["testcases.android.audio.BasicBluetooth"]

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



#Bluetooth
#speaker/mic
#speakerphone
#external headset (HTC)
#MP3 playback
#in-call
#Volume controls
#Silent mode


class AudioSuite(common.DroidTestSuite):
  pass

def GetSuite(conf):
  suite = AudioSuite(conf)
  suite.AddTest(DownlinkAudioSINAD)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


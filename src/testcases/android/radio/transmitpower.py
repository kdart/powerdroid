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
Transmitter power measurements.
-------------------------------

Measure transmitter radiated power and power consumption.

"""

__version__ = "$Revision$"


from droid.qa import core

from testcases.android import common



class VoiceCallTransmitPower(common.DroidBaseTest): 
  """
Purpose
+++++++

Measure the relationship between MS TX power level setting, actual
transmit power, and DC current draw.  Note that the MS TX level is a
number that actually indicates a reduction, in 2 dB steps, from maximum
power.

This test uses the arbitrary distance values that map to PGSM and PCS
power level values.


Pass Criteria
+++++++++++++

None

Start Condition
+++++++++++++++

Basic setup.

End Condition
+++++++++++++

DUT is transmitting at maximum power.


Prerequisites
+++++++++++++

  testcases.android.common.DeviceSetup

Procedure
+++++++++

1. Set MS TX power to lowest level (which is highest number, 31).
2. For each distance value, perform:
  - Measure received transmit power.
  - Take long sample of current measurements.

"""
  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def MeasureCall(self, txmeasurer):
    cf = self.config
    env = cf.environment
    testset = env.testset

    datafile = self.GetFile("voicetransmitpower", "dat")
    self.Info("Data file path: %r" % (datafile.name,))
    datafile.write("# 'Distance (n)'\t'Power (dBm)'\n")

    for distance in ("d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8",
        "d9", "d10", "d11", "d12", "d13", "d14", "d15", "d16", "d17"):
      testset.SetDistance(distance)
      self.TakeCurrentMeasurements([self.CallChecker],
          metadata={"distance": distance.upper()})
      rxpower = txmeasurer.Perform()
      self.Info("MS TX level @ %s = %s." % (distance, rxpower))
      datafile.write("%s\t%s\n" % (distance[1:], float(rxpower)))
    datafile.close()
    for errcode in testset.Errors():
      self.Diagnostic(errcode)

  def CheckCall(self):
    cf = self.config
    if not cf.environment.testset.callcondition.connected:
      self.Diagnostic("Call is not active.")
      cf.environment.DUT.CallInactive()
      for errcode in cf.environment.testset.Errors():
        self.Diagnostic(errcode)
      raise core.TestFailError("Call dropped after measurement.")

  def Execute(self, downlinkaudio, uplinkaudio):
    cf = self.config
    env = cf.environment
    txmeasurer = env.testset.GetTransmitPowerMeasurer()
    txmeasurer.Prepare(cf)
    if downlinkaudio:
      self.DownlinkAudioOn()
    else:
      self.DownlinkAudioOff()
    if uplinkaudio:
      self.UplinkAudioOn()
    else:
      self.UplinkAudioOff()
    self.MakeACall(user=True)
    self.MeasureCall(txmeasurer)
    self.CheckCall()
    self.HangupCall(user=False)
    return self.Passed("Completed.")


class DataTransmitPower(common.DroidBaseTest): 
  """
Purpose
+++++++

Measure the relationship between MS TX power level setting (distance),
and DC current draw for data activity (saturated channel).


Pass Criteria
+++++++++++++

None

Start Condition
+++++++++++++++

Basic setup.

End Condition
+++++++++++++

DUT will be transmitting at maximum power.


Prerequisites
+++++++++++++

  testcases.android.common.DeviceSetup

Config Parameters
+++++++++++++++++

uplinks: (integer) number of uplink GSM channels (default: 2).
downlinks: (integer) number of downlink GSM channels (default: 3).

Procedure
+++++++++

- Set MS TX power to lowest level (which is highest number, 31).
- Repeat the following for each defined distance value:
  - Start netperf tool, delayed 90 seconds.
  - Take long sample of current measurements (at least 5 minutes).
  - Copy and write netperf output to local disk (test results area).

Note that the current (I) data file should be sliced at the 50 second to the
200 second marks for accurate average current calculation.

For example::

  pdreport -m sum -t 50,200 DataTransmitPower-*.dat

"""
  PREREQUISITES = ["testcases.android.common.DeviceSetup"]


  def MeasureDataCurrent(self):
    cf = self.config
    env = cf.environment
    testset = env.testset
    testset.SetMultiSlotConfig(
        downlinks=cf.get("downlinks", 3),
        uplinks=cf.get("uplinks", 2))
    dlchans, ulchans = testset.GetMultiSlotConfig()
    self.Info("Channels: downlink: %s, uplink: %s" % (dlchans, ulchans))
    npcmd = "netperf -H 192.168.1.1,inet -t TCP_STREAM -f k -l 180"
    for distance in ("d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8",
        "d9", "d10", "d11", "d12", "d13", "d14", "d15", "d16", "d17"):
      self.Info("Distance: %s" % distance)
      testset.SetDistance(distance)
      env.DUT.Daemonize(npcmd, outfile="/sdcard/np.txt", delay=90)
      self.TakeCurrentMeasurements(metadata=
          {"distance": distance.upper(), "channels": ulchans})
      npname = self.GetFilename(
          "netperf_level%s_chan%s" % (distance, ulchans), "txt")
      env.DUT.CopyFileFromDevice(npname, "/sdcard/np.txt")
    for errcode in testset.Errors():
      self.Diagnostic(errcode)

  def Initialize(self):
    super(DataTransmitPower, self).Initialize()
    self.DownlinkAudioOff()
    self.UplinkAudioOff()
    self.HangupCall(user=False)

  def Execute(self):
    cf = self.config
    env = cf.environment
    if cf.timespan < 300:
      raise core.TestIncompleteError("Need at least 300 second timespan")
    if not env.testset.IsPDPAttached():
      raise core.TestIncompleteError("Need PDP context active.")
    self.MeasureDataCurrent()
    return self.Passed("Completed.")


class CallMeasurementSuite(common.DroidBaseSuite):
  pass


def GetSuite(conf):
  suite = CallMeasurementSuite(conf)
  suite.AddTest(VoiceCallTransmitPower, False, False)
  suite.AddTest(VoiceCallTransmitPower, True, False)
# There is currently no means to supply uplink audio.
# When there is these tests can be enabled (uncommented)
#  suite.AddTest(VoiceCallTransmitPower, False, True)
#  suite.AddTest(VoiceCallTransmitPower, True, True)
  suite.AddTest(DataTransmitPower)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


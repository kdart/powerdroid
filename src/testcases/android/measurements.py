#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Mixin classes for measurement functions.

"""

import os
import shutil

from droid.qa import core
from droid.measure import core as measurecore
from droid.measure import sequencer
from droid.storage import datafile


class MeasurementsMixin(object):
  """A mixin class for core.Test classes that provides instrument
  measurement methods.
  *Must* be mixed in with a core.Test subclass.
  """


  def GetMetadata(self, extra=None):
    """Construct a metadata mapping.
    """
    rv = {}
    rv["testname"] = self.test_name.split(".")[-1]
    rv["starttime"] = self.GetStartTimestamp()
    rv.update(self.config.environment.DUT.states)
    if extra is not None:
      rv.update(extra)
    return rv

  def SaveMeasurementFile(self, metadata=None):
    cf = self.config
    metadata = self.GetMetadata(metadata)
    metadata["voltage"] = int(cf.powersupplies.voltage * 100)
    fpdir = datafile.GetDirectoryName(cf)
    datafile.MakeDataDir(fpdir)
    fpname = datafile.GetFileName(metadata)
    tmpfile = cf.datafilename
    dest = "%s/%s" % (fpdir, fpname)
    if tmpfile and os.path.exists(tmpfile):
      shutil.move(tmpfile, dest)
      self.Info("Created data file %r." % (dest,))
      os.chmod(dest, 0440)
    return dest

  def _TakeVoltageMeasurements(self, checkers):
    from droid.measure import voltage
    cf = self.config
    seq = sequencer.Sequencer(cf)
    vm = voltage.VoltageMeasurer(cf)
    seq.AddFunction(vm, cf.delay)
    if checkers:
      checkerdelay = len(checkers)
      for i, checker in enumerate(checkers):
        seq.AddFunction(checker, 300, delay=checkerdelay+i)
    self.Info("Taking voltage measurements.")
    cf.UI.printf("Please wait.")
    try:
      seq.Run()
    finally:
      sequencer.SequencerClose()

  def TakeVoltageMeasurements(self, checkers=None, delay=5.0, metadata=None):
    cf = self.config
    cf.datafilename = "/var/tmp/voltage.dat"
    env = cf.environment
    self.DisconnectDevice()
    self.Sleep(float(cf.get("measuredelay", delay)))
    try:
      self._TakeVoltageMeasurements(checkers)
    finally:
      self.ConnectDevice()
      env.DUT.ActivateUSB()
    if not cf.flags.DEBUG:
      self.SaveMeasurementFile(metadata)

  def _TakeCurrentMeasurements(self, checkers, delay):
    from droid.measure import current
    cf = self.config
    cf.datafilename = "/var/tmp/current.dat"
    ps = cf.environment.powersupply
    # this re-verifies USB is not connected by checking for negative
    # current (charger on).
    dccurrent = ps.MeasureDCCurrent()
    if float(dccurrent) < 0.0:
      raise core.TestSuiteAbort(
          "USB seems to be charging DUT. Current is: %s." % dccurrent)
    seq = sequencer.Sequencer(cf)
    usboff = measurecore.ChargerOff(cf)
    currentmeasurer = current.PowerCurrentMeasurer(cf)
    seq.AddFunction(usboff, 0, delay=5.0)
    seq.AddFunction(currentmeasurer, currentmeasurer.measuretime, 
        delay=float(cf.get("measuredelay", delay)))
    if checkers:
      checkerdelay = len(checkers)
      for i, checker in enumerate(checkers):
        seq.AddFunction(checker, 10, delay=checkerdelay+i)
    self.Info("Taking measurements for %s seconds." % (cf.timespan,))
    cf.UI.printf("Please wait.")
    try:
      seq.Run()
    finally:
      sequencer.SequencerClose()

  def TakeCurrentMeasurements(self, checkers=None, delay=60.0, metadata=None):
    cf = self.config
    env = cf.environment
    self.DisconnectDevice()
    try:
      self._TakeCurrentMeasurements(checkers, delay)
    finally:
      self.ConnectDevice()
      env.DUT.ActivateUSB()
    if not cf.flags.DEBUG:
      self.SaveMeasurementFile(metadata)

  def StartIPCounters(self):
    cf = self.config
    self.counters = cf.environment.testset.GetIPCounters()

  def EndIPCounters(self):
    cf = self.config
    endcounters = cf.environment.testset.GetIPCounters()
    startcounters = self.counters
    del self.counters
    self.Info("OTA network traffic counts:\n%s" % (
        endcounters - startcounters))

  def CallChecker(self, timestamp, lastvalue):
    """Can be used as a call connected checker for measurements."""
    if not self.config.environment.testset.callcondition.connected:
      self.config.environment.DUT.CallInactive()
      raise core.TestFailError("Call dropped at %s." % timestamp)
    return lastvalue




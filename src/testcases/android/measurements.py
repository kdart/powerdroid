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



"""Mixin classes for measurement functions.

"""

import os
import shutil

from droid.qa import core
from droid.qa import constants
from droid.measure import sequencer
from droid.storage import datafile


class MeasurementsMixin(object):
  """A mixin class for core.Test classes that provides instrument
  measurement methods.
  *Must* be mixed in with a core.Test subclass.
  """
  def Initialize(self):
    cf = self.config
    cf.datafiles.name = "/var/tmp/droid_measure"

  def Finalize(self, result):
    cf = self.config
    cf.logfile.note(str(cf.environment.DUT))
    fpdir = datafile.GetDirectoryName(cf)
    fpname = datafile.GetFileName(self)
    if result == constants.PASSED and not cf.flags.DEBUG:
      datafile.MakeDataDir(fpdir)
      tmpfile = cf.datafiles.name + ".dat"
      dest = "%s/%s" % (fpdir, fpname)
      if tmpfile and os.path.exists(tmpfile):
        shutil.move(tmpfile, dest)
        self.Info("Created data file %r." % (dest,))
        os.chmod(dest, 0440)
    self.Info("Collecting bug report.")
    cf.environment.DUT.BugReport(cf.logfile)

  def TakeVoltageMeasurements(self, checkers=None):
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
      sequencer.Close()

  def TakeCurrentMeasurements(self, checkers=None):
    from droid.measure import current
    cf = self.config
    ps = cf.environment.powersupply
    # this re-verifies USB is not connected by checking for negative
    # current (charger on).
    dccurrent = ps.MeasureDCCurrent()
    if float(dccurrent) < 0.0:
      raise core.TestSuiteAbort(
          "USB seems to be charging DUT. Current is: %s." % dccurrent)
    seq = sequencer.Sequencer(cf)
    cm = current.PowerCurrentMeasurer(cf)
    seq.AddFunction(cm, cm.measuretime)
    if checkers:
      checkerdelay = len(checkers)
      for i, checker in enumerate(checkers):
        seq.AddFunction(checker, 10, delay=checkerdelay+i)
    self.Info("Taking measurements for %s seconds." % (cf.timespan,))
    cf.UI.printf("Please wait.")
    try:
      seq.Run()
    finally:
      sequencer.Close()

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
    if not self.config.environment.testset.callcondition.connected:
      self.config.environment.DUT.CallInactive()
      raise core.TestFailError("Call dropped at %s." % timestamp)
    return lastvalue




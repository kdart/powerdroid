#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#
# Copyright The Android Open Source Project
#
# Note that docstrings are in RST format:
# <http://docutils.sourceforge.net/rst.html>.


"""
Measure radio/call handling versus battery level
------------------------------------------------


"""

__version__ = "$Revision$"


from pycopia import aid
#from pycopia import timelib
#from droid import adb
from droid.qa import core

from testcases.android import interactive


class BatteryEffectTest(interactive.AndroidInteractiveMixin, core.Test):
  """
Purpose
+++++++

Measure relation between battery voltage and call handling.

Pass criteria
+++++++++++++

None

Start Condition
+++++++++++++++

No call active.

End Condition
+++++++++++++

No change

Reference
+++++++++

None

Prerequisites
+++++++++++++

None

Procedure
+++++++++

Start at maximum battery voltage (4.2 volts). 
Bring up a voice call.
Step down voltage in 0.01 volt increments until it reaches minimum value
(2.8 volts)
For each increment:
  check that the call is still active.
  If the call drops before the normal cutoff, grab a bug report.

"""

  def Initialize(self):
    cf = self.config
    env = cf.environment
    self.Info("Setting maximum battery and rebooting.")
    env.powersupply.SetVoltage(4.2)
    env.DUT.Reboot()
    self.Sleep(60)
    self.WaitForRuntime()
    self.MakeACall(True)
    self.DisconnectDevice()
    self.Sleep(5)

  def Execute(self):
    self.Info("Starting.")
    cf = self.config
    env = cf.environment
    env.testset.ClearErrors()
    for v in aid.frange(4.2, 2.8, -0.01):
      env.powersupply.SetVoltage(v)
      self.config.UI.Print("voltage at: %s." % (v,))
      self.Sleep(10)
      if not env.testset.callcondition.connected:
        env.DUT.CallInactive()
        for errcode in cf.environment.testset.Errors():
          self.Info(errcode)
        if v >= 3.0:
          self.ConnectDevice()
          env.DUT.ActivateUSB()
          batt = env.DUT.GetBatteryInfo()
          self.Info("Voltage: %s  level: %s" % (v, batt.capacity))
          return self.Failed("Called dropped at voltage: %s" % (v,))
    return self.Passed("Done. Call did not drop.")

  def Finalize(self, outcome):
    cf = self.config
    env = cf.environment
    env.powersupply.SetVoltage(3.8)
    self.ConnectDevice()
    self.HangupCall()


class BatteryEffectSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = BatteryEffectSuite(conf)
  suite.addTest(BatteryEffectTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


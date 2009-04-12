#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project


"""Camera related power tests.

"""

import os

from droid.qa import core



class BLERTests(core.Test):
  pass


class EGPRSBitError(BLERTests):
  """
Purpose
+++++++

Perform a EGPRS Bit Error measurement.

Pass criteria
+++++++++++++

BER ratio is zero.

Start Condition
+++++++++++++++

Test set in EGPRS active cell mode.

End Condition
+++++++++++++

No change.

Reference
+++++++++


Prerequisites
+++++++++++++


Procedure
+++++++++

Invoke testset's EGPRS SRB bit error measurer. 
Check that the report is zero BER ratio.

"""
  def Execute(self):
    cf = self.config
    testset = cf.environment.testset
    self.Info(cf.measure.srbber)
    measurer = testset.GetEGPRSBitErrorMeasurer()
    rpt = measurer.Measure(cf)
    self.SaveData(rpt.error_ratio)
    if rpt.error_ratio == 0.0:
      self.Info(rpt)
      return self.Passed("BER is zero.") 
    else:
      self.Diagnostic(rpt)
      return self.Failed("BER is not zero.") 


class FindZeroErrorPoint(BLERTests):
  """
Purpose
+++++++

Perform a EGPRS Bit Error measurement at various power levels, seek the
txpower level that just achieves zero errors.

Pass criteria
+++++++++++++

BER ratio is zero.

Start Condition
+++++++++++++++

Test set in EGPRS active cell mode.

End Condition
+++++++++++++

No change.

Reference
+++++++++


Prerequisites
+++++++++++++


Procedure
+++++++++


"""
  def Execute(self):
    cf = self.config
    testset = cf.environment.testset
    self.Info(cf.measure.srbber)
    testset.txpower = -65.0
    measurer = testset.GetEGPRSBitErrorMeasurer()
    measurer.Prepare(cf)
    errcount = 0
    while True:
      rpt = measurer.Perform()
      if rpt.error_ratio == 0.0:
        self.Info(testset.txpower)
        errcount = 0
      else:
        self.Diagnostic("At %s, got %s BER." % (testset.txpower, rpt.error_ratio))
        if errcount > 2:
          txerr = testset.txpower + 2.0
          measurer.Finish()
          return self.Passed("TX power: %s" % txerr) 
        errcount += 1
      testset.txpower -= 1.0
      if testset.txpower < -110.0:
        measurer.Finish()
        return self.Failed("Did not find reasonable min tx power level.")


class BLERSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = BLERSuite(conf)
  suite.AddTest(EGPRSBitError)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


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


class BLERSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = BLERSuite(conf)
  suite.AddTest(EGPRSBitError)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


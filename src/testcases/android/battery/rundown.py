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




"""

"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"



from droid.qa import core


class BatteryRundownTest(core.Test):
  """
Purpose
+++++++

Measure voltage and current of an actual battery discharging.

Pass criteria
+++++++++++++

None

Start Condition
+++++++++++++++

Test bed is set up to use the battery run-down test jig, and a fully
charged battery is connected to it.

End Condition
+++++++++++++

Battery is depleted.

Reference
+++++++++

None

Prerequisites
+++++++++++++

None

Procedure
+++++++++



"""
  def Execute(self):
    cf = self.config
    env = cf.environment
    self.Info("Starting battery rundown.")

    return self.Passed("Done.")



class BatteryRundownSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = BatteryRundownSuite(conf)
  suite.AddTest(BatteryRundownTest)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


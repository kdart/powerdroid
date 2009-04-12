#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#
# Copyright 2006 The Android Open Source Project
#
# Note that docstrings are in RST format:
# <http://docutils.sourceforge.net/rst.html>.
#
# The docstring headings map to testcase fields, so the names should not
# be changed.


"""Calling Tests

Test calling out from the device.
"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"


from droid.qa import core
from testcases.android import interactive

# A common base class for all tests in a module is useful for common helper
# methods.
class CallBaseTest(core.Test):
  pass

# The actual test implementation class. There may be more than one of
# these. Fill in the appropriate docstring sections as accurately as
# possible.

class CallTest(CallBaseTest, 
        interactive.AndroidInteractiveMixin):
  """
Purpose
+++++++

Calling out from the device using the USB interface.

Pass criteria
+++++++++++++

Call is activated.

Start Condition
+++++++++++++++

No call is active.

End Condition
+++++++++++++

No change.

Reference
+++++++++

None.

Prerequisites
+++++++++++++

None

Procedure
+++++++++

Use the Call method on the DUT.

"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    self.ConnectDevice()
    number = cf.get("dial", "4083486488")
    self.Info("Dialing %r" % number)
    DUT.Call(number)
    self.Sleep(20)
    self.Info("Hanging up")
    DUT.Hangup()
    return self.Passed("Dialed call")


class CallSuite(core.TestSuite):
  pass


def GetSuite(conf):
  suite = CallSuite(conf)
  suite.AddTest(CallTest)
  return suite

def Run(conf):
  suite = GetSuite(conf)
  suite.Run()


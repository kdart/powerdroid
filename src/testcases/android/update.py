#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#
# Copyright The Android Open Source Project
#
# The docstring headings map to testcase fields, so the names should not
# be changed.


"""Update the device.

This module just provides a suite with the DeviceUpdate test case added.
"""

__author__ = 'dart@google.com (Keith Dart)'
__version__ = "$Revision$"


from droid.qa import core

from testcases.android import common


def GetSuite(conf):
  # create the suite with the passed-in configuration object.
  suite = core.TestSuite(conf)
  suite.addTest(common.DeviceUpdate)
  return suite


def Run(conf):
  suite = GetSuite(conf)
  suite()


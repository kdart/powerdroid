#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Droid universal constants and enumerations.

"""

__author__ = 'dart@google.com (Keith Dart)'

from pycopia import aid

# results a test object can produce.
TESTRESULTS = aid.Enums(PASSED=1, FAILED=0, INCOMPLETE=-1, ABORT=-2, NA=-3,
                    EXPECTED_FAIL=-4)
TESTRESULTS.sort()
[EXPECTED_FAIL, NA, ABORT, INCOMPLETE, FAILED, PASSED] = TESTRESULTS

# PASSED: Execute() passed, and the suite may continue.
# FAILED: Execute() failed, but the suite can continue. You may also raise a
# TestFailError exception.
# INCOMPLETE: Execute() could not complete, and the pass/fail criteria
# could not be determined. but the suite may continue. You may also raise
# a TestIncompleteError exception.
# ABORT: Execute() could not complete, and the suite cannot continue.
# Raising TestSuiteAbort has the same effect.
# NA: A result that is not applicable (e.g. it is a holder of tests).
# EXPECTED_FAIL: Means the test is failing due to a bug, and is already
# known to fail. 

# Default report message.
NO_MESSAGE = "no message"

# Type of objects the TestRunner can run, and reports can be generated
# from.
OBJECTTYPES = aid.Enums("module", "TestSuite", "Test", "TestRunner", "unknown")
[MODULE, SUITE, TEST, RUNNER, UNKNOWN] = OBJECTTYPES

# Types of serialized data that can be stored in the database.
DATATYPES = aid.Enums("pickle", "repr", "text", "json", "BER", "java", 
            "packed", "XDR")
[DT_PICKLE, DT_REPR, DT_TEXT, DT_JSON, 
  DT_BER, DT_JAVA, DT_PACKED, DT_XDR] = DATATYPES


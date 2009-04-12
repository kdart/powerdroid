#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Constants and enumerations used throughout the 'droid framework.
"""

__author__ = 'dart@google.com (Keith Dart)'

from pycopia import aid


OFF = aid.Enum(0, "OFF")
ON = aid.Enum(1, "ON")
UNKNOWN = aid.Enum(-1, "UNKNOWN")


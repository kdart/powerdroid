#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Power Droid specific exceptions.

"""

__author__ = 'dart@google.com (Keith Dart)'



class Error(Exception):
  pass

class DroidError(Error):
  """General framework error."""

class OperationalError(DroidError):
  """Caller did something out of sequence."""



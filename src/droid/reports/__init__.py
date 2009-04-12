#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
# $Id$
#
# Copyright The Android Open Source Project
#

"""Droid reporting interface.

"""

__author__ = 'dart@google.com (Keith Dart)'



class Report(object):
  """Abstrace base class for measurement reporting."""

  def __init__(self, **kwargs):
    self.Initialize(**kwargs)

  def close(self):
    pass

  def fileno(self):
    return None

  def Initialize(self, **kwargs):
    pass

  def Finalize(self, **kwargs):
    pass

  def SetColumns(self, *args):
    """Sets the column headings."""
    raise NotImplementedError

  def WriteRecord(self, *args):
    """Write a record from objects."""
    raise NotImplementedError

  def WriteTextRecord(self, *args):
    """Write a record where all arguments are strings (faster)."""
    raise NotImplementedError

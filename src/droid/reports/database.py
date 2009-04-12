#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
# $Id$
#
# Copyright The Android Open Source Project
#

"""Reports for writing to databases.
"""

__author__ = 'dart@google.com (Keith Dart)'


from droid.reports import Report


class DataBaseReport(Report):

  def Initialize(self, database, host="localhost"):
    pass

  def close(self):
    pass

  def SetColumns(self, *args):
    raise NotImplementedError

  def WriteRecord(self, *args):
    raise NotImplementedError



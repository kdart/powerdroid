#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Reports used by the measurement system. 

These write to text files in various formats.
"""

__author__ = 'dart@google.com (Keith Dart)'

import sys
import os

from droid.reports import core


class FileReport(core.BaseDatafile):
  EXTENSION = ".txt"
  filename = None

  def __init__(self, context):
    self._filename = context.datafilename

  name = property(lambda self: self.filename)

  def Initialize(self):
    if self._filename == "-":
      self._fo = sys.stdout
      self.filename = "<stdout>"
      self._doclose = False
    else:
      basename, ext = os.path.splitext(self._filename)
      self.filename = basename + self.EXTENSION
      self._fo = open(self.filename, "w")
      self._doclose = True

  def Finalize(self):
    if self._fo is not None:
      if self._doclose:
        self._fo.close()
      self._fo = None

  def SetColumns(self, *args):
    self._fo.write("\t".join([repr(a) for a in args]))
    self._fo.write("\n")

  def WriteRecord(self, *args):
    self._fo.write("\t".join([repr(a) for a in args]))
    self._fo.write("\n")

  def WriteTextRecord(self, *args):
    self._fo.write("\t".join(args))


class CsvReport(FileReport):
  EXTENSION = ".csv"

  def Initialize(self):
    import csv
    super(CsvReport, self).Initialize()
    self._csv = csv.writer(self._fo)

#  def Finalize(self):
#    super(CsvReport, self).Finalize()
#    self._csv.close()
#    del self._csv

  def SetColumns(self, *args):
    self._csv.writerow(args)

  def WriteRecord(self, *args):
    self._csv.writerow(args)

  def WriteTextRecord(self, *args):
    self._csv.writerow([s.strip() for s in args])


class GnuplotReport(FileReport):
  EXTENSION = ".dat"

  def SetColumns(self, *args):
    self._fo.write("# ")
    self._fo.write("\t".join([repr(a) for a in args]))
    self._fo.write("\n")

  def WriteRecord(self, *args):
    self._fo.write("\t".join([repr(a) for a in args]))
    self._fo.write("\n")

  def WriteTextRecord(self, *args):
    self._fo.write("\t".join(args))




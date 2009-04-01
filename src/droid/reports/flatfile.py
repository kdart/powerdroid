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



"""Reports used by the measurement system. 

These write to text files in various formats.
"""

__author__ = 'dart@google.com (Keith Dart)'

import sys

from droid.reports import Report


class FileReport(Report):
  EXTENSION = ".txt"

  def Initialize(self, filename=None, filelike=None, **kwargs):
    if filename:
      self._fo = open(filename + self.EXTENSION, "w")
      self._doclose = True
    elif filelike:
      self._fo = filelike
      self._doclose = False
    else:
      raise ValueError("Must supply filename or filelike parameters.")

  def Finalize(self):
    pass

  name = property(lambda s: s._fo.name)

  def __del__(self):
    if self._fo is not None:
      self.close()

  def close(self):
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

  def Initialize(self, **kwargs):
    import csv
    super(CsvReport, self).Initialize(**kwargs)
    self._csv = csv.writer(self._fo)

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



def GetReport(filename, format):
  fmt = format[0].upper()
  if filename:
    if fmt == "C":
      report = CsvReport(filename=filename)
    elif fmt == "T":
      report = FileReport(filename=filename)
    elif fmt == "G":
      report = GnuplotReport(filename=filename)
    else:
        raise ValueError("Invalid report format: %r" % format)
  else:
    if fmt == "C":
      report = CsvReport(filelike=sys.stdout)
    elif fmt == "T":
      report = FileReport(filelike=sys.stdout)
    elif fmt == "G":
      report = GnuplotReport(filelike=sys.stdout)
    else:
        raise ValueError("Invalid report format: %r" % format)
  return report



#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Module that encapsulates how data files are encoded and decoded.

"""

__author__ = 'dart@google.com (Keith Dart)'


import sys
import os
import re
from errno import EEXIST

from pycopia import aid
from pycopia import dictlib
from pycopia import timelib
from pycopia import timespec

from droid import constants


ON = constants.ON
OFF = constants.OFF
UNKNOWN = constants.UNKNOWN

_STATE_RE = re.compile(r"(\w+)(ON|OFF|UNKNOWN)")
_STATEMAP = {
  "ON": ON,
  "OFF": OFF,
  "UNKNOWN": UNKNOWN,
}

_DATA_RE = re.compile(r"([a-z]+)([A-Z0-9]+)")


def GetDirectoryName(config):
  build = config.environment.DUT.build
  return "%s/%s/%s/%s" % (
      config.DATABASEDIR, 
      build.product, 
      build.type, 
      build.id)

def GetFileName(metadata):
  """Construct full data path name from a test case instance.

  Returns a tuple of directory name and file name.
  """
  fname = "%s-%s-%s.dat" % (
      metadata.pop("testname"),
      metadata.pop("starttime"),
      "-".join(["%s%s" % t for t in metadata.items()]),
      )
  return fname

def DecodeFullPathName(pathname):
  data = DataFileData()
  data.build = dictlib.AttrDict()
  data.pathname = pathname
  data.rollup = 0
  data.voltage = 0.0
  data.samples = 0
  pathname = os.path.abspath(pathname)
  dirname, fname = os.path.split(pathname)
  nameparts = fname.split("-")
  dirparts = dirname.split("/")
  if "data" in dirparts:
    data.build.id = dirparts[-1]
    data.build.type = dirparts[-2]
    data.build.product = dirparts[-3]
  else:
    data.build = None
  try:
    mt = timelib.strptime_mutable(nameparts[1], "%m%d%H%M%S")
  except:
    data.timestamp = timelib.localtime_mutable(os.path.getmtime(pathname))
  else:
    mt.set_format("%a, %d %b %Y %H:%M:%S %Z")
    # year info is not encoded in the timestamp, so get it from file system.
    mtime = timelib.localtime_mutable(os.path.getmtime(pathname))
    mt.year = mtime.tm_year
    data.timestamp = mt
  data.testcase = nameparts[0]

  if len(nameparts) > 1:
    endoffset = -1
    try:
      data.voltage = float(nameparts[endoffset].split(".")[0]) / 100.0
    except (ValueError, TypeError, IndexError):
      try:
        data.rollup = timespec.parse_timespan(nameparts[endoffset].split(".")[0])
        endoffset -= 1
      except ValueError:
        data.rollup = 0
      try:
        data.voltage = float(nameparts[endoffset].split(".")[0]) / 100.0
      except (ValueError, TypeError, IndexError):
        data.voltage = 0.0
    endoffset -= 1
    try:
      data.samples = int(nameparts[endoffset])
    except (ValueError, TypeError, IndexError):
      data.samples = 0

    for part in nameparts[2:endoffset]:
      mo = _STATE_RE.match(part)
      if mo:
        data[mo.group(1)] = _STATEMAP[mo.group(2)]
      else:
        mo = _DATA_RE.match(part)
        if mo:
          data[mo.group(1)] = mo.group(2)
        else:
          print >>sys.stderr, "Warning: name component not matched: %r" % (part,)

  return data


def MakeDataDir(fpdir):
  try:
    os.makedirs(fpdir)
  except OSError, error:
    if error[0] == EEXIST:
      pass
    else:
      raise


class DataFileData(dictlib.AttrDict):
  def __str__(self):
    s = ["Data Summary:"]
    build = dict.__getitem__(self, "build")
    s.append("     from file: %r" % self["pathname"])
    s.append("      testcase: %s" % self["testcase"])
    if build:
      s.append(" build.product: %s" % build.product)
      s.append("    build.type: %s" % build.type)
      s.append("      build.id: %s" % build.id)
    s.append("        rollup: %s" % self.rollup)
    s.append("       voltage: %s" % self.get("voltage", UNKNOWN))
    s.append("    subsamples: %s" % self.get("samples", UNKNOWN))
    for name, value in self._GetStates().items():
        s.append("%14.14s: %s" % (name, value))
    return "\n  ".join(s)

  # two metadata compare equal iff states are equal.
  def __eq__(self, other):
    for name, value in self._GetStates().items():
      try:
        if other[name] != value:
          return False
      except KeyError:
        return False
    return True

  def __ne__(self, other):
    return not self.__eq__(other)

  def Compare(self, other, missingok=True):
    for name, value in self._GetStates().items():
      try:
        if other[name] != value:
          return False
      except KeyError:
        if not missingok:
          return False
    return True

  def CompareData(self, other, namelist, missingok=True):
    for name in namelist:
      try:
        if other[name] != self[name]:
          return False
      except KeyError:
        if not missingok:
          return False
    return True

  def GetFileName(self, base):
    fname = "%s-%s-%s%s.txt" % (
      base,
      self.timestamp.strftime("%m%d%H%M%S"),
      "-".join(self.GetStateStrings()),
      aid.IF(self.rollup, "-%ssec" % int(self.rollup), ""),
      )
    return fname

  def _GetStates(self):
    metadata = self.copy()
    for excname in ("testcase", "pathname", "build", "rollup",
          "samples", "voltage", "timestamp"):
      try:
        metadata.pop(excname)
      except KeyError:
        pass
    return metadata

  def GetStateStrings(self):
    metadata = self._GetStates()
    s = []
    for name, value in metadata.items():
      s.append("%s%s" % (name, value))
    return s

  def GetStateString(self, *names):
    s = []
    for name in names:
      try:
        value = self[name]
      except KeyError:
        pass
      else:
        s.append("%s%s" % (name, value))
    return "-".join(s)



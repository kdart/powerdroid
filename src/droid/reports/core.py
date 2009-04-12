#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Core report module.

Supports constructing data holder formats of various types.
"""

import os

from pycopia import dictlib
from pycopia import module

DATAFORMATS = { # name: implementation (class object)
  "txt": "droid.reports.flatfile.FileReport",
  "": "droid.reports.flatfile.FileReport",
  "gnu": "droid.reports.flatfile.GnuplotReport",
  "dat": "droid.reports.flatfile.GnuplotReport",
  "csv": "droid.reports.flatfile.CsvReport",
  "rrd": "droid.reports.rrd.RRDReport",
#  "hdf": "droid.reports.hdf5.HDF5Datafile",
#  "h5": "droid.reports.hdf5.HDF5Datafile",
#  "db": "droid.reports.database.DataBaseReport",
#  "cli": "droid.reports.clientserver.ClientReport",
#  "ser": "droid.reports.clientserver.ServerReport",
}

class DatafileError(Exception):
  pass


class BaseDatafile(object):
  """Abstract base class for measurement reporting."""

  def __init__(self, context):
    pass

  def __del__(self):
    self.Finalize()

  def Initialize(self):
    pass

  def Finalize(self):
    pass

  def SetColumns(self, *args):
    """Sets the column headings.

    Args:
      Any number of strings. The number of arguments reflects the number
      of columns in a table of data.
    """
    raise NotImplementedError

  def AddMetadata(self, metadata):
    """Add metadata to the file.

    Generally, this method can only be called before Initialize() is
    called, or after Finalize() is called. That is, the file is closed.

    Args:
      metadata: mapping of names to valus.
    """
    raise NotImplementedError

  def GetMetadata(self):
    raise NotImplementedError

  def WriteRecord(self, *args):
    """Write a record from objects."""
    raise NotImplementedError

  def WriteTextRecord(self, *args):
    """Write a record where all arguments are strings (usually faster).

    Args:
      Any number of strings.
    """
    raise NotImplementedError


class Metadata(dictlib.AttrDict):
  def __str__(self):
    s = ["Data Summary:"]
    build = dict.get(self, "build", None)
    s.append("      testcase: %s" % self["testcase"])
    if build:
      s.append(" build.product: %s" % build.product)
      s.append("    build.type: %s" % build.type)
      s.append("      build.id: %s" % build.id)
    s.append("       voltage: %s" % self.get("voltage", UNKNOWN))
    s.append("       samples: %s" % self.get("samples", UNKNOWN))
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

  def _GetStates(self):
    metadata = self.copy()
    for excname in ("testcase", "pathname", "build",
          "samples", "voltage", "timestamp"):
      try:
        metadata.pop(excname)
      except KeyError:
        pass
    return metadata


def GetDatafile(context):
  """Construct a measurement data writer object."""
  datafilename = context.datafilename
  basename, ext = os.path.splitext(datafilename)
  datafile_type = ext[1:]
  classname = DATAFORMATS[datafile_type.lower()[:3]]
  cls = module.GetObject(classname)
  rep = cls(context)
  return rep


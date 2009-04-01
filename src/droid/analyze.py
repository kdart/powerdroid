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



"""Module for analysis of data.

"""


import os
import re
import itertools

import numpy
from pycopia import timelib
from pycopia import timespec
from pycopia import aid

from droid.reports import flatfile
from droid.storage import datafile
from droid.physics import physical_quantities
PQ = physical_quantities.PhysicalQuantity


mA = PQ(1.0, "mA")
HOUR = PQ(3600.0, "s")
V = PQ(1.0, "V")

BATTERIES = {
    #           capacity           cutoff voltage
    "EXCA160": (960.0 * mA * HOUR, 2.8 * V),
    "DREA160": (1150.0 * mA * HOUR, 2.8 * V),
}

PLOT_COLORS = [
    (0.0, 0.2, 0.0, 1.0),
    (0.5, 0.0, 0.9, 0.1),
    (0.0, 0.0, 1.0, 0.1),
    (0.9, 0.0, 0.5, 0.1),
    (1.0, 0.0, 0.0, 0.1),
]

# break up column name and measurement unit.
HEADER_RE = re.compile(r'(\w+)\W*\((\w+)\)')


def TimeMarksGenerator(timespecs):
  """A generator function for generating periods of time.

  Args:
    timespecs (string) a string specifying a sequence of relative time
    values, separated by commas. Relative time values are of the form "1d"
    (for one day), "30s" (for thirty seconds), etc. 
    If a substring "..." is present (it should be last) then make
    the last two times a delta time and repeat indefinitly, incrementing
    the time value by that delta time.

  Returns:
    An iterator that yields each time mark given, as seconds (float).
  """
  last = 0.0
  lastlast = 0.0
  p = timespec.TimespecParser()
  for mark in [s.strip() for s in timespecs.split(",")]:
    if mark == "...":
      delta = last - lastlast
      tmi = TimeRepeater(last, delta)
      while 1:
        yield tmi.next()
    else:
      p.parse(mark)
      secs = p.seconds
      lastlast = last
      last = secs
      yield secs


class TimeRepeater(object):
  def __init__(self, start, step):
    self._current = start
    self._step = step

  def __iter__(self):
    return self

  def next(self):
    self._current += self._step
    return self._current


def GetHMSString(secs):
  minutes, seconds = divmod(secs, 60.0)
  hours, minutes = divmod(minutes, 60.0)
  return "%02.0f:%02.0f:%2.1f" % (hours, minutes, seconds)


def TimeSlice(measurements, start, end):
  """Return slice of array from start to end time, in seconds. 

  Time is relative to beginning of array.

  Args:
    measurements: multi-dimensional array with time stamps in first column. Array
    should be organized in rows.
    start and end are floats, in seconds. 
  """
  times = measurements.transpose()[0]
  beginning = times[0]
  starti = times.searchsorted(beginning + start)
  endi = times.searchsorted(beginning + end)
  return measurements[starti:endi]


def NormalizeTime(measurements):
  """Normalize a data array containing timestamps as the first data column
  to start at zero time.
  """
  measurements = measurements.transpose()
  # Subtract the first timestamp value from all timestamp values.
  measurements[0] = measurements[0] - measurements[0][0]
  return measurements.transpose()


def ReadArray(filename):
  """Reads an array from a file.

  The file should have been produced by an object from the
  droid.reports.flatfile module.
  """
  unused_, filetype = os.path.splitext(filename)
  fo = open(filename)
  try:
    if filetype == ".txt":
      header = map(eval, fo.readline().split("\t"))
      a = numpy.fromfile(fo, dtype="f8", sep="\n\t")
    elif filetype == ".csv":
      header = fo.readline().split(",")
      a = numpy.fromfile(fo, dtype="f8", sep=",\n")
    elif filetype == ".dat": # gnuplot report
      line1 = fo.readline()[2:].split("\t")
      try:
        header = map(eval, line1)
      except (ValueError, SyntaxError): # assume no header line
        header = line1
        fo.seek(0)
      a = numpy.fromfile(fo, dtype="f8", sep="\n")
    else:
      raise ValueError(
        "ReadArray: Invalid file type. need .txt, .csv, or .dat (got %r)." % 
        filetype)
  finally:
    fo.close()
  a.shape = (-1, len(header))
  return header, a


def MakeCharts(filename, timemarks=None, ylim=None, columns=None,
      interactive=False):
  # import pylab here since this is a very large library that you might
  # not want loaded and initialized everytime you use this module. Also,
  # if you are using one of the GTK based backends for matplotlib, and you
  # do not have DISPLAY set (e.g. running from a remote shell), then you
  # will see this exception raised when you import this module:
  # RuntimeError: could not open display
  # This is not in my, or matplotlib's, control.
  import pylab
  from matplotlib.font_manager import FontProperties
  if not interactive:
    pylab.ioff()
  font = FontProperties(size="smaller")
  names = []
  header, measurements = ReadArray(filename)
  unit = HEADER_RE.search(header[1]).group(2)
  measurements = NormalizeTime(measurements)
  # timeslice set large by default to get all data.
  if timemarks is None:
    timemarks = TimeMarksGenerator("0s,5d")
  timemarks = iter(timemarks)
  start = timemarks.next()
  for end in timemarks:
    subset = TimeSlice(measurements, start, end)
    if len(subset) > 0:

      # Y axis set to consistent values for comparisons.
      if ylim is None:
        if unit == "V":
          pylab.ylim(2.0, 4.2)
        elif unit == "A":
          pylab.ylim(-0.02, 2.5)
        elif unit == "mA":
          pylab.ylim(-20.0, 2500.0)
        # else just auto-scale.
      else:
        pylab.ylim(*ylim) # should be tuple of (min,max).

      datacolumns = subset.transpose()
      x_time = datacolumns[0]
      if len(x_time) < 100:
        mrk = "."
        ls = "-"
      else:
        mrk = ","
        ls = "None"
      datacols, headers = _GetColumns(datacolumns, header, columns)
      for col, label, color in itertools.izip(datacols,  headers,
              itertools.cycle(PLOT_COLORS) ):
        pylab.plot(x_time, col, color=color, label=label, ls=ls, marker=mrk)
      pylab.setp(pylab.gcf(), dpi=100, size_inches=(9,6))
      pylab.xlabel("Time (s)")
      pylab.ylabel(unit)
      title = "%s-%ss-%ss" % (os.path.splitext(filename)[0], int(start), int(end))
      pylab.title(title, fontsize="small")
      pylab.legend(prop=font)

      if interactive:
        pylab.show()
      else:
        fname = "%s.%s" % (title, "png")
        pylab.savefig(fname, format="png")
        names.append(fname)
        pylab.cla()
      start = end
    else:
      break
  return names


def _GetColumns(datacolumns, header, columns):
  if columns is not None: # should be tuple of column numbers, or int.
    datacols = []
    headers = []
    if type(columns) in (tuple, list):
      for n in columns:
        datacols.append(datacolumns[n])
        headers.append(header[n])
    else:
      n = int(columns)
      datacols.append(datacolumns[n])
      headers.append(header[n])
  else:
    datacols = datacolumns[1:]
    headers = header[1:]
  return datacols, [HEADER_RE.search(h).group(1) for h in headers]

def CCDFChart(filename, timemarks=None, ylim=None, interactive=False):
  pass


def PlotHistogram(filename, timemarks=None, columns=1, interactive=False):
  import pylab
  if not interactive:
    pylab.ioff()
  header, measurements = ReadArray(filename)
  unit = HEADER_RE.search(header[1]).group(2)
  measurements = NormalizeTime(measurements)
  names = []
  if timemarks is None:
    timemarks = TimeMarksGenerator("0s,5d")
  timemarks = iter(timemarks)
  start = timemarks.next()
  for end in timemarks:
    subset = TimeSlice(measurements, start, end)
    if len(subset) <= 0:
      continue
    datacolumns = subset.transpose()
    datacols, headers = _GetColumns(datacolumns, header, columns)
    for col, label, color in itertools.izip(datacols, headers,
          itertools.cycle(PLOT_COLORS)):
      hist, edges = numpy.histogram(col, 1024, (-0.1, numpy.max(col) + 0.1), True)
      pylab.plot(edges, hist, color=color, label=label) # plot it
    pylab.setp(pylab.gcf(), dpi=100, size_inches=(9,6))
    title = "histogram-%s-%s-%ss-%ss" % (
        os.path.splitext(filename)[0], "-".join(headers), int(start), int(end))
    pylab.title(title, fontsize="small")
    pylab.xlabel(unit)
    if interactive:
      pylab.show()
    else:
      fname = "%s.%s" % (title, "png")
      pylab.savefig(fname, format="png")
      pylab.cla()
      names.append(fname)
  return names


_SAMPLE = ("http://chartserver.corp.google.com/chart?" 
  "cht=bhg&"
  "chc=corp&"
  "chs=300x128&"
  "chd=s:zwq,heg,VYW&"
  "chco=008000,FFCC33,3072F3&"
  "chls=1,4,0|1,4,0|1,4,0&"
  "chdl=idle|w%2Fsync|w%2Fcall&"
  "chxt=x,y&"
  "chxl=0:|0|1|2|3|4|5|6|7|8|9|10|1:|111111|222222|333333&"
  "chxr=0,0,100|1,0,10&"
  "chxs=0,676767,9,0|1,676767,10.5,0&"
  "chtt=Battery+Life&"
  "chbh=5,2")


DASHBOARD_PARTS = "/home/android-build/dashboard_parts"


def DoDashboard(timemarks=None, battery="DREA160"):
  """Create a custom dashboard report."""
#  reports = []
#  for fname in filenames:
#    metadata = datafile.DecodeFullPathName(fname)
#    rpt = GetBatteryLifeReport(fname, timemarks, battery, metadata)
#    reports.append(rpt)
#  pngfilename = BatteryBarChart(reports)
# XXX
  from droid import cs_client


  data = {
    "111111": [8.0, 6.0, 4.0],
    "222222": [7.5, 6.5, 3.0],
    "333333": [8.5, 4.5, 3.6],
  }
  names = []
  measurements = []

  keys = data.keys()
  keys.sort()
  for name in keys:
    names.append(name)
    measurements.append(data[name])

  return cs_client.ChartTag(measurements, 300, 128, top=10, bottom=0, tick=1,
    cht="bhg",
    chc="corp",
    #chs="300x128",
    #chd="%(data)s" % data,
    chco="008000,FFCC33,3072F3",
    chls="1,4,0|1,4,0|1,4,0",
    chdl="idle|sync|call",
    chxt="x,y",
    chxl="0:|0|1|2|3|4|5|6|7|8|9|10|1:|%s" % "|".join(names),
    chxr="0,0,100|1,0,10",
    chxs="0,676767,9,0|1,676767,10.5,0",
    chtt="Battery Life",
    chbh="5,2")



def RollupTable(filename, timespan="1minute"):
  timemarks = TimeMarksGenerator("0s,%s,..." % timespan)
  newfilename = "%s-%s" % (os.path.splitext(filename)[0], timespan)
  header, arr = ReadArray(filename)
  header = header[:2] # timestamp and average value

  report = flatfile.GnuplotReport(filename=newfilename)
  report.SetColumns(*header)

  start = timemarks.next()
  for end in timemarks:
    minute = TimeSlice(arr, start, end)
    if len(minute) > 0:
      minutecolumns = minute.transpose()
      report.WriteRecord(minutecolumns[0][-1], numpy.average(minutecolumns[1]))
      start = end
    else:
      break
  report.Finalize()
  report.close()
  return newfilename + report.EXTENSION


class ArveReport(object):
  def __init__(self, fname, timemarks=None):
    self.metadata = datafile.DecodeFullPathName(fname)
    header, arr = ReadArray(fname)
    unit = HEADER_RE.search(header[1]).group(2)
    self.samplestart = arr[0][0]
    if timemarks:
      it = iter(timemarks)
      start = it.next()
      end = it.next()
      arr = TimeSlice(arr, start, end)

    self.starttime = arr[0][0]
    self.endtime = arr[-1][0]

    self.samples = len(arr)
    arr = arr.transpose()
    timecol = arr[0]
    avgvaluecol = arr[1]

    self.sampleperiod = PQ(timecol[1] - timecol[0], "s")
    self.mean = PQ(numpy.mean(avgvaluecol), unit)
    self.maximum = PQ(numpy.amax(avgvaluecol), unit)
    self.minimum = PQ(numpy.amin(avgvaluecol), unit)
    self.median  = PQ(numpy.median(avgvaluecol), unit)

  def __str__(self):
    ts = timelib.localtime_mutable(self.samplestart)
    ts.set_format("%a, %d %b %Y %H:%M:%S %Z")
    offset = GetHMSString(self.starttime - self.samplestart)
    span = GetHMSString(self.endtime - self.starttime)
    s = ["Samples started at %s.\n"
    "Report offset %s after sampling started and spans %s." % (ts, offset, span)]
    s.append(str(self.metadata))
    s.append("")
    s.append("%s %s samples:" % (self.samples, self.sampleperiod))
    s.append(" Maximum: %s" % self.maximum)
    s.append(" Minimum: %s" % self.minimum)
    s.append("    Mean: %s" % self.mean)
    s.append("  Median: %s" % self.median)
    return "\n".join(s)


class TimeSpan(object):
  def __init__(self, seconds, minutes=0, hours=0, days=0, weeks=0):
    self._seconds = (float(seconds) + minutes*60.0 + hours*3600.0 + days*86400.0 + 
        weeks*604800.0)

  seconds = property(lambda s: s._seconds)
  minutes = property(lambda s: s._seconds / 60.0)
  hours = property(lambda s: s._seconds / 3600.0)
  days = property(lambda s: s._seconds / 86400.0)

  def GetDHMS(self):
    """Return a tuple of days, hours, minutes, and seconds given a total
    count in seconds.
    """
    mins, secs = divmod(self._seconds, 60.0)
    hours, mins = divmod(mins, 60.0)
    days, hours = divmod(hours, 24.0)
    return (days, hours, mins, secs)

  def __str__(self):
    t = self.GetDHMS()
    return "%.0f days, %.0f hours, %.0f minutes, and %.1f seconds." % t

  def __repr__(self):
    return "%s(%r)" % (self.__class__.__name__, self._seconds)

  def __float__(self):
    return self._seconds

  def AsPhysicalQuantity(self):
    return PQ(self._seconds, "s")


def BatteryLifeByCurrent(measurements, unit="A", battery="EXCA160"):
  """Remove charge from the battery using the measured discrete time intervals.

  Args:
    measurements (array): An array with timestamps in the first column,
    and average current measurement in the second column. The array should
    be organized in rows. 
    unit (string): The unit that the second column, average current draw,
    is in. Usually "mA", or "A", default "A".
    battery (string): The model name of the battery that will be used to
    compute lifetime. Default "EXCA160".
  Return:
    A BatteryLifeReport containing the time span and remaining battery
    charge.
  """
  charge = BATTERIES[battery][0].inUnitsOf("C")
  zeroC = PQ(0.0, "C")
  measurements_iter = iter(measurements)
  firstrow  = measurements_iter.next()
  starttime = timeval = PQ(firstrow[0], "s")

  for row in measurements_iter:
    nexttime = PQ(row[0], "s")
    averagecurrent = PQ(row[1], unit)
    delta_t = nexttime - timeval
    charge -= (averagecurrent * delta_t)
    timeval = nexttime
    if charge <= zeroC:
      break
  return BatteryLifeReport(battery, (nexttime - starttime).value, charge, None)


def BatteryLifeByVoltage(voltagemeasurements, battery="EXCA160"):
  """Find the battery life from battery voltage data. 

  Find the cutoff point and calculate battery life by time to that point.
  The cutoff point is simply the lowest measured voltage, where the device
  would have turned itself off and the voltage increased after that.

  Args:
    voltagemeasurements (array): an array, organized as rows, with the
    first value being a timestamp, and the second a voltage reading of the
    battery under test.

  Return:
    A BatteryLifeReport containing the time span and cutoff voltage.
  """
  cutoff_spec = BATTERIES[battery][1].value
  voltagemeasurements = voltagemeasurements.transpose()
  for i, val in enumerate(voltagemeasurements[1]):
    if val < cutoff_spec:
        break
  start = voltagemeasurements[0][0]
  end = voltagemeasurements[0][i]
  cutoff = voltagemeasurements[1][i]
  return BatteryLifeReport(battery, (end - start), None, PQ(cutoff, "V"))


def GetBatteryLifeReport(fname, timemarks=None, battery=None, metadata=None):
  """Return a BatteryLifeReport given a data file of current or voltage
  measurements.
  """
  header, measurements = ReadArray(fname)
  if timemarks:
    measurements = TimeSlice(measurements, 
        timemarks.next(),
        timemarks.next())
  unit = HEADER_RE.search(header[1]).group(2)
  if unit == "V":
    rpt = BatteryLifeByVoltage(measurements, battery)
  elif unit.endswith("A"): # mA or A
    rpt = BatteryLifeByCurrent(measurements, unit, battery)
  else:
    raise ValueError, "Can't determine unit of data column."
  rpt.metadata = metadata
  return rpt


def BatteryBarChart(report_list, interactive=False):
  """Create a bar chart given a list of battery life reports."""
  # same as above.
  import pylab
  from matplotlib.font_manager import FontProperties
  from matplotlib import colors
  if not interactive:
    pylab.ioff()
  font = FontProperties(size=9)

  N = len(report_list)
  barwidth = 1.0 / N + 0.1
  build = report_list[0].metadata.build
  pylab.title(
      "Battery Life for %s-%s-%s" % (build.product, build.type, build.id))
  pylab.subplots_adjust(left=0.11, bottom=0.05, right=0.95, top=0.95)

  max_lifetime = 0.0
  for index, battery_report in enumerate(report_list):
    lifetime = float(battery_report.lifetime)
    max_lifetime = max(lifetime, max_lifetime)
    blue = aid.IF(battery_report.byvoltage, 0.0, 0.5)
    color = colors.rgb2hex(aid.IF(battery_report.estimated, 
        ((index * 0.1) % 1.0, 0, blue), 
        (0, 1.0, blue)))
    label = "(%s) %s (%.2f h)" % (index + 1, 
        battery_report.metadata.GetStateString("sync", "updates", "call", "audio"), 
        battery_report.lifetime.hours)
    pylab.bar(index, lifetime, width=barwidth, color=color, label=label)

  # Make room for unobstructed legend (wish it could be outside the plot).
  pylab.ylim(0.0, max_lifetime * 1.5) 
  pylab.xlim(-barwidth, N)
  # labels are position offset by +1.
  pylab.xticks(pylab.arange(N) + (barwidth / 2.0), 
      map(str, pylab.arange(N) + 1), 
      fontsize=10)

  pylab.ylabel('Time (s)')
  pylab.legend(prop=font)

  if interactive:
    pylab.show()
  else:
    fname = "batterylife-%s.png" % (report_list[0].metadata.timestamp.strftime("%m%d%H%M%S"))
    pylab.savefig(fname, format="png")
    return fname


class BatteryLifeReport(object):
  """Report that holds a battery life.

  This holds the essential information for computing battery life, and
  does a battery life computation when requested. 

  The "lifetime" attribute is the expected or actual time to discharge a
  fully charged battery. It is a TimeSpan object.
  The "estimated" attribute indicates whether that time is actual, or
  estimated. It is a boolean.
  The "byvoltage" attribute indicates if the time was measured by voltage
  (battery depletion) method.

  Args:
    battery (string): a battery model string (e.g. "EXCA160").
    time (float): The length of time taken for a measurement set.
    endcharge (PhysicalQuantity): a charge value, in Coloumbs, that was
      left in the battery after being discharged over the timespan given.
      This is provided for current-draw methods of measurement.
    cutoff (PhysicalQuantity): The final, cutoff, voltage of the battery.
      This is provided when the battery depletion, measured by voltage
      drop, is done. 
  """

  def __init__(self, battery, time, endcharge=None, cutoff=None):
    self.battery = battery
    self._lifetime = TimeSpan(time)
    self._actualtime = None
    self._estimated = None
    self.metadata = None
    self.endcharge = endcharge
    self.cutoff = cutoff

  def _GetLifetime(self):
    """Computes the actual or estimated battery life.

    It also provides an estimation indicator if the battery was not
    completely discharged.
    """
    if self._actualtime is not None:
      return self._actualtime
    if self.endcharge is not None:
      if self.endcharge <= PQ(0.01, "C"):
        self._actualtime = self._lifetime
        self._estimated = False
        return self._lifetime
      else:
        startcharge = BATTERIES[self.battery][0]
        delta_t = self._lifetime.AsPhysicalQuantity()
        timeavail  = delta_t / (startcharge - self.endcharge) * startcharge
        ts = TimeSpan(timeavail.value)
        self._actualtime = ts
        self._estimated = True
        return ts
    if self.cutoff is not None:
      self._actualtime = self._lifetime
      self._estimated = False
      return self._lifetime

  def _IsEstimated(self):
    if self._estimated is None:
      self._GetLifetime()
    return self._estimated

  lifetime = property(_GetLifetime, 
      doc="The expected lifetime of the battery, real or estimated.")
  estimated = property(_IsEstimated,
      doc="True if the lifetime value is estimated from current draw sample.")
  byvoltage = property(lambda self: self.cutoff is not None, 
      doc="True if this lifetime measurement was obtained by voltage method.")

  def __str__(self):
    startcharge = BATTERIES[self.battery][0]
    lt = self._GetLifetime()
    s = ["Battery life for %r (%s)%s:" % (
        self.battery, startcharge.inUnitsOf("mA*h"), 
        aid.IF(self._IsEstimated(), " (estimated)", "" ))]
    if self.cutoff is not None:
      if self.cutoff.value >= 2.9:
        s.append("Warning: Minimum point of %s is not near cutoff." % self.cutoff)
      s.append("Cutoff voltage was about: %s" % self.cutoff)
    s.append("seconds: %s\nhours: %s\n%s" % (lt.seconds, lt.hours, lt))
    return "\n".join(s)


# Functions for interactive reporting from command line.

def DoGraph(filename, timemarks=None, columns=None):
  """Make a series of graphs from the the data in file split on the time
  marks. 
  """
  names = MakeCharts(filename, timemarks, columns=columns)
  for name in names:
    print "PNG file saved to:", name

def DoHistogram(filename, timemarks=None, columns=None):
  """Make a histogram chart.
  """
  names = PlotHistogram(filename, timemarks, columns=columns)
  for name in names:
    print "PNG file saved to:", name

def DoCCDFChart(filename, timemarks=None):
  pass

def DoRollupTable(filenames, arve, timespan):
  """Create a new data set consisting of averages for one minute
  intervals.
  """
  for fname in filenames:
    newname = RollupTable(fname, timespan)
    if arve:
      DoSummary(newname)
    print newname

def DoSummary(fname, timemarks=None):
  rpt = ArveReport(fname, timemarks)
  rptfname = rpt.metadata.GetFileName("summary")
  stream = open(rptfname, "w")
  stream.write(str(rpt))
  stream.write("\n")
  stream.close()
  print rptfname

DoArveReport = DoSummary

def DoBattery(fname, timemarks=None, battery=None):
  """Do a battery life determination and write the result to a file.
  """
  metadata = datafile.DecodeFullPathName(fname)
  rpt = GetBatteryLifeReport(fname, timemarks, battery, metadata)
  rptfname = metadata.GetFileName("batterylife")
  stream = open(rptfname, "w")
  stream.write(str(metadata))
  stream.write("\n")
  stream.write(str(rpt))
  stream.write("\n")
  stream.close()
  print rptfname


def DoFullBatteryChart(filenames, timemarks=None, battery=None):
  reports = []
  for fname in filenames:
    metadata = datafile.DecodeFullPathName(fname)
    rpt = GetBatteryLifeReport(fname, timemarks, battery, metadata)
    reports.append(rpt)
  print BatteryBarChart(reports)




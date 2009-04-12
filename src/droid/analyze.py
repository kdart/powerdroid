#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Module for analysis of data. Mostly current and voltage time-domain
readings related to batteries.

"""


import os
import re
import itertools

import numpy
from pycopia import timelib
from pycopia import timespec
from pycopia import aid
from pycopia import dictlib

from droid.reports import flatfile
from droid.storage import datafile
from droid.physics import physical_quantities

# abbreviation
PQ = physical_quantities.PhysicalQuantity


mA = PQ(1.0, "mA")
HOUR = PQ(3600.0, "s")
V = PQ(1.0, "V")
mA_h = mA * HOUR

BATTERIES = {
    #           capacity           cutoff voltage
    "EXCA160": (960.0 * mA_h, 2.8 * V),
    "DREA160": (1150.0 * mA_h, 2.8 * V),
    "DREA160_USED": (1130.0 * mA_h, 2.8 * V),
    "DREA160_OLD": (977.0 * mA_h, 2.8 * V), # old means 300 cycles
    "DREA160_OLD43": (885.0 * mA_h, 2.8 * V), # old with 4.3 volt charge.
    "DIAM160": (900.0 * mA_h, 2.8 * V),
}
# Per Jack_Wang@htc.com:
# If charging voltage is 4.2V, battery capacity will be higher than 977mAh
# after 300 cycles.
# If charging voltage is 4.3V, battery capacity will be higher than 885mAh
# after 300 cycles.


PLOT_COLORS = [
    (0.0, 0.8, 0.0, 1.),
    (0.5, 0.0, 0.9, 1.),
    (0.0, 0.0, 1.0, 1.),
    (0.9, 0.0, 0.5, 1.),
    (1.0, 0.0, 0.0, 1.),
]

color_cycler = itertools.cycle(PLOT_COLORS)

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


def NormalizeTime(measurements, start=None, offset=None):
  """Normalize a data array containing timestamps as the first data column
  to start at zero time.

  Args:
    measurements (array) a numpy array containing a measurement set.
    start (float) an optional absolute time stamp to take as start time.
    offset (float) an optional relative time to offset the result.
  """
  if start is None:
    start = measurements[0][0]
  measurements = measurements.transpose()
  # Subtract the first timestamp value from all timestamp values.
  measurements[0] = measurements[0] - start
  if offset is not None:
    measurements[0] = measurements[0] + offset
  return measurements.transpose()


def ValueCheck(number):
  """Check for NaN and INF special values.

  Substitute numpy equivalents. These values are the special IEEE-488
  values that signal special numbers.
  """
  if number == 9.91E+37:
    return numpy.nan
  elif number == 9.9E+37:
    return numpy.inf
  elif number == -9.9E+37:
    return -numpy.inf
  else:
    return number


class DataSet(object):
  """Holds measurement data, label, and unit information.

  Also provides some common methods to operate on the data.

  This may be instantiated from several sources. Use filename parameter if
  source is a data (.dat) file, use dataset parameter if source is another
  dataset object, use array and headers if source is an array object and
  associated headers with labels an units. 
  """
  def __init__(self, filename=None, timespec=None, dataset=None,
        array=None, headers=None):
    if filename is not None:
      self.FromFile(filename, timespec)
    elif dataset is not None:
      self.FromDataSet(dataset, timespec)
    elif array is not None and headers is not None:
      self.FromArray(array, headers, timespec)
    else:
      self.measurements = None
      self.labels = None
      self.units = None
      self.metadata = None
      self.samplestart = 0.0
      self.starttime = 0.0
      self.endtime = 0.0
      self._mean = None

  unit = property(lambda self: self.units[1]) # assumes all columns same unit

  def __len__(self):
    return len(self.measurements)

  def __getitem__(self, idx):
    return self.measurements[idx]

  def __iter__(self):
    return iter(self.measurements)

  def GetStats(self):
    """Common statistics.

    Returns:
      mean, maximum, minimum, median, crestfactor
      of the measurement data.
    """
    if self._mean is None:
      self.Transpose()
      unit = self.units[1]
      timecol = self.measurements[0]
      col1 = self.measurements[1]
      self.sampleperiod = PQ(timecol[1] - timecol[0], self.units[0])
      self._mean = PQ(numpy.mean(col1), unit)
      self._maximum = PQ(numpy.amax(col1), unit)
      self._minimum = PQ(numpy.amin(col1), unit)
      self._median  = PQ(numpy.median(col1), unit)
      self._crestfactor  = float(self._maximum / self._mean)
      self.Transpose()
    return (self._mean, self._maximum, self._minimum, self._median, 
        self._crestfactor)

  mean = property(lambda self: self.GetStats()[0])
  maximum = property(lambda self: self.GetStats()[1])
  minimum = property(lambda self: self.GetStats()[2])
  median = property(lambda self: self.GetStats()[3])
  crestfactor = property(lambda self: self.GetStats()[4])

  def __str__(self):
    mean, maxi, mini, median, cf = self.GetStats()
    ts = timelib.localtime_mutable(self.samplestart)
    ts.set_format("%a, %d %b %Y %H:%M:%S %Z")
    offset = GetHMSString(self.starttime - self.samplestart)
    span = GetHMSString(self.endtime - self.starttime)
    s = ["Samples started at %s.\n"
    "Data offset %s after sampling started and spans %s." % (ts, offset, span)]
    s.append(str(self.metadata))
    s.append("")
    s.append("%s %s samples:" % (len(self.measurements), self.sampleperiod))
    s.append(" Maximum: %s" % maxi)
    s.append(" Minimum: %s" % mini)
    s.append("    Mean: %s" % mean)
    s.append("  Median: %s" % median)
    s.append("      CF: %s" % cf)
    return "\n".join(s)

  def FromFile(self, filename, timespec=None):
    headers, measurements = ReadArray(filename)
    self.FromArray(measurements, headers, timespec)
    self.metadata = datafile.DecodeFullPathName(filename)

  def FromArray(self, measurements, headers, timespec=None):
    self.metadata = None
    self._mean = None
    self.samplestart = measurements[0][0]
    if timespec:
      timemarks = TimeMarksGenerator(timespec)
      self.measurements = TimeSlice(measurements,
          timemarks.next(),
          timemarks.next())
    else:
      self.measurements = measurements
    self.starttime = self.measurements[0][0]
    self.endtime = self.measurements[-1][0]
    labels = []
    units = []
    for h in headers:
      match = HEADER_RE.search(h)
      if match:
        labels.append(match.group(1))
        units.append(match.group(2))
      else:
        raise ValueError("Not a properly formated data header")
    self.labels = labels
    self.units = units

  def FromDataSet(self, dataset, timespec=None):
    if timespec:
      timemarks = TimeMarksGenerator(timespec)
      self.measurements = TimeSlice(dataset.measurements,
          timemarks.next(),
          timemarks.next())
    else:
      self.measurements = dataset.measurements.copy()
    self.labels = dataset.labels[:]
    self.units = dataset.units[:]
    self.metadata = dataset.metadata.copy()
    self._mean = None

  def NormalizeTime(self, start=None, offset=None):
    self.measurements = NormalizeTime(self.measurements, start, offset)

  def Transpose(self):
    self.measurements = self.measurements.transpose()

  def GetColumns(self, columns):
    """Returns a tuple of a list of selected columns, and a list of column
    names (without unit).

    Args:
      columns (int, or sequence of ints): The column number, or numbers,
      starting from zero that will be extracted out (vertical slice).

    Returns:
      array for first column, the time values.
      list of arrays of select data columns.
      list of labels as strings. These positionally match the data columns.
    """
    datacolumns = self.measurements.transpose()
    if columns is not None: # should be tuple of column numbers, or int.
      datacols = []
      labels = []
      if type(columns) in (tuple, list):
        for n in columns:
          datacols.append(datacolumns[n])
          labels.append(self.labels[n])
      else:
        n = int(columns)
        datacols.append(datacolumns[n])
        labels.append(self.labels[n])
    else:
      datacols = datacolumns[1:]
      labels = self.labels[1:]
    return datacolumns[0], datacols, labels

  def GetTimeSlice(self, timespec):
    if type(timespec) is str:
      timemarks = TimeMarksGenerator(timespec)
      return TimeSlice(self.measurements, 
          timemarks.next(),
          timemarks.next())
    elif type(timespec) in (list, tuple):
      return TimeSlice(self.measurements, timespec[0], timespec[1])
    else:
      raise ValueError("Need timespec string or 2-tuple of (start, end) time.")

  def GetTimeSlices(self, timespec):
    """Iterator generator to iterate over sections of time.

    Args:
      timespec (string): a time span specification, such as "0s,5m,..." to
      get 5 minute chunks at a time.
    """
    timemarks = iter(TimeMarksGenerator(timespec))
    start = timemarks.next()
    for end in timemarks:
      subset = TimeSlice(self.measurements, start, end)
      ds = DataSet()
      ds.measurements = subset
      ds.units = self.units
      ds.labels = self.labels
      ds.metadata = self.metadata
      yield ds, start, end
      start = end


def _ReadCSV(fileobj):
  for line in fileobj:
    for el in line.split(","):
      yield float(el)

def ReadArray(filename):
  """Reads an array from a file.

  The first line must be a header with labels and units in a particular
  format. 
  The file could have been produced by an object from the
  droid.reports.flatfile module (hint, hint).
  """
  unused_, filetype = os.path.splitext(filename)
  fo = open(filename, "rU")
  try:
    if filetype == ".txt":
      header = map(eval, fo.readline().split("\t"))
      a = numpy.fromfile(fo, dtype="f8", sep="\n\t")
    elif filetype == ".csv":
      header = map(str.strip, fo.readline().split(","))
      a = numpy.fromiter(_ReadCSV(fo), numpy.float64)
    elif filetype == ".dat": # gnuplot style data
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
  # Data may have SCPI NAN or INF values in it. Convert to numpy
  # equivalents.
  a = numpy.fromiter(itertools.imap(ValueCheck, a), numpy.float64)
  a.shape = (-1, len(header))
  return header, a


def MakeTimePlot(dataset, ylim=None, columns=None, autoscale=False):
  import pylab
  from matplotlib.font_manager import FontProperties
  font = FontProperties(size="x-small")
  pylab.ioff()
  x_time, datacols, labels = dataset.GetColumns(columns)
  metadata = dataset.metadata
  if len(x_time) < 100:
    mrk = "."
    ls = "-"
  else:
    mrk = ","
    ls = "None"
  fig = pylab.figure(dpi=100, size_inches=(9,6))
  ax = fig.gca()
  if not autoscale:
    _SetYLimit(ax, ylim, unit)
  ax.set_xlabel("Time (s)")
  ax.set_ylabel(unit)
  for col, label, color in itertools.izip(datacols,  labels, color_cycler):
    ax.plot(x_time, col, color=color, label=label, ls=ls, marker=mrk)
  #label = "%s-%s" % (colname, metadata.GetStateString(*legenddata))
  title = "%s-%s-%s" % (metadata.testcase, 
      metadata.timestamp.strftime("%m%d%H%M%S"),
      "-".join(labels))
  #pylab.title(title, fontsize="x-small")
  ax.set_title(title, prop=font)
  ax.legend(prop=font)
  return fig


def MakeCharts(dataset, timemarks="0s,9d", ylim=None, columns=None,
      autoscale=False, events=None, interactive=False):
  # import pylab here since this is a very large library that you might
  # not want loaded and initialized everytime you use this module. Also,
  # if you are using one of the GTK based backends for matplotlib, and you
  # do not have DISPLAY set (e.g. running from a remote shell), then you
  # will see this exception raised when you import this module:
  # RuntimeError: could not open display
  # This is not in my, or matplotlib's, control.
  import pylab
  from matplotlib.font_manager import FontProperties
  pylab.ioff()
  names = []
  if type(events) is DataSet:
    events.NormalizeTime(dataset.measurements[0][0])
  dataset.NormalizeTime()
  unit = dataset.unit

  for subset, start, end in dataset.GetTimeSlices(timemarks):
    if len(subset) > 0:
      x_time, datacols, labels = subset.GetColumns(columns)
      if len(x_time) < 100:
        mrk = "."
        ls = "-"
      else:
        mrk = ","
        ls = "None"
      for col, label, color in itertools.izip(datacols,  labels, color_cycler):
        pylab.plot(x_time, col, color=color, label=label, ls=ls, marker=mrk)
      pylab.setp(pylab.gcf(), dpi=100, size_inches=(9,6))
      pylab.xlabel("Time (s)")
      if not autoscale:
        _SetYLimit(pylab.gca(), ylim, unit)
      pylab.ylabel(unit)

      if events is not None:
        ax = pylab.gca()
        for row in events:
          ax.axvline(row[0], color="rgbymc"[int(row[1]) % 6])

      metadata = subset.metadata
      title = "%s-%s-%s-%ss-%ss" % (metadata.testcase, 
          metadata.timestamp.strftime("%m%d%H%M%S"),
          "-".join(labels),
          int(start), 
          int(end))
      pylab.title(title, fontsize="x-small")
      font = FontProperties(size="x-small")
      pylab.legend(prop=font)

      if not interactive:
        fname = "%s.%s" % (title, "png")
        pylab.savefig(fname, format="png")
        names.append(fname)
        pylab.cla()
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


def PlotHistogram(filenames, timemarks=None, columns=None, bins=2000, 
      interactive=False, legenddata=(), autoscale=False):
  import pylab
  from matplotlib.font_manager import FontProperties
  if not interactive:
    pylab.ioff()
  try:
    bins = int(bins)
    brange = (-0.05, 2.5)
    binname = str(bins)
  except ValueError:
    binname = bins.upper()
    if binname.startswith("D"): # detailed
      bins = (list(aid.frange(0.0, 0.05, 0.0005)) + 
              list(aid.frange(0.05, 1.0, 0.001)) + 
              list(aid.frange(1.0, 2.6, 0.002))
              )
      brange = (-0.05, 2.5)
    elif binname.startswith("M"): # medium detail
      bins = (list(aid.frange(0.0, 0.05, 0.0005)) + 
              list(aid.frange(0.05, 1.1, 0.001))
              )
      brange = (-0.05, 1.0)
    elif binname.startswith("Z"): # zoom at lower end
      bins = (list(aid.frange(0.0, 0.05, 0.0005)) + 
              list(aid.frange(0.05, 0.51, 0.001))
              )
      brange = (-0.05, 0.5)
    elif binname.startswith("S"): # super zoom at lower end
      bins = (list(aid.frange(0.0, 0.05, 0.0005)) + 
              list(aid.frange(0.05, 0.16, 0.001))
              )
      brange = (-0.05, 0.15)
  ts = None
  unit = None
  for filename in filenames:
    metadata = datafile.DecodeFullPathName(filename)
    if ts is None:
      ts = metadata.timestamp.strftime("%m%d%H%M%S")
    header, measurements = ReadArray(filename)
    if unit is None:
      unit = HEADER_RE.search(header[1]).group(2)
    measurements = NormalizeTime(measurements)
    if timemarks:
      timemarks = TimeMarksGenerator(timemarks)
      measurements = TimeSlice(measurements, 
          timemarks.next(),
          timemarks.next())
    datacolumns = measurements.transpose()
    datacols, headers = _GetColumns(datacolumns, header, columns)
    for col, colname, color in itertools.izip(datacols, headers, color_cycler):
      label = "%s-%s" % (colname, metadata.GetStateString(*legenddata))
      hist, edges = numpy.histogram(col, bins, brange, False)
      pylab.plot(edges, hist, color=color, label=label) # plot it

  pylab.axis(xmin=-0.005, ymin=-100)
  pylab.setp(pylab.gcf(), dpi=100, size_inches=(9,6))
  title = "histogram-%s-%s" % (ts, "bins%s" % binname)
  pylab.title(title, fontsize="x-small")
  if unit is not None:
    pylab.xlabel(unit)
  if legenddata:
    font = FontProperties(size="x-small")
    pylab.legend(prop=font)
  if interactive:
    pylab.show()
    fname = None
  else:
    fname = "%s.%s" % (title, "png")
    pylab.savefig(fname, format="png")
    pylab.cla()
  return fname


def _SetYLimit(ax, ylim, unit):
  if ylim is None:
    if unit == "V":
      ax.set_ylim(2.0, 4.4)
    elif unit == "A":
      ax.set_ylim(-0.02, 2.5)
    elif unit == "mA":
      ax.set_ylim(-20.0, 2500.0)
  else:
    ax.set_ylim(*ylim) # should be tuple of (min,max).


def TwoSetPlot(ds1, ds2, ylim1=None, ylim2=None, autoscale=False, interactive=False):
  import pylab
  from matplotlib.font_manager import FontProperties
  if not interactive:
    pylab.ioff()
  font = FontProperties(size="x-small")
  ds1.NormalizeTime()
  ds2.NormalizeTime()
  ax1 = pylab.subplot(111)
  x_time1, datacols1, labels1 = ds1.GetColumns(1)
  x_time2, datacols2, labels2 = ds2.GetColumns(1)
  if not autoscale:
    _SetYLimit(ax1, ylim1, ds1.unit)
  pylab.plot(x_time1, datacols1[0], 
      color=color_cycler.next(), label=labels1[0], ls="None", marker=",")
  pylab.xlabel("Time (s)")
  pylab.ylabel(ds1.unit)
  ax2 = pylab.twinx()
  if not autoscale:
    _SetYLimit(ax2, ylim2, ds2.unit)
  pylab.plot(x_time2, datacols2[0], 
      color=color_cycler.next(), label=labels2[0], ls="None", marker=",")
  pylab.ylabel(ds2.unit)
  ax2.yaxis.tick_right()
  pylab.legend(prop=font)
  pylab.setp(pylab.gcf(), dpi=100, size_inches=(9,6))
  title = "plot-%s-%s-%s" % (ds1.metadata.timestamp.strftime("%m%d%H%M%S"), 
      ds1.unit, ds2.unit)
  pylab.title(title, fontsize="x-small")
  if interactive:
    pylab.show()
    fname = None
  else:
    fname = "%s.%s" % (title, "png")
    pylab.savefig(fname, format="png")
    pylab.cla()
  return fname


def BatteryBarChart(report_list, interactive=False, autoscale=False,
      legenddata=()):
  """Create a bar chart given a list of battery life reports."""
  # same as above.
  import pylab
  from matplotlib.font_manager import FontProperties
  from matplotlib import colors
  if not interactive:
    pylab.ioff()

  N = len(report_list)
  barwidth = 1.0 / N + 0.1
  build = report_list[0].metadata.build
  pylab.title(
      "Battery Life for %s-%s-%s" % (build.product, build.type, build.id))
  pylab.subplots_adjust(left=0.10, bottom=0.05, right=0.95, top=0.95)
  max_lifetime = 0.0
  for index, battery_report in enumerate(report_list):
    lifetime = float(battery_report.lifetime.hours)
    max_lifetime = max(lifetime, max_lifetime)
    blue = aid.IF(battery_report.byvoltage, 0.0, 0.5)
    color = colors.rgb2hex(aid.IF(battery_report.estimated, 
        ((index * 0.1) % 1.0, 0, blue), 
        (0, 1.0, blue)))
    label = "(%s) %s (%.2f h)" % (index + 1, 
        battery_report.metadata.GetStateString(*legenddata), 
        battery_report.lifetime.hours)
    pylab.bar(index, lifetime, width=barwidth, color=color, label=label)
  if autoscale:
    # Make room for legend at top (wish it could be outside the plot).
    pylab.ylim(0.0, max_lifetime + (index * 2.8) + 13.0) 
  else:
    pylab.ylim(0.0, 200.0)
  pylab.xlim(-barwidth, N)
  # label index is origin 1.
  pylab.xticks(pylab.arange(N) + (barwidth / 2.0), 
      map(str, pylab.arange(N) + 1), 
      fontsize=10)

  pylab.ylabel('Time (h)')
  if legenddata:
    font = FontProperties(size=9)
    pylab.legend(prop=font)

  if interactive:
    pylab.show()
  else:
    fname = "batterylife-%s.png" % (
        report_list[0].metadata.timestamp.strftime("%m%d%H%M%S"))
    pylab.savefig(fname, format="png")
    return fname


# XXX TODO(dart) this is not quite right yet. bars are not grouped.
def MultiBatteryBarChart(report_list, interactive=False, legenddata=(),
      title=""):
  """Create a bar chart with that places similar conditions together for
  comparison.

  Reports with matching metadata should be grouped together in the list.
  """
  import pylab
  from matplotlib.font_manager import FontProperties
  from matplotlib import colors
  if not interactive:
    pylab.ioff()
  build = report_list[0].metadata.build

  N = len(report_list)

  barwidth = 1.0 / 8.0

  patches = []
  labels = []
  thefig = pylab.gcf()
  thefig.set_size_inches((11,7))
  thefig.set_dpi(80.0)
  pylab.title("Battery Life (%s) %s" % (build.id, title))
  pylab.subplots_adjust(left=0.07, bottom=0.05, right=0.55, top=0.95)

  group = 0
  last_report = None
  for index, battery_report in enumerate(report_list):
    lifetime = float(battery_report.lifetime.hours)
    blue = aid.IF(battery_report.byvoltage, 0.0, 0.5)
    color = colors.rgb2hex((
        aid.IF(battery_report.estimated, 1.0, 0.0),
        (index * 0.05) % 1.0,
        (group * 0.1) % 1.0)
        )
    if last_report and \
        last_report.metadata.CompareData(battery_report.metadata, 
        legenddata, missingok=True):
      label = "(%s) - (%.2f h)" % (index + 1, lifetime)
    else:
      label = "(%s) %s (%.2f h)" % (index + 1, 
          battery_report.metadata.GetStateString(*legenddata), lifetime)
      group += 1
      #pylab.bar(index + group, 0, width=barwidth) # spacer
    patchlist = pylab.bar(index + group, lifetime, width=barwidth, color=color, label=label)
    labels.append(label)
    patches.extend(patchlist)
    last_report = battery_report

  pylab.ylim(0.0, 200.0)
  pylab.xlim(-barwidth, N)
  # label index is origin 1.
  x_range = pylab.arange(N)
  pylab.xticks(x_range + (barwidth / 2.0), map(str, x_range + 1), fontsize=10)
  pylab.ylabel('Time (h)')
  if legenddata:
    font = FontProperties(size=9)
    pylab.figlegend(patches, labels, "upper right", prop=font)

  if interactive:
    pylab.show()
  else:
    fname = "batterylife_group-%s.png" % (
        report_list[0].metadata.timestamp.strftime("%m%d%H%M%S"))
    pylab.savefig(fname, format="png")
    return fname


def MultiBuildBatteryBarChart(report_list, interactive=False, autoscale=False,
      legenddata=()):
  """Create a bar chart given a list of battery life reports."""
  # same as above.
  import pylab
  from matplotlib.font_manager import FontProperties
  from matplotlib import colors
  if not interactive:
    pylab.ioff()

  N = len(report_list)
  barwidth = 1.0 / N + 0.1

  thefig = pylab.gcf()
  thefig.set_size_inches((11,6))
  thefig.set_dpi(80.0)
  pylab.subplots_adjust(left=0.07, bottom=0.05, right=0.75, top=0.95)

  max_lifetime = 0.0
  patches = []
  labels = []
  pylab.title("Battery comparison: %s"  % (
      report_list[0].metadata.GetStateString(*legenddata)), fontsize="small")
  for index, battery_report in enumerate(report_list):
    lifetime = float(battery_report.lifetime.hours)
    max_lifetime = max(lifetime, max_lifetime)
    blue = aid.IF(battery_report.byvoltage, 0.0, 0.5)
    color = colors.rgb2hex(
        aid.IF(battery_report.estimated, 
            ((index * 0.1) % 1.0, 0.5, blue), 
            ((index * 0.1) % 1.0, 1.0, blue))
        )
    label = "(%s) %s (%.2f h)" % (index + 1, 
        battery_report.metadata.build.id,
        battery_report.lifetime.hours)
    patchlist = pylab.bar(
        index, lifetime, width=barwidth, color=color, label=label)
    labels.append(label)
    patches.extend(patchlist)
  if autoscale:
    pylab.ylim(0.0, max_lifetime + 20.0) 
  else:
    pylab.ylim(0.0, 200.0)
  pylab.xlim(-barwidth, N)
  # labels are position offset by +1.
  pylab.xticks(pylab.arange(N) + (barwidth / 2.0), 
      map(str, pylab.arange(N) + 1), 
      fontsize=10)

  pylab.ylabel('Time (h)')
  if legenddata:
    font = FontProperties(size=9)
    pylab.figlegend(patches, labels, "upper right", prop=font)

  if interactive:
    pylab.show()
  else:
    fname = "batterylife_builds-%s.png" % (
        report_list[0].metadata.timestamp.strftime("%m%d%H%M%S"))
    pylab.savefig(fname, format="png")
    return fname


def RollupTable(filename, timespan="1minute"):
  timemarks = TimeMarksGenerator("0s,%s,..." % timespan)
  newfilename = "%s-%s.dat" % (os.path.splitext(filename)[0], timespan)
  header, arr = ReadArray(filename)
  header = header[:2] # timestamp and average value

  ctx = dictlib.AttrDict()
  ctx.datafilename = newfilename
  report = flatfile.GnuplotReport(ctx)
  report.Initialize()
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
  return newfilename


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


def BatteryLifeByCurrent(measurements, unit="A", battery="DREA160", strict=True):
  """Remove charge from the battery using the measured discrete time intervals.

  Args:
    measurements (array): An array with timestamps in the first column,
    and average current measurement in the second column. The array should
    be organized in rows. 
    unit (string): The unit that the second column, average current draw,
    is in. Usually "mA", or "A", default "A".
    battery (string): The model name of the battery that will be used to
    compute lifetime. Default "DREA160".
  Return:
    A BatteryLifeReport containing the time span and remaining battery
    charge.
  """
  charge = BATTERIES[battery][0].inUnitsOf("C")
  charge_consumed = PQ(0.0, "C")
  zeroC = PQ(0.0, "C")
  measurements_iter = iter(measurements)
  firstrow  = measurements_iter.next()
  starttime = timeval = PQ(firstrow[0], "s")
  errcount = 0 

  for row in measurements_iter:
    nexttime = PQ(row[0], "s")
    rawvalue = row[1] # Column 1 is averaged samples from instrument.
    if numpy.isnan(rawvalue):
      if strict:
        raise ValueError( "NaN value in data: at time %s (offset %s)." % (
            nexttime, nexttime - starttime))
      else:
        # some overflow happened, so pick some arbitrary high value.
        rawvalue = 1.5 
        errcount += 1
    measurement = PQ(rawvalue, unit)
    delta_t = nexttime - timeval
    charge_interval = measurement * delta_t
    charge -= charge_interval
    charge_consumed += charge_interval
    timeval = nexttime
    if charge <= zeroC:
      break
  return BatteryLifeReport(battery, (nexttime - starttime).value, 
      charge, charge_consumed, None, errcount)


def BatteryChargeTime(dataset, battery="DREA160", strict=True):
  """Compute charge time by counting DC current measurements.

  """
  fullcharge = BATTERIES[battery][0].inUnitsOf("C")
  charge_added = PQ(0.0, "C")
  unit = dataset.unit

  measurements_iter = iter(dataset.measurements)
  firstrow  = measurements_iter.next()
  starttime = timeval = PQ(firstrow[0], "s")
  errcount = 0 

  for row in measurements_iter:
    nexttime = PQ(row[0], "s")
    rawvalue = row[1]
    if numpy.isnan(rawvalue):
      if strict:
        raise ValueError( "NaN value in data: at time %s (offset %s)." % (
            nexttime, nexttime - starttime))
      else:
        # some overflow happened, so pick some arbitrary high value.
        rawvalue = -0.1
        errcount += 1
    if rawvalue < 0.0: # DC charging measurements are negative
      measurement = PQ(rawvalue, unit)
      delta_t = nexttime - timeval
      charge_added -= measurement * delta_t 
      timeval = nexttime
      if charge_added >= fullcharge:
        break
  return BatteryChargeReport(battery, (nexttime - starttime).value, 
      charge_added, errcount)


class BatteryChargeReport(object):
  """Holds result of battery charge time calculation.

  When stringified it provides a description of the results.
  """
  def __init__(self, battery, time, charged, errorcount):
    self.battery = battery
    self._chargetime = TimeSpan(time)
    self.charged = charged.inUnitsOf("mA*h")
    self.errorcount = errorcount

  def __str__(self):
    s = []
    fullcharge = BATTERIES[self.battery][0].inUnitsOf("mA*h")
    s.append("Battery charge time for %r (rated %s):" % (self.battery, fullcharge))
    if self.errorcount:
      s.append("Warning: data had %s errors or overflows." % self.errorcount)
    if self.charged < fullcharge:
      s.append("Not enough data to determine charge time. Got: %s" % self.charged)
    else:
      s.append("Charge placed in interval: %s" % self.charged)
    ct = self._chargetime
    s.append("seconds: %s\nhours: %s\n%s" % (ct.seconds, ct.hours, ct))
    return "\n".join(s)


def BatteryLifeByVoltage(voltagemeasurements, battery="DREA160"):
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
  # The DUT may turn off before the cutoff voltage is measured. But the
  # absolute minimum reading may be far past that, since the voltage is
  # held near zero sometimes by the DUT.
  v_min = numpy.min(voltagemeasurements[1])
  if v_min > cutoff_spec:
    cutoff_spec = v_min
  for i, val in enumerate(voltagemeasurements[1]):
    if val <= cutoff_spec:
        break
  start = voltagemeasurements[0][0]
  end = voltagemeasurements[0][i]
  cutoff = voltagemeasurements[1][i]
  return BatteryLifeReport(battery, (end - start), None, None, PQ(cutoff, "V"))


def GetBatteryLifeReportFromFile(fname, 
      timemarks=None, battery=None, metadata=None, strict=True):
  """Return a BatteryLifeReport given a data file of current or voltage
  measurements.
  """
  data = DataSet(filename=fname, timespec=timemarks)
  if metadata:
    data.metadata.update(metadata)
  return GetBatteryLifeReport(data, battery, strict)


def GetBatteryLifeReport(dataset, battery=None, strict=True):
  unit = dataset.unit
  if unit == "V":
    rpt = BatteryLifeByVoltage(dataset.measurements, battery)
  elif unit.endswith("A"): # mA or A
    rpt = BatteryLifeByCurrent(dataset.measurements, unit, battery, strict)
  else:
    raise ValueError, "Can't determine unit of dataset column."
  rpt.metadata = dataset.metadata
  return rpt


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
    battery (string): a battery model string (e.g. "DREA160").
    time (float): The length of time taken for a measurement set.
    endcharge (PhysicalQuantity): a charge value, in Coloumbs, that was
      left in the battery after being discharged over the timespan given.
      This is provided for current-draw methods of measurement.
    cutoff (PhysicalQuantity): The final, cutoff, voltage of the battery.
      This is provided when the battery depletion, measured by voltage
      drop, is done. 
  """

  def __init__(self, battery, time, endcharge=None, consumed_charge=None, cutoff=None, errorcount=0):
    self.battery = battery
    self._lifetime = TimeSpan(time)
    self._actualtime = None
    self._estimated = None
    self.metadata = None
    self.endcharge = endcharge
    self.consumed_charge = consumed_charge
    self.cutoff = cutoff
    self.errorcount = errorcount

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

  def __repr__(self):
    return "%s(%r, %r, %r, %r, %r, %r)" % (self.__class__.__name__, 
        self.battery, self._lifetime, self.endcharge, self.consumed_charge, 
        self.cutoff, self.errorcount)

  def __str__(self):
    startcharge = BATTERIES[self.battery][0]
    lt = self._GetLifetime()
    s = ["Battery life for %r (%s)%s:" % (
        self.battery, startcharge.inUnitsOf("mA*h"), 
        aid.IF(self._IsEstimated(), " (estimated)", "" ))]
    if self.errorcount:
      s.append("Warning: data had %s errors or overflows." % self.errorcount)
    if self.cutoff is not None: # a battery voltage derived report.
      if self.cutoff.value >= 2.9:
        s.append("Warning: Minimum point of %s is not near cutoff." % self.cutoff)
      s.append("Cutoff voltage was about: %s" % self.cutoff)
    else:
      s.append("Charge consumed in interval: %s" % self.consumed_charge.inUnitsOf("mA*h"))
    s.append("seconds: %s\nhours: %s\n%s" % (lt.seconds, lt.hours, lt))
    return "\n".join(s)


class BatteryLifeEstimator(object):
  """
Ic = in-call current
Iu = usage current
Is = syncing current
Iuc = Iu + Ic

tc = call time
ts = sync time
tu = usage time
tuc = call usage time

B - (Ic*tc + Is*ts + Iu*tu + Iuc*tuc) = 0
batterylife = tc + ts + tu + tuc
  """
  def __init__(self, icall=320.0, iusage=250.0, isync=34.0, istandby=6.0, 
        battery="DREA160"):
    self.battery_capacity = BATTERIES[battery][0]
    # current for each mode, in mA
    self.iusage = PQ(iusage, "mA")
    self.icall = PQ(icall, "mA")
    self.isync = PQ(isync, "mA")
    self.istandby = PQ(istandby, "mA")
    self.icallusage = self.icall + self.iusage

  def GetBatteryLife(self, tusage, tcall, tcallusage, tsync=0.0):
    tusage = PQ(tusage, "s")
    tcall = PQ(tcall, "s")
    tsync = PQ(tsync, "s")
    tcallusage = PQ(tcallusage, "s")
    tstandby = (self.battery_capacity - 
        self.icall * tcall - 
        self.iusage * tusage - 
        self.isync * tsync - 
        self.icallusage * tcallusage) / self.istandby
    return (tstandby + tusage + tcall + tsync + tcallusage).inUnitsOf("min")


# Functions for interactive reporting from command line.

def DoGraph(filename, timemarks=None, columns=None, ylim=None,
      autoscale=False, eventsfile=None):
  """Make a series of graphs from the the data in file split on the time
  marks. 
  """
  data = DataSet(filename=filename, timespec=timemarks)
  if eventsfile is not None:
    events = DataSet(filename=eventsfile)
  else:
    events = None
  names = MakeCharts(data, columns=columns, ylim=ylim, 
      events=events, autoscale=autoscale)
  for name in names:
    print "PNG file saved to:", name


def DoTwoSetPlot(filename1, filename2, timemarks=None, ylim1=None,
      ylim2=None, autoscale=False):
  """
  """
  ds1 = DataSet(filename=filename1, timespec=timemarks)
  ds2 = DataSet(filename=filename2, timespec=timemarks)
  print TwoSetPlot(ds1, ds2, ylim1, ylim2, autoscale)


def DoCCDFChart(filename, timemarks=None):
  pass


def DoRollupTable(filenames, summary, timespan):
  """Create a new data set consisting of averages for one minute
  intervals.
  """
  for fname in filenames:
    newname = RollupTable(fname, timespan)
    if summary:
      DoSummary(newname)
    print newname


def DoSummary(fname, timemarks=None):
  data = DataSet(filename=fname, timespec=timemarks)
  rptfname =data.metadata.GetFileName("summary")
  stream = open(rptfname, "w")
  stream.write(str(data))
  stream.write("\n")
  stream.close()
  print rptfname


def DoBattery(fname, timemarks=None, battery=None, strict=True):
  """Do a battery life determination and write the result to a file.
  """
  data = DataSet(filename=fname, timespec=timemarks)
  rpt = GetBatteryLifeReport(data, battery, strict)
  rptfname = data.metadata.GetFileName("batterylife")
  stream = open(rptfname, "w")
  stream.write(str(data.metadata))
  stream.write("\n")
  stream.write(str(rpt))
  stream.write("\n")
  stream.close()
  print rptfname


def DoBatteryCharge(fname, timemarks=None, battery=None, strict=True):
  """
  """
  data = DataSet(filename=fname, timespec=timemarks)
  rpt = BatteryChargeTime(data, battery, strict)
  rptfname = data.metadata.GetFileName("batterycharge")
  stream = open(rptfname, "w")
  stream.write(str(data.metadata))
  stream.write("\n")
  stream.write(str(rpt))
  stream.write("\n")
  stream.close()
  print rptfname


def DoFullBatteryChart(filenames, timemarks=None, battery=None, 
      autoscale=False, legenddata=None, extradata=None, strict=True):
  reports = []
  for fname in filenames:
    metadata = datafile.DecodeFullPathName(fname)
    if extradata:
      metadata.update(extradata)
    rpt = GetBatteryLifeReportFromFile(fname, timemarks, 
        battery, metadata, strict)
    reports.append(rpt)
  print BatteryBarChart(reports, autoscale=autoscale, legenddata=legenddata)


class _MetaKeyGenerator(object):
  def __init__(self, metakeys, missingok=True):
    self._metakeys = metakeys
    self._missingok = missingok

  def __call__(self, report):
    s = []
    metadata = report.metadata
    for name in self._metakeys:
      try:
        s.append(str(metadata[name]))
      except KeyError:
        if self._missingok:
          pass
        else:
          raise ValueError("cannot compare")
    return tuple(s)


def DoFullMultiBatteryChart(filenames, timemarks=None, battery=None, 
      autoscale=False, legenddata=None, extradata=None, strict=True):
  reports = []
  for fname in filenames:
    dataset = DataSet(filename=fname, timespec=timemarks)
    if extradata:
      dataset.metadata.update(extradata)
    rpt = GetBatteryLifeReport(dataset, battery, strict)
    reports.append(rpt)
  # sort by selected metadata
  reports.sort(key=_MetaKeyGenerator(legenddata, strict))
  print MultiBatteryBarChart(reports, legenddata=legenddata)


def DoCrossBuildBatteryChart(filenames, timemarks=None, battery=None, 
      autoscale=False, legenddata=None, extradata=None, strict=True):
  reports = []
  first_metadata = datafile.DecodeFullPathName(filenames[0])
  filenames.sort()
  for fname in filenames:
    # filter reports state that matches the first one.
    try:
      metadata = datafile.DecodeFullPathName(fname)
    except OSError, err:
      print err
      continue
    if extradata:
      metadata.update(extradata)
    if not first_metadata.CompareData(metadata, legenddata, missingok=True):
      print "Warning:", fname, "does not match state of first file."
      continue
    rpt = GetBatteryLifeReportFromFile(fname, timemarks, battery, metadata, strict)
    reports.append(rpt)
  print MultiBuildBatteryBarChart(reports, autoscale=autoscale, 
      legenddata=legenddata)




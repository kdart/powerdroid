#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

r"""Functions to make interactive analysis easier. Intended for use with
Ipython. In Ipython do the following:

from droid.interactive import *

Or, what I do, define a shell alias like this:

alias ip='ipython -pylab -nobanner -noconfirm_exit -c \
    "from droid.interactive import *"'

Then you can do:

$ ip
In [1]: Plot("current.dat")

In [2]: Histogram("current.dat", bins="S")

etc.

"""

import numpy
import pylab
from matplotlib import widgets
from pycopia import cliutils

from droid import analyze

PQ = analyze.PQ # shorthand for PhysicalQuantity


def Plot(filename=None, dataset=None, timemarks=None, 
    events=None, eventfile=None,
    ylim=None, columns=1, battery="DREA160",
    autoscale=True):
  """Plot from ipython.

  Args:
    filename (string): name of a data file to plot. This will be loaded
    into a DataSet object.

    dataset (DataSet): pre-existing dataset to plot. Mutually exclusive
    with filename parameter.

    timemarks (string): a time spec indicating a span of time to slice.

    eventfile (string): name of data file containing event marks.

    events (DataSet): A pre-existing event dataset. 

    ylim (tuple of (min, max): minimum and maximum Y values to plot.

    columns (int, or sequence of ints): The column number, or numbers,
    starting from zero that will be extracted out (vertical slice).

    battery (string): Name of battery model. Default is "DREA160"

    autoscale (bool): If True, automatically fit graph scale to data.
    False means use a fixed scale (2.5 amp max).

  """
  if filename is not None:
    dataset = analyze.DataSet(filename=filename, timespec=timemarks)
  if eventfile is not None:
    events = analyze.DataSet(filename=eventfile)
  if dataset is None:
    print "You should supply a filename or a dataset."
    return
  analyze.MakeCharts(dataset, ylim=ylim, events=events,
      columns=columns, autoscale=autoscale, interactive=True)
  pylab.gcf().set_size_inches((9,7))
  plotaxes = pylab.gca()
  pylab.subplots_adjust(bottom=0.15)
  capacity = analyze.BATTERIES[battery][0]
  reporter = DataSampleReporter(plotaxes, dataset, capacity)
  span = widgets.SpanSelector(plotaxes, reporter.StatSelected, "horizontal")
  capaxes = pylab.axes([0.20, 0.025, 0.65, 0.03])
  capslider = widgets.Slider(capaxes, "Batt (mA-h)", 800, 1350, capacity.inUnitsOf("mA*h").value)
  capslider.on_changed(reporter.SetCapacity)
  pylab.ion()
  pylab.show()


def TwoPlot(fname1, fname2, timemarks=None, ylim=None, autoscale=True):
  """Plot a two axis plot. """
  ds1 = analyze.DataSet(filename=fname1, timespec=timemarks)
  ds2 = analyze.DataSet(filename=fname2, timespec=timemarks)
  analyze.TwoSetPlot(ds1, ds2, autoscale=autoscale, 
      ylim1=ylim, ylim2=ylim, interactive=True)


def Histogram(filename, timemarks="0s,5d", columns=1, bins=2000, 
      legenddata=()):
  """Histogram from data."""
  analyze.PlotHistogram([filename], timemarks=timemarks, columns=columns,
      bins=bins, legenddata=legenddata, interactive=True)


def BuildHistogram():
  filename = cliutils.get_input("File name?")
  timemarks = cliutils.get_input("Time span?", "0s,5d")
  columns = cliutils.get_input("columns?", "1")
  columns = int(columns)
  bins = cliutils.get_input("bins [N, super, zoom]?", "2000")
  legenddata = cliutils.get_input("legend data?", None)

  analyze.PlotHistogram([filename], timemarks=timemarks, columns=columns,
      bins=bins, legenddata=legenddata, interactive=True)


def Clear():
  pylab.cla()


def GetBatteryLifeReport(dataset, battery="DREA160"):
  unit = dataset.unit
  if unit == "V":
    rpt = analyze.BatteryLifeByVoltage(dataset.measurements, battery)
  elif unit.endswith("A"): # mA or A
    rpt = analyze.BatteryLifeByCurrent(dataset.measurements, unit, battery, True)
  else:
    raise ValueError, "Don't know unit %r." % (unit,)
  return rpt


class DataSampleReporter(object):
  def __init__(self, axes, dataset, capacity):
    self._axes = axes
    self.dataset = dataset
    self.unit = self.dataset.units[1]
    self.battery_capacity = capacity
    self._vlines = None
    # create a text box
    self.textbox = pylab.figtext(0.5, 0.5, "", fontsize="x-small", family="monospace",
        bbox=dict(facecolor="red", alpha=0.2), visible=False, zorder=100,
        axes=axes)

  def StatSelected(self, tmin, tmax):
    set = self.dataset.GetTimeSlice((tmin, tmax))
    values = set.transpose()[1]
    unit = self.unit
    if len(values) > 0 and unit.endswith("A"):
      s = []
      s.append("%d samples over %.2f seconds." % (len(values), tmax - tmin))
      avg = self.avgcurrent = numpy.mean(values)
      s.append("Maximum: %.6f %s" % ( numpy.amax(values), unit))
      s.append("Minimum: %.6f %s" % ( numpy.amin(values), unit))
      s.append("Average: %.6f %s" % ( avg, unit))
      s.append(" Median: %.6f %s" % ( numpy.median(values), unit))
      s.append("Estimated battery life: %.2f hours" % (
          self.battery_capacity / analyze.PQ(avg, unit)).inUnitsOf("h").value)
      self.textbox.set_text("\n".join(s))
      self._RemoveVlines()
      self._vlines = (self._axes.axvline(tmin, color="r"), 
                      self._axes.axvline(tmax, color="r"))
      self.textbox.set_visible(True)
    else:
      self._RemoveVlines()
      self.textbox.set_text("")
      self.textbox.set_visible(False)
    pylab.gcf().canvas.draw()

  def _RemoveVlines(self):
    if self._vlines is not None:
      vlines = self._vlines
      self._vlines = None
      for vline in vlines:
        vline.remove()

  def SetCapacity(self, value):
    self.battery_capacity = PQ(value, "mA*h")
    if self.unit.endswith("A") and self.textbox.get_visible():
      self.textbox.set_text(
          "Average: %.6f %s\nEstimated battery life: %.2f hours" % (self.avgcurrent, self.unit,
              (self.battery_capacity / analyze.PQ(self.avgcurrent, self.unit)).inUnitsOf("h").value))
      pylab.gcf().canvas.draw()





#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright 2006 The Android Open Source Project

"""Library of plotting functions for power data.

"""

__author__ = 'dart@google.com (Keith Dart)'


from cStringIO import StringIO

from numpy import arange

# import matplotlib
from matplotlib import figure
from matplotlib import ticker
# from matplotlib import dates as dateutil
from matplotlib.backends import backend_agg

from PIL import Image



GRAPH_SIZE = (704, 440)
LINE_STYLE      = ("-", "--")
GRID_STYLE      = ("-", ":")
GRID_LINEWIDTH  = 0.0001
GRAPH_LINEWIDTH = 1.0
DEFAULT_COLORS = ["#FF0000", "#00FF00"]


class Error(Exception):
  pass

class PlotError(Error):
  """Some error occurred and plot could not be created."""


class Graph(object):
  """Base class for all chart or graphs.

  Defines common methods. 

  Args:
    title: The title of the chart that will appear in the title location.
    Any extra keyword arguments are passed on the the Initialize() method
    that a sublass may use.
  """
  def __init__(self, title, **kwargs):
    self.title = title
    self.Initialize(**kwargs)

  def GetFigure(self, figsize=(6,6), dpi=75, 
                facecolor="1.0", edgecolor="1.0", linewidth="1.0",
                frameon=True, subplotpars=None):
    fig = figure.Figure(figsize=figsize, dpi=dpi, facecolor=facecolor,
                        edgecolor=edgecolor, linewidth=linewidth,
                        frameon=frameon, subplotpars=subplotpars)
    backend_agg.FigureCanvasAgg(fig)
    return fig

  def RenderFigure(self, fig, mimetype=None):
    canvas = fig.canvas
    outformat = _MIMEMAP[mimetype]
    canvas.draw()
    size = canvas.get_renderer().get_canvas_width_height()
    buf = canvas.buffer_rgba(0,0)
    im = Image.frombuffer('RGBA', size, buf, 'raw', 'RGBA', 0, 1)
    imdata = StringIO()
    im.save(imdata, format=outformat)
    del fig.canvas # break circular reference
    return imdata.getvalue()

  # override the following.
  def Initialize(self, **kwargs):
    pass

  def AddDataset(self, *args, **kwargs):
    raise NotImplementedError

  def AddData(self, *args, **kwargs):
    raise NotImplementedError

  def GetImage(self, mimetype="image/png", **kwargs):
    fig = self.GetFigure(**kwargs)
    ax = fig.add_subplot(111)
    ax.set_title("Not Implemented")
    return self.RenderFigure(fig, mimetype)

# maps mime types to PIL.Image file types.
_MIMEMAP = {
  None: "PNG", # default format
  "image/png": "PNG",
  "image/jpeg": "JPEG",
}

class TimeDomainGraph(Graph):
  """
  """

  def GetImage(self, mimetype="image/png", **kwargs):
    """
    """

class LinePlot(Graph):
  pass # TODO(dart) implement...

# Pie chart

class PieGraph(Graph):
  """Pie chart.

  Each data value has a label and a color.
  """
  def Initialize(self):
    self.values = []
    self.labels = []
    self.colors = []

  def AddData(self, data, label, color):
    self.values.append(data)
    self.labels.append(label)
    self.colors.append(color)

  def AddDataset(self, data, labels, colors):
    self.values.extend(data)
    self.labels.extend(labels)
    self.colors.extend(colors)

  def GetImage(self, mimetype="image/png", **kwargs):
    fig = self.GetFigure(**kwargs)
    ax = fig.add_subplot(111)
    ax.pie(self.values, labels=self.labels, colors=self.colors,
           autopct="%0.2f%%", shadow=True)
    ax.set_title(self.title)
    return self.RenderFigure(fig, mimetype)


class BarPlot(Graph):
  def Initialize(self):
    self.values = []
    self.xlabels = []
    self.dlabels = []
    self.colors = []
  
  def AddDataset(self, data, xlabels, dlabels, colors):
    self.values.extend(data)
    self.xlabels.extend(xlabels)
    self.dlabels.extend(dlabels)
    self.colors.extend(colors)
  
  def GetImage(self, mimetype="image/png", **kwargs):
    fig = self.GetFigure(**kwargs)
    ind = arange(len(self.xlabels))
    width = 1.0/len(self.dlabels) - 0.05
    ax = fig.add_subplot(111, xticks = ind+width, xticklabels = self.xlabels)
    legend_bars = []
    legend_labels = []
    count = 0
    for v in self.values:
      p = ax.bar(ind+(width*count), v, width, color=self.colors[count])
      for i in range(len(self.xlabels)):
        ax.text(ind[i]+(width*(count+0.5)), v[i], str(v[i]), horizontalalignment = 'center', color = self.colors[count])
      legend_bars.append(p[0])
      legend_labels.append(self.dlabels[count])
      count += 1
    ax.legend(legend_bars, legend_labels, shadow=True)
    ax.set_title(self.title)
    return self.RenderFigure(fig, mimetype)


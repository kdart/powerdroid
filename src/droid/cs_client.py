#!/usr/bin/python2.4

# Copyright 2006, 2007 Google Inc.

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


"""Utilities to simplify use of ChartServer.

Functions here can help you automatically scale data to fit in a
ChartServer chart, or to generate the URL for a chart, or the whole
IMG tag.

ChartServer documentation --
https://www.corp.google.com/eng/designdocs/chartserver/chartserver.html
"""

__author__ = "cris@google.com (Cris Perdue)"


import math
import urllib
import string


def ScaleData(data, low, high):
  """Generic data rescaler.

  Args:
    data: a list of numbers.  "None" is also permitted, and maps
      to itself.
    low: min value in data will map to this.
    high: max value in data will map to this.
  Returns:
    A new list of numbers scaled to fit into the range
    from low to high.  If the data are all  equal,
    they all map to (high-low)/2.
  """
  dmin, dmax = _MinMax(data)
  # Handle data with zero range by putting it in the middle of the chart.
  if dmin == dmax:
    return [(high - low) / 2] * len(data)

  scale_factor = (high - low) / (dmax - dmin)
  def Scaler(x):
    if x is None:
      return None
    else:
      return low + ((x - dmin) * scale_factor)
  return map(Scaler, data)

# Define a mapping for extended encoding.
X_CHART_CODES_CHARS = string.ascii_uppercase + string.ascii_lowercase + \
  string.digits + '-' + '.'
X_CHART_CODES = []
for i in range(len(X_CHART_CODES_CHARS)):
  for j in range(len(X_CHART_CODES_CHARS)):
    X_CHART_CODES.append(X_CHART_CODES_CHARS[i] + X_CHART_CODES_CHARS[j])
X_N_CHART_CODES = len(X_CHART_CODES)
X_ENCODING_PARAMETER = 'e'

# These are used for the data encoding mapping functions.  Override these
# in the client code according to your needs.  The default is simple encoding.
S_CHART_CODES = string.ascii_uppercase + string.ascii_lowercase + string.digits
S_N_CHART_CODES = len(S_CHART_CODES)
S_ENCODING_PARAMETER = 's'

# Some external clients depend on these package variables.  These are for
# backward-compatibility.
CHART_CODES = S_CHART_CODES
N_CHART_CODES = S_N_CHART_CODES

# In the final chart we want the data to cover at least this
# much of the range from top to bottom.
_SPREAD = .5

def EncodeForChart(data, extended_encoding=False):
  """Converts integers into a string for ChartServer.

  Args:
    data: List of integers in the range (0 - 61 if simple encoding, 0-4095 if
          exended encoding).
          Any data point greater than (61 or 4095) is handled as the max
          supported for the encoding.
          Points with value None or less than 0 encode
          as "_" if simple encoding, or "__" if extended encoding, which
          display as blank sections of the chart.
    extended_encoding: a boolean indicating how to encode the input data.
  Returns:
    String that encodes the numbers for ChartServer.
  """
  EMPTY_CODE = ""
  CHART_CODES = ""
  N_CHART_CODES = 0

  if extended_encoding:
    EMPTY_CODE = '__'
    CHART_CODES = X_CHART_CODES
    N_CHART_CODES = X_N_CHART_CODES
  else:
    EMPTY_CODE = '_'
    CHART_CODES = S_CHART_CODES
    N_CHART_CODES = S_N_CHART_CODES

  def Encode(x):
    if x is None or x < 0:
      return EMPTY_CODE
    else:
      return CHART_CODES[min(x, N_CHART_CODES - 1)]
  return ''.join(map(Encode, data))


def FindScale(data):
  """Computes vertical scale information for the data.
  This aligns the top and bottom ticks exactly with the top
  and bottom of the chart.  You may like this, and ChartServer does
  not permit another way.

  Args:
    data: a sequence of numbers.  "None" is also permitted
      and is ignored.  There must be at least one number.
  Returns:
    A three-tuple of numbers - a value for the bottom of the chart,
    one for the top of the chart, and a distance between ticks, all in
    data coordinates.
  """
  # Top and bottom of the data
  data_low, data_high = _MinMax(data)
  data_range = data_high - data_low

  # Handle data with zero range by putting it in the middle
  # of the chart.
  flat = data_range == 0
  if flat:
    return _ScaleFlatData(data_high)

  # First and simplest cut at tick size: power of ten great enough
  # to cover the entire chart range.  Two tick intervals may be
  # needed to cover the data.
  tick1 = 10 ** int(math.ceil(math.log10(data_range)))

  assert tick1 <= 10 * data_range, "tick1 too big"

  # The tick marks will be placed at values ending in 0, 2, or 5,
  # which means they are at intervals of 10 ** x * (1 or 2 or 5).
  for tick in _Ticks(tick1):
    bottom_tick = _Quantize(data_low, tick)
    top_tick = _Quantize(data_high + tick, tick)
    # We like a large tick size provided it spreads out the data over
    # at least half the chart height.
    if data_range >= (top_tick - bottom_tick) * _SPREAD:
      return (bottom_tick, top_tick, tick)

    # Postconditions for current implementation:
    # bottom_tick <= data_low
    # data_high <= top_tick
    # data_range >= (top_tick - bottom_tick) * _SPREAD

  raise Exception("internal error in FindScale")


def ScaleZeroBased(data):
  """Scales data for a chart that will have 0 as the y origin.
  Looks for the largest tick size that places the midpoint
  of the data near enough the chart's y axis midpoint.  Also
  requires more than one tick.  Treats any data values less than 0
  as 0.
  """
  data_low, data_high = _MinMax(data)
  data_high = max(data_high, 0.0)  # Force data_high/low to at least zero.
  data_low  = max(data_low,  0.0)
  data_range = data_high - data_low
  data_mid = (data_high + data_low) / 2.0

  if data_range == 0.0:
    return _ScaleFlatData(data_high)

  # First and simplest cut at tick size: power of ten at least
  # as great as data_high.
  tick1 = 10 ** int(math.ceil(math.log10(data_high)))

  # The tick marks will be placed at values ending in 0, 2, or 5,
  # which means they are at intervals of 10 ** x * (1 or 2 or 5).
  for tick in _Ticks(tick1):
    # Consider the two placements of top_tick closest to twice
    # the data midpoint.
    for top_tick in (_Quantize((data_mid * 2) + tick, tick),
                      _Quantize((data_mid * 2), tick)):
      # We like a large tick size provided: there is more than one tick;
      # the data fits on the chart; and data_mid is near enough
      # to the middle of the chart height.
      if (tick < top_tick and data_high <= top_tick
          and 0.4 <= data_mid / top_tick <= 0.6):
        return (0, top_tick, tick)

def _ScaleFlatData(data_value):
  """Produces scaling information for data with zero range,
  putting the data near the middle.  Helper for FindScale.
  """
  if data_value == 0:
    # Data is exactly zero, scale it at the bottom of 0 to 1.
    return (0.0, 1.0, 1.0)
  else:
    double = _NearestDouble(data_value)
    # TODO(cris): compute a nicer tick interval for these cases.
    if double < 0:
      return (double, 0.0, double)
    else:
      return (0.0, double, double)


def _MinMax(data):
  """Find the minimum & maximum of the data (ignoring any items that are None.
  """
  numeric_data = [x for x in data if x is not None]
  return min(numeric_data), max(numeric_data)


def _Ticks(tenx):
  """Generates potential tick intervals, ending in 0, 2, or 5."""
  # Tick is the current candidate power of 10
  tick = tenx
  multiples = (5.0, 2.0, 1.0)
  n = len(multiples)
  # I indexes into the multiples round-robin fashion
  i = n - 1;
  while True:
    yield tick * multiples[i]
    i = (i + 1) % n
    if i == 0:
      tick = tick / 10.0


def _Quantize(y, unit):
  """Returns the greatest multiple of "unit" not more than y."""
  return unit * (y // unit)


def _NearestDouble(x):
  """Finds number near 2 * x that is an integer in the range 1-9 times 10 ** y.
  This is used when the chart is completely flat.

  Args:
    x: a number.

  Returns:
    A number "n" that is some power of ten times an integer
    in the range 1-9, such that the argument
    x is closer to half of n than any alternative n.
    Returns zero if given 0.
  """
  if x == 0:
    return 0

  factor = 1
  if x < 0:
    factor = -1
  # Base is the biggest power of 10 not greater than abs(x).
  base = 10 ** int(math.floor(math.log10(abs(x))))
  # x_norm is x, scaled to a range with known candidates for n.
  # 1 <= x_norm < 10 and x_norm == x * (10 ** k)
  x_norm = abs(x) / base
  # A largish number that will get smaller
  best_diff = 100
  # Will be "the answer"
  best = None
  # 2, 3 ... 10, 20
  list = range(2, 11) + [20]
  for n in list:
    diff = abs(x_norm - n / 2.0) / n
    if (diff < best_diff):
      best_diff = diff
      best = n
  return factor * best * base

def _EnsureSeqOfSeqs(data):
  """Wrap simple lists or tuples in a list."""
  if not data: # [] or ()
    return [data]
  if isinstance(data[0], list) or isinstance(data[0], tuple):
    return data
  return [data]


def ChartTag(data, width, height, top=None, bottom=None, tick='auto',
             extended_encoding=False, **params):
  """Returns an IMG tag for a ChartServer chart.
  Top and bottom must be given together, and then "tick"
  must not be "auto".
  The URL automatically includes labels for the y axis, with numbers
  at the top and bottom, unless tick is None.
  You will want to pass in some ChartServer parameters
  such as cht (for line color) and chl (x axis labels).

  Args:
    data: a sequence of numbers; some may have value of None, or a
    sequence of such sequences (for a multi-line chart).  In the
    latter case, all lists must have the same length.
    width: integer pixel width for the chart
    height: integer pixel height for the chart
    top: greatest data value displayable on the chart
    bottom: least data value displayable on the chart
    tick: One of: 'auto' - automatic; or a number: interval
      between tick marks, in the data space.  Defaults to "auto".
      If tick is 'auto', top and bottom can both be None,
      or top can be None and bottom 0.  Otherwise all three
      values must be supplied as numbers.
      No other combinations work at this time.
    extended_encoding: if set to true, uses the extended encoding character set
    to encode the input data.  This increases data resolution to 4096 values.
    if false (default), uses the simple encoding, which uses a resolution of 62
    values (0-61).
    other keyword parameters: the name and value are URLencoded
      and included in the URL.  If "cht" is not supplied, it
      defaults to "lb" (blue line chart).  You may define your
      own Y-axis labels by specifying the "chly" parameter or by
      specifying the "chxt" parameter and including "y" among
      its values.  If data is empty and you do not specify any
      Y-axis labels, the Y-axis will be set to "No Data".
  """
  chs = '%sx%s' % (width, height)
  url = ChartUrl(data, top, bottom, tick, extended_encoding=extended_encoding,
      chs=chs, **params)
  return ('<img width="%d" height="%d" src="%s">' %
          (width, height, url))


def ChartUrl(datasets, top=None, bottom=None, tick='auto',
    extended_encoding=False, **params):
  """Returns a URL for a ChartServer chart.
  This is useful for building an IMG tag with special classes or
  attributes.

  Args:
    Same as for ChartTag, except this does not take width or height.
  """
  datasets = _EnsureSeqOfSeqs(datasets)
  # Concatenate all lists for range calcuations, and check lengths
  flat_data = []
  for dataset in datasets:
    if len(dataset) != len(datasets[0]):
      raise Exception(
        'Datasets with different lengths passed to MultiDataChartUrl')
    flat_data.extend(dataset)
  # Value "None" indicates it is not yet defined.
  tick_unit = None
  y_labels = params.get('chly')
  have_y_labels = ('chly' in params
      or ('chxt' in params and 'y' in params['chxt']))

  if [x for x in flat_data if x is not None] == []:
    y_labels = '|No data|'
    scaled_datasets = datasets
  else:
    # Now define bottom, top, and tick_unit.
    if bottom is None and top is None and tick == 'auto':
      bottom, top, tick_unit = FindScale(flat_data)
    elif bottom == 0 and top is None and tick == 'auto':
      bottom, top, tick_unit = ScaleZeroBased(flat_data)
    elif (type(bottom) in (float, int) and
          type(top) in (float, int) and
          type(tick) in (float, int)):
      tick_unit = tick
    else:
      raise Exception('Bad scaling arguments to ChartUrl')

    # Scale the data.
    # For every element "x" in every dataset in scaled_datasets,
    # we want: 0 <= x < (62 || 4096) depending on if it is simple or extended
    # encoding.
    if extended_encoding:
      N_CHART_CODES = X_N_CHART_CODES
    else:
      N_CHART_CODES = S_N_CHART_CODES
    scale_factor = (N_CHART_CODES - .001) / (top - bottom)
    def Scale(y):
      if y is None:
        return None
      else:
        height = max( (y - bottom, 0.0) )
        return int(height * scale_factor)
    scaled_datasets = [map(Scale, dataset) for dataset in datasets]

    if not have_y_labels and y_labels is None:
      # Compute y_labels.

      # Magnitude is -1 if tick is .5, .2, or .1, -2 if tick is .05, .02,
      # or .01, i.e. exponent of power of 10 that is no greater than
      # tick_unit.
      magnitude = math.floor(math.log10(tick_unit) * 1.001)

      # Number of digits required after the decimal point to print ticks:
      precision = int(max(0, -1 * magnitude))

      # Chart labels:
      top_label = '%2.*f' % (precision, top)
      bottom_label = '%2.*f' % (precision, bottom)

      n_intervals = int(round((top - bottom) / tick_unit))
      y_labels = top_label + ('|' * n_intervals) + bottom_label

  def quote(pair):
    return '&%s=%s' % (urllib.quote(pair[0]), urllib.quote(pair[1]))

  if params.get('cht') is None:
    params['cht'] = 'lb'
  if not have_y_labels and y_labels:
    params['chly'] = y_labels
  graph_params = ''.join(map(quote, params.items()))
  encoded_data = \
    ','.join(
        map(lambda x: EncodeForChart(x, extended_encoding=extended_encoding),
          scaled_datasets))
  if extended_encoding:
    ENCODING_PARAMETER = X_ENCODING_PARAMETER
  else:
    ENCODING_PARAMETER = S_ENCODING_PARAMETER
  result = ('http://chart.apis.google.com/chart?chd=%s:%s%s' %
            (ENCODING_PARAMETER, encoded_data, graph_params))
  return result

#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Interface to the Google chart server from Python.
"""

__all__ = ['GetChartQuery', 'GetChartURL']

from pycopia.urlparse import urlencode


LOCALSERVERBASE="/charts/chart"
CHARTSERVERBASE="http://chartserver.corp.google.com/chart"

# Map chart types to server base. Basically says what chart types the
# Gtest server should handle. The default is Google chartserver.
_SERVERHANDLER = {
  "test": LOCALSERVERBASE,
  "tp": LOCALSERVERBASE,
}

# For simple data encoding scheme.
_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

def _tofloat(v):
  try:
    return float(v)
  except TypeError:
    return v

def SimpleEncode(data, defaultmin=False):
  """Encode a list of data into the chartserver "simple" encoding.
  The values in the list should be floats, or convertible to floats. A
  value of None indicates missing data. The data is scaled to the range
  that the chart server allows.
  """
  assert type(data) is list, "need to supply a list"
  if len(data) == 0:
    return "s:"
  if len(data) == 1:
    return "s:%s" % _CHARS[max(min(int(data[0]), 61), 0)]

  if isinstance(data[0], list): # a list of lists - multiple datasets
    alldata = []
    for subl in data:
      alldata.extend(subl)
    miny, rng = _GetDataLimit(alldata, defaultmin)
  else:
    miny, rng = _GetDataLimit(data, defaultmin)
    data = [data]

  if rng == 0:
    return "s:A"

  encoded = ["s:"]
  for subl in data:
    s = _EncodeDataPoints(subl, miny, rng)
    if len(s) > 0:
      encoded.append(s)
      encoded.append(",")
  return "".join(encoded)

def _GetDataLimit(data, defaultmin=False):
  data = map(_tofloat, data)
  # work around Python quirk: None value is always minimum!
  if defaultmin:
    miny = 0
  else:
    miny = min(filter(lambda v: type(v) is float, data))
  rng = max(data) - miny
  return miny, rng

def _EncodeDataPoints(data, miny, rng):
  s = []
  for datum in data:
    if datum is None:
      s.append("_")
    else:
      s.append(_CHARS[int(((datum-miny) / rng) * 61)])
  return "".join(s)

def EncodeLabels(labels):
  assert type(labels) is list, "labels need to be a list"
  return "|".join(map(str, labels))

def _EncodeComma(data):
  assert type(data) is list, "labels need to be a list"
  return ",".join(map(str, data))

def _IntegerEncode(data):
  assert type(data) is list, "need to supply a list"
  if isinstance(data[0], list): #if list of lists
    vals = [EncodeLabels(subl) for subl in data]
    return "i:%s" % _EncodeComma(vals)
  else:
    return "i:%s" % EncodeLabels(data)

# If refmin=True, use 0 as the minimum data point
def _EncodeData(data, dataencoding, defaultmin=False):
  if dataencoding == "s":
    return SimpleEncode(data, defaultmin)
  elif dataencoding == "i":
    return _IntegerEncode(data)
  else:
    raise ValueError, "invalid dataencoding type"

def GetChartQuery(data, cht, chc="corp", chs=(350, 200), dataencoding="s",
       chl=None, chly=None, chld=None, chco=None, **kwargs):
  """Construct the query part of a chart URL.
  """
  params = {"cht": cht, "chc": chc, "chs": "%sx%s" % chs}
  # Use default minimum 0 as reference when we draw any type of bar graphs
  if cht.startswith("b"):
    params["chd"] = _EncodeData(data, dataencoding, True)
  else:
    params["chd"] = _EncodeData(data, dataencoding)
  if chl:
    params["chl"] = EncodeLabels(chl)
  if chly:
    params["chly"] = EncodeLabels(chly)
  if chld:
    params["chld"] = EncodeLabels(chld)
  if chco:
    params["chco"] = _EncodeComma(chco)
  params.update(kwargs)
  return urlencode(params)

def GetChartURL(data, cht, **kwargs):
  """Construct the complete chart URL.

  The chart type (cht) determines the base part (host).
  """
  base = _SERVERHANDLER.get(cht, CHARTSERVERBASE)
  q = GetChartQuery(data, cht, **kwargs)
  return base + "?" + q

if __name__ == "__main__":
  testdata = [
            [1, 5, 7, 10, 55, 11, None, 22, 24],
            [7, 5, 2],
        ]
  for data in testdata:
    print GetChartURL(data, "lg", chl=map(str, data))



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



"""Run tests from test specifications.

 example measure set:
#    mclass, period, frequency, delay, runtime
[
 (voltage.VoltageMeasurer,       5.0, None, None, None),
 (current.POwerCurrentMeasurer, "fast", None, None, None),
]

"""


from droid.measure import sequencer
from droid.util import module


# shortcut/alias map for common measurers
_MODEMAP = {
  "V": "droid.measure.voltage.VoltageMeasurer",
  "C": "droid.measure.current.PowerCurrentMeasurer",
  "A": "droid.measure.current.CurrentMeasurer",
}

def ParseMeasureMode(mspec):
  rv = []
  parts = mspec.split(",")
  for part in parts:
    args, kwargs = ParseArgs(part)
    #         mclass, period, frequency, delay, runtime
    callargs = [None, "N", None, 0.0, None]
    for i, arg in enumerate(args):
      callargs[i] = arg
    for pos, kw in enumerate(("period", "frequency", "delay", "runtime")):
      try:
        arg = kwargs.pop(kw)
      except KeyError:
        pass
      else:
        callargs[pos + 1] = arg
    mclass = _MODEMAP.get(callargs[0][0].upper())
    if mclass:
      callargs[0] = mclass
    rv.append(callargs)
  return rv


def ParseArgs(arguments):
  args = []
  kwargs = {}
  targs = arguments.split(":")
  for i, arg in enumerate(targs):
    vals = arg.split("=", 1)
    if len(vals) == 2:
      kwargs[vals[0]] = _EvalArg(vals[1])
    else:
      args.append(_EvalArg(vals[0]))
  return args, kwargs


def _EvalArg(arg):
  try:
    return eval(arg)
  except:
    return arg


def RunSequencer(context, measureset):
  """Fetch, populate, run, and close the test sequencer.

  The context is a measurement context configuration object.
  The measureset is a sequence of tuples, each tuple represents the
  arguments to the sequencer's AddFunction method.
  """
  seq = sequencer.Sequencer(context)
  for mspec in measureset:
    mclass, period, frequency, delay, runtime = mspec
    if delay is None:
      delay = 0.0
    if type(mclass) is str:
      mclass = module.GetObject(mclass)
    measurer = mclass(context)
    if type(period) is str:
      specialmode = period[0].upper()
      if specialmode == "F": # fast mode
        seq.AddFunction(measurer, measurer.measuretime)
      elif specialmode in "ND": # normal or default, use default delay
        seq.AddFunction(measurer, context.delay, None, delay, runtime)
      else: 
        seq.AddFunction(measurer, period, frequency, delay, runtime)
    else:
        seq.AddFunction(measurer, period, frequency, delay, runtime)
  try:
    seq.Run()
  finally:
    sequencer.Close()



if __name__ == "__main__":
  spec = ParseMeasureMode("voltage:30,current:fast,callcheck:60:delay=30")
  print spec



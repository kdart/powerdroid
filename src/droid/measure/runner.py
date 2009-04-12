#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright Google Inc. All Rights Reserved.

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
  "P": "droid.measure.core.TimeProgressMeter",
}

class MeasureSet(list):
  def Add(self, measurer, period="N", frequency=None, delay=0.0,
      runtime=None):
    self.append([measurer, period, frequency, delay, runtime])


def ParseMeasureMode(context, mspec):
  rv = MeasureSet()
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
    classname = _MODEMAP.get(callargs[0][0].upper(), callargs[0])
    mclass = module.GetObject(classname)
    measurer = mclass(context)
    callargs[0] = measurer
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
    measurer, period, frequency, delay, runtime = mspec
    if delay is None:
      delay = 0.0
    if type(period) is str:
      specialmode = period[0].upper()
      if specialmode == "F": # fast mode
        seq.AddFunction(measurer, measurer.measuretime)
      elif specialmode in "ND": # normal or default, use default delay
        seq.AddFunction(measurer, measurer.delaytime, None, delay, runtime)
      else: 
        seq.AddFunction(measurer, period, frequency, delay, runtime)
    else:
        seq.AddFunction(measurer, period, frequency, delay, runtime)
  try:
    seq.Run()
  finally:
    sequencer.Close()





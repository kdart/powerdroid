#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Perform paced measurements or other functions.

The Sequencer object lets you run functions at different rates,
time delays, and time spans.

Below is the basic interface a measurement object must have if it is to be
added to a Sequencer. Basically, the AddFunction method just
needs a callable that takes two arguments: timestamp and some value taken
from the previous measurement objects return value. However, usually a
measurement would have some settings or state taken from a context.  All
measurement functions should execute fast, faster than the clock period of
the measurement sequencer (1/16 second by default). They should contain no
sleeps (just use a properly timed function, or set of functions,  if you
need that).

class SampleMeasurer(object):
  def __init__(self, context):
    pass

  def __call__(self, timestamp, lastvalue):
    return lastvalue # or a new value, but some value.

"""

import sys
import errno

from pycopia import timelib
from pycopia import timespec
from pycopia import asyncio
from pycopia.OS import rtc  # Currenly, only Linux has this module.

from droid.measure import core
from droid.util import module


class StopSequencer(Exception):
  pass


class MeasureSet(list):
  def Add(self, measurer, period="N", frequency=None, delay=0.0,
      runtime=None):
    self.append([measurer, period, frequency, delay, runtime])


def ParseMeasureMode(context, mspec):
  rv = MeasureSet()
  defaultdatafilename = context.datafilename
  for jobspec in mspec.split(","):
    args, kwargs = ParseMeasureArgs(jobspec)
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
    classname = core.MEASUREALIAS.get(callargs[0].lower(), callargs[0])
    mclass = module.GetObject(classname)
    context.datafilename = kwargs.pop("datafile", defaultdatafilename)
    measurer = mclass(context)
    callargs[0] = measurer
    rv.append(callargs)
  return rv


def ParseMeasureArgs(arguments):
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
    return int(arg)
  except ValueError:
    try:
      return float(arg)
    except ValueError:
      try:
        return GetSecondsFromTimespec(arg)
      except ValueError:
        return arg # a special case string, most likely


class _Sequencer(rtc.RTC, asyncio.PollerInterface):
  """Paces a set of measurements using the RTC and poller."""

  def __init__(self, context):
    super(_Sequencer, self).__init__()
    self._tickrate = context.clockrate
    try:
      self.irq_rate_set(self._tickrate)
    except IOError, why:
      super(_Sequencer, self).close()
      if why[0] == errno.EINVAL:
        raise core.MeasureError("%s: tick rate must be a power of 2" % (why,))
      else:
        raise
    self._debug = context.flags.DEBUG
    self.Clear()

  def __str__(self):
    return "Sequencer jobs: %r" % (self._sets,)

  def readable(self):
    return True

  def close(self):
    self.Stop()
    self.Clear()
    super(_Sequencer, self).close()

  def Clear(self):
    self._sets = {}
    self._rates = set()
    self._removedjobs = []
    self._ticks = 0
    self._lastvalue = None
    self._running = False

  def read_handler(self):
    count, irq = self.read()
    if irq & rtc.RTC_PF:
      while count > 0: # in case we missed an interrupt
        self._ticks += 1
        for rate in self._rates.copy():
          if self._ticks % rate == 0:
            for callback, oneshot in self._sets[rate]:
              self._lastvalue = callback(timelib.now(), self._lastvalue)
              if oneshot:
                self.DeleteJob((callback, rate, oneshot))
        count -= 1

  def error_handler(self, ex, val, tb):
    if ex is StopSequencer or ex is KeyboardInterrupt:
      raise ex, val
    if self._debug:
      from pycopia import debugger
      debugger.post_mortem(tb, ex, val)
    else:
      raise ex, val, tb

  def AddJob(self, job):
    measurer, ticks, oneshot = job
    try:
      jl = self._sets[ticks]
    except KeyError:
      jl = self._sets[ticks] = []
      self._rates.add(ticks)
    jl.append((measurer, oneshot))

  def DeleteJob(self, job):
    measurer, ticks, oneshot = job
    try:
      jl = self._sets[ticks]
    except KeyError:
      return
    jl.remove((measurer, oneshot))
    if not jl:
      del self._sets[ticks]
      self._rates.remove(ticks)
    if oneshot and type(measurer) is not JobStarter: # XXX hack?
      self._removedjobs.append(measurer) # save for later finalizing
    if not self._sets:
      raise core.AbortMeasurements("No more measurements to run.")

  def AddFunction(self, callback, period=1.0, frequency=None,
        delay=0.0, runtime=None):
    """Add a functional object (callable) for timed execution.

    Args:
      callback: a callable.
      period (optional float or timespec): the time period between
          each call to the callback function.
      frequency (optional float): the frequency of calling, in Hz.
      Overrides period if provided.
      (The options period and frequency are mutually exclusive)
      delay (float): Will delay running the function for <delay> seconds
      after the sequencer is started. Default is to start immediatly.
      runtime (float): The span of time, in seconds, the function
      will be called after it is started. By default it runs until the
      sequencer is stopped.
    """
    if not (period or frequency) and delay:
      self.AddJob(self._GetOneshot(callback, delay))
      return
    job = self._GetJob(callback, period, frequency)
    if delay:
      self.AddJob(self._GetOneshot(JobStarter(job), delay))
    else:
      self.AddJob(job)
    if runtime:
      if type(runtime) is str:
        runtime = GetSecondsFromTimespec(runtime)
      self.AddJob(self._GetOneshot(JobStopper(job), runtime + delay))

  def DeleteFunction(self, callback, period=1.0, frequency=None):
    job = self._GetJob(callback, period, frequency)
    self.DeleteJob(job)

  def _GetJob(self, callback, period, frequency):
    period = GetPeriod(period, frequency)
    if period < 1.0 / self._tickrate:
      raise core.MeasureError(
          "Period of %s is too small for sequencer clock rate of %s." % (
              period, self._tickrate))
    return (callback, int(period * self._tickrate), False)

  def _GetOneshot(self, callback, delay):
    if type(delay) is str:
      delay = GetSecondsFromTimespec(delay)
    return (callback, int(delay * self._tickrate), True)

  def AddMeasureset(self, measureset):
    """Add a pre-parsed measurement set."""
    for mspec in measureset:
      measurer, period, frequency, delay, runtime = mspec
      if delay is None:
        delay = 0.0
      if type(period) is str:
        specialmode = period[0].upper()
        if specialmode == "F": # fast mode
          self.AddFunction(measurer, measurer.measuretime, None, delay, runtime)
        elif specialmode in "ND": # normal or default, use default delay
          self.AddFunction(measurer, measurer.delaytime, None, delay, runtime)
        else: 
          self.AddFunction(measurer, GetSecondsFromTimespec(period), 
              frequency, delay, runtime)
      else:
          self.AddFunction(measurer, period, frequency, delay, runtime)

  def Start(self):
    if not self._running:
      for rate in self._rates:
        for callback, oneshot in self._sets[rate]:
          if hasattr(callback, "Initialize"):
            callback.Initialize()
      asyncio.poller.register(self)
      self.periodic_interrupt_on()
      self._running = True

  def Stop(self):
    if self._running:
      self.periodic_interrupt_off()
      asyncio.poller.unregister(self)
      for rate in self._rates:
        for callback, oneshot in self._sets[rate]:
          if hasattr(callback, "Finalize"):
            callback.Finalize()
      # Finalize measurerers that were removed during the run.
      while self._removedjobs:
        callback = self._removedjobs.pop()
        if hasattr(callback, "Finalize"):
          callback.Finalize()
      self._running = False

  def Run(self):
    """Primary event loop."""
    self.Start()
    try:
      try:
        while 1:
          asyncio.poller.poll(-1)
      except StopSequencer, ended:
        return ended
    finally:
      self.Stop()



# The measurement timer must be a singleton, due to the nature of the RTC
# device and kernel interface (it may not be shared).
_measurement_timer = None

def Sequencer(context):
  global _measurement_timer
  if _measurement_timer is None:
    _measurement_timer = _Sequencer(context)
  _measurement_timer.Clear()
  # This makes the measurement set end at the time given by timespan.
  _measurement_timer.AddFunction(_StopSequencer, context.timespan)
  return _measurement_timer


def SequencerClose():
  global _measurement_timer
  mt = _measurement_timer
  _measurement_timer = None
  mt.close()


def _StopSequencer(timestamp, lastvalue):
  raise StopSequencer, timestamp


def RunSequencer(context, measureset):
  """Fetch, populate, run, and close the test sequencer.

  The context is a measurement context configuration object.
  The measureset is a sequence of tuples, each tuple represents the
  arguments to the sequencer's AddFunction method.
  """
  seq = Sequencer(context)
  seq.AddMeasureset(measureset)
  try:
    seq.Run()
  finally:
    SequencerClose()


def RunMeasureSpec(context, measurespec):
  measureset = ParseMeasureMode(context, measurespec)
  if context.useprogress:
    measureset.Add(core.TimeProgressMeter(context))
  RunSequencer(context, measureset)


class JobStarter(object):
  """Special handler that inserts a job when invoked, presumably after a
  delay.
  """
  def __init__(self, job):
    self.job = job

  def Initialize(self):
    try:
      self.job[0].Initialize()
    except AttributeError:
      pass

  def Finalize(self):
    try:
      self.job[0].Finalize()
    except AttributeError:
      pass

  def __call__(self, timestamp, value):
    _measurement_timer.AddJob(self.job)
    return value


class JobStopper(object):
  def __init__(self, job):
    self.job = job

  def __call__(self, timestamp, value):
    _measurement_timer.DeleteJob(self.job)
    return value


def GetPeriod(period, frequency):
    if frequency is not None:
      return 1.0 / float(frequency)
    if type(period) is str:
      return GetSecondsFromTimespec(period)
    return period


_ts_parser = timespec.TimespecParser()

def GetSecondsFromTimespec(timespec):
  _ts_parser.parse(timespec)
  return _ts_parser.seconds



# unit test...
if __name__ == "__main__":
  class _TestingMeasurer(object):
    def __init__(self, id):
      self._id = id

    def __call__(self, timestamp, lastvalue):
      print timestamp, self._id, lastvalue
      if lastvalue is None:
        return 1
      return lastvalue + 1

  ctx = core.MeasurementContext()
  ctx.timespan = 300.0
  mc = Sequencer(ctx)
  mc.AddFunction(_TestingMeasurer("4SEC"), period=4.0)
  mc.AddFunction(core.TimeProgressMeter(ctx), period=10)
  mc.AddFunction(_TestingMeasurer("DELAYED_2SEC"), period=2.0, delay=30)
  mc.AddFunction(_TestingMeasurer("2SEC4TENSEC"), period=2.0, delay=40,
      runtime=10)
  print mc.Run()
  Close()
  print "=== running 6, 7, 10, 30 second jobs. ==="
  for t in (6, 7, 10, 30):
    ctx.timespan = t
    mc = Sequencer(ctx)
    mc.AddFunction(_TestingMeasurer("1SEC"), period=1.0)
    mc.AddFunction(_TestingMeasurer("2SEC"), period=2.0)
    mc.AddFunction(_TestingMeasurer("3SEC"), period=3.0)
    starttime = timelib.now()
    print mc.Run()
    print "elapsed:", timelib.now() - starttime, "should be:", t
    print
    Close()


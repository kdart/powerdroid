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



"""Perform paced measurements or other functions.

The MeasurementHandler object lets you run functions at different rates,
time delays, and time spans.

The MeasurementController object controls the handler, and makes it easy
to add time delayed function objects.

Below is the basic interface a measurement object must have if it is to be
added to a MeasurementController. Basically, the AddFunction method just
needs a callable that takes two arguments: timestamp and some value taken
from the previous measurement objects return value. However, usually a
measurement would have some settings or state taken from a context.  All
measurement functions should execute fast, faster than the clock period of
the measurement sequencer (1/16 second by default). They should contain
no sleeps (just use a properly timed function if you need that).

class SampleMeasurer(object):
  def __init__(self, context):
    pass

  def __call__(self, timestamp, lastvalue):
    return lastvalue # or a new value, but some value.

"""

import sys

from pycopia import dictlib

from droid.storage import Storage


class Error(Exception):
  pass

class AbortMeasurements(Error):
  pass

class MeasureError(Error):
  pass


class ConfigDict(dictlib.AttrDict):
  def __init__(self, name):
    super(ConfigDict, self).__init__()
    self._configname = name

  def __str__(self):
    s = ["Config for %r:" % self._configname]
    for name, value in self.items():
      if not name.startswith("_"):
        s.append("%20.20s : %s" % (name, value))
    return "\n".join(s)


def MeasurementContext(**kwargs):
  """Constructor for measurement data holder.
  
  This object sets default values for measurements. (e.g. time span,
  sample rate, etc.). You can override any with optional keyword arguments,
  or set them at any time later. Most measurer objects take one as a
  paramter.

  Returns:
    The primary storage RootContainer, holding common measurement
    parameters, pre-set to default values.
  """
  ctx = Storage.GetConfig()
  # measurement context global settings
  ctx.timespan = 3600.0    # total measurement span
  ctx.calltime = 60.0     # time to keep calls up, if any
  ctx.clockrate = 16      # clock rate of sequencer, in Hz
  ctx.delay = 5           # default delay between measurements 
  ctx.useprogress = False # show a progress meter
  ctx.reset = False       # perform an instrument reset.
  ctx.triggered = False   # if performing a triggered measurement
  ctx.capturemode = "N"   # default normal capture mode.

  # trigger parameters have their own namespace.
  ctx.trigger = ConfigDict("trigger")
  ctx.trigger.slope = "POS"
  ctx.trigger.count = 1
  ctx.trigger.offsetpoint = -2048
  ctx.trigger.level = 1.0
  ctx.trigger.hysteresis = 0.05

  # Settings related to power supplies
  ctx.voltmeters = ConfigDict("voltmeters")
  ctx.voltmeters.resolution = "medium"

  ctx.testsets = ConfigDict("testsets")
  ctx.testsets.txpower = -75.0 # dBm
  ctx.testsets.profile = "EDGE"
  ctx.testsets.dialednumber = "6502849239"
  ctx.testsets.downlinkaudio = "none"

  ctx.callplan = ConfigDict("callplan")
  ctx.callplan.include = True # send callplan info if True
  ctx.callplan.orignumber = "5141001130"
  ctx.callplan.numbertype = "network" # UNKNown|INATional|NATional|NETWork|DEDicated
  ctx.callplan.plan = "national" # UNKNown|ISDN|NATional|PRIVate|TELex|DATA
  ctx.callplan.screening = "network" # UNSCreened|UVPassed|UVFailed|NETWork
  ctx.callplan.presentation = "allowed" # ALLowed|RESTricted|NNAVailable

  # bluetooth test sets
  ctx.bttestsets = ConfigDict("bttestsets")
  ctx.bttestsets.use = False
  ctx.bttestsets.btaddress = 0
  ctx.bttestsets.audioroute = "inout"
  ctx.bttestsets.autoanswer = True
  ctx.bttestsets.pin = 0

  # datafiles 
  ctx.datafiles = ConfigDict("datafiles")
  ctx.datafiles.format = "G"
  ctx.datafiles.name = None

  # power supplies
  ctx.powersupplies = ConfigDict("powersupplies")
  ctx.powersupplies.voltage = 3.8
  ctx.powersupplies.subsamples = 4096
  ctx.powersupplies.subsampleinterval = 15.6e-6

  # generic audio generators
  ctx.audiogenerator = ConfigDict("audiogenerator")
  ctx.audiogenerator.frequency = "1000 Hz"
  ctx.audiogenerator.pulsed = False
  ctx.audiogenerator.voltage = "1.5 V"
  ctx.audiogenerator.power = -3.0 #  dBm0
  ctx.audiogenerator.coupling = "DC"
  ctx.audiogenerator.outputstate = True

  # generic audio analyzers
  ctx.audioanalyzer = ConfigDict("audioanalyzer")
  ctx.audioanalyzer.multimeasure = True
  ctx.audioanalyzer.measurecount = 30
  ctx.audioanalyzer.continuous = False
  ctx.audioanalyzer.dosinad = True
  ctx.audioanalyzer.dofrequency = True
  ctx.audioanalyzer.frequency = "1000 Hz"
  ctx.audioanalyzer.expected_voltage = "0.8 V"
  ctx.audioanalyzer.detectortype = "PEAK"
  ctx.audioanalyzer.filtertype = "BPAS300"

  # For multitone analyzer
  ctx.multitoneanalyzer = ConfigDict("multitoneanalyzer")
  ctx.multitoneanalyzer.multimeasure = True
  ctx.multitoneanalyzer.measurecount = 10
  ctx.multitoneanalyzer.continuous = False
  ctx.multitoneanalyzer.dosinad = False
  ctx.multitoneanalyzer.dofrequency = False
  ctx.multitoneanalyzer.measuremode = "DOWN"
  ctx.multitoneanalyzer.expected_voltage = "1.0 V"
  ctx.multitoneanalyzer.usegenerator = True # set measure freqs. same as generator's
  ctx.multitoneanalyzer.frequencies = [300.0, 440.0, 580.0, 720.0, 860.0, 
      1000.0, 1140.0, 1280.0, 1420.0, 1560.0, 1700.0, 1840.0, 1980.0, 
      2120.0, 2260.0, 2400.0, 2540.0, 2680.0, 2820.0, 3000.0]

  # For multitone generator
  ctx.multitonegenerator = ConfigDict("multitonegenerator")
  ctx.multitonegenerator.preset = "MTA140"
  ctx.multitonegenerator.uplinkstate = False
  ctx.multitonegenerator.uplinklevels = 1.0
  ctx.multitonegenerator.downlinkstate = True
  ctx.multitonegenerator.downlinklevels = 70.0
  ctx.multitonegenerator.frequencies = [300.0, 440.0, 580.0, 720.0, 860.0, 
      1000.0, 1140.0, 1280.0, 1420.0, 1560.0, 1700.0, 1840.0, 1980.0, 
      2120.0, 2260.0, 2400.0, 2540.0, 2680.0, 2820.0, 3000.0]

  # measurers
  ctx.measure = ConfigDict("measure")
  ctx.measure.continuous = False
  ctx.measure.timeout = 10.0 # zero means no timeout
  ctx.measure.external_attenuation = 10.0 # dB on RF signal
  # SRB loopback BER tests
  ctx.measure.srbber = ConfigDict("srbber")
  ctx.measure.srbber.count = 80000
  ctx.measure.srbber.txpower = -75.0 # dBm, -85 at device with 10dB attenuator
  ctx.measure.srbber.delay = 0.5
  ctx.measure.srbber.framedelay = -1 # less than zero means automatic delay selection

  # caller overrides.
  ctx.update(kwargs)
  return ctx


class OldMeasurer(object):
  """Base class for all measurers.
  """
  def __init__(self, ctx):
    assert ctx.voltage < 5.0 # we don't want to "smoke" the DUT.
    self._context = ctx
    self._device = ctx.device
    self._report = ctx.report
    if ctx.reset:
      self._device.Reset()
      self._device.ask("*OPC?")
    self._device.Errors() # clear errors
    self.measuretime = self._device.Prepare(ctx)

  def Run(self):
    capturemode = self._context.capturemode
    try:
      if capturemode == "S":
        self.Single()
      elif capturemode == "R":
        self.Raw(5, self._context.timespan)
    finally:
      self._report.Finalize()
      self._report.close()

  def Single(self):
    raise NotImplementedError

  def Raw(self, N, timeout=0.0):
    raise NotImplementedError


class BaseMeasurer(object):
  """Base class and example for a typical measurement function."""
  # catchers to avoid AttributeError
  datafile = None 
  measuretime = 1.0

  def __init__(self, context):
    pass

  def __call__(self, timestamp, lastvalue):
    return lastvalue # or a new value, but some value.

  def Initialize(self, context):
    pass

  def Finalize(self):
    pass


class TimeProgressMeter(BaseMeasurer):
  """Print progress to stderr.

  Special measure function that writes a timestamp and the last value to
  stderr, on same line repeatedly.

  Args:
    context (mapping) a measurement context.
  """

  def __init__(self, context):
    self._runtime = context.timespan
    self._starttime = None

  def __call__(self, timestamp, value):
    if self._starttime is None:
      self._starttime = timestamp
      return value
    dt = timestamp - self._starttime
    percent = dt / self._runtime  * 100
    sys.stderr.write("                                                     \r")
    sys.stderr.write("%12.2fs (%6.2f%%) %s" % (dt, percent, value))
    sys.stderr.flush()
    return value



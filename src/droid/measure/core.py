#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

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

 example measure set:
[
 (voltage.VoltageMeasurer,       5.0, None, None, None, "voltage"),
 (current.POwerCurrentMeasurer, "fast", None, None, None, "current"),
]

"""

import sys

from pycopia import dictlib

#from droid.reports import core as reportscore
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
  ctx.timespan = 1800.0   # default measurement time span
  ctx.calltime = 60.0     # time to keep calls up, if any
  ctx.clockrate = 16      # clock rate of sequencer, in Hz
  ctx.delay = 5           # default delay between measurements 
  ctx.timeout = "T3s"     # GPIB instrument timeout 
  ctx.useprogress = False # show a progress meter
  ctx.reset = False       # perform an instrument reset.
  ctx.triggered = False   # if performing a triggered measurement
  ctx.capturemode = "N"   # default normal capture mode.
  ctx.SIM = "T-Mobile"   # What SIM is in the DUT
  ctx.datafilename = "-" 

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

  # power supplies
  ctx.powersupplies = ConfigDict("powersupplies")
  ctx.powersupplies.voltage = 3.8     # volts
  ctx.powersupplies.timeout = "T3s"   # GPIB timeout contant names
  ctx.powersupplies.window = "HANN"   # 'HANN' or 'RECT'
  ctx.powersupplies.detector = "ACDC" # 'ACDC' or 'DC'
  ctx.powersupplies.maxcurrent = 3.0 # for agilent can be: 3.0, 1.0 or 0.020
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

  # modems
  ctx.modems = ConfigDict("modems")
  ctx.modems.autoanswer = False
  ctx.modems.dialednumber = "6502849239"
  ctx.modems.autoredial = False
  ctx.modems.redialattempts = 5

  # self testing
  ctx.debug = ConfigDict("debug")
  ctx.debug.sleep = 0.0

  ### measurers ###
  # common settings
  ctx.measure = ConfigDict("measure")
  ctx.measure.continuous = False
  ctx.measure.timeout = 10.0 # zero means no timeout
  ctx.measure.external_attenuation = 10.0 # dB on RF signal

  # SRB loopback BER tests
  ctx.measure.srbber = ConfigDict("srbber")
  ctx.measure.srbber.count = 80000
  ctx.measure.srbber.multimeasure = True
  ctx.measure.srbber.measurecount = 10
  ctx.measure.srbber.txpower = -75.0 # dBm, -85 at device with 10dB attenuator
  ctx.measure.srbber.delay = 0.5
  ctx.measure.srbber.framedelay = -1 # less than zero means automatic delay selection

  # transmitter power measurements
  ctx.measure.transmitpower = ConfigDict("transmitpower")
  ctx.measure.transmitpower.multimeasure = True
  ctx.measure.transmitpower.measurecount = 10
  ctx.measure.transmitpower.burstcapture = "ALL"
  ctx.measure.transmitpower.estimated_power = True # needed for 8PSK modulation
  ctx.measure.transmitpower.trigger_qualification = True

  # caller overrides.
  ctx.update(kwargs)
  return ctx


# Shortcut/alias map for common measurers
MEASUREALIAS = {
  "voltage": "droid.measure.voltage.VoltageMeasurer",
  "current": "droid.measure.current.CurrentMeasurer",
  "progress": "droid.measure.core.TimeProgressMeter",
  # power supply measurers
  "pscurrent": "droid.measure.current.PowerCurrentMeasurer",
  "psvoltage": "droid.measure.current.PowerVoltageMeasurer",
  "pschargecurrent": "droid.measure.current.PowerSupplyChargeCurrentMeasurer",
  # PS controllers
  "pson": "droid.measure.core.PowerSupplyOutputOn",
  "psoff": "droid.measure.core.PowerSupplyOutputOff",
  "usbon": "droid.measure.core.ChargerOn",
  "usboff": "droid.measure.core.ChargerOff",
  "toggleusb": "droid.measure.core.ToggleCharger",
  # testset controllers
  "tstoggleoutput": "droid.measure.testset.ToggleRFOutput",
  # for unit testing
  "null": "droid.measure.core.NullMeasurer",
  "debug": "droid.measure.core.DebugMeasurer",
}


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

  def Single(self):
    raise NotImplementedError

  def Raw(self, N, timeout=0.0):
    raise NotImplementedError


class BaseMeasurer(object):
  """Base class and example for a typical measurement function.

  Objects based on this class are intended for use in the measurement
  sequencer. 
  """
  # Default values to avoid AttributeError
  datafile = None 
  measuretime = 1.0
  delaytime = 30.0

  def __init__(self, context):
    pass

  def __call__(self, timestamp, lastvalue):
    return lastvalue # or a new value, but some value.

  def Initialize(self):
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


class ToggleCharger(BaseMeasurer):
  """Toggle the charger output state. 

  This controls the USB via the USB switch in The Android lab.
  """
  def __init__(self, ctx):
    super(ToggleCharger, self).__init__(ctx)
    self._device = ctx.environment.powersupply

  def Initialize(self):
    self._chargerstate = self._device.GetChargerOutputState()

  def __call__(self, timestamp, lastvalue):
    self._chargerstate = not self._chargerstate
    self._device.SetChargerOutputState(self._chargerstate)
    return lastvalue


class ChargerOff(BaseMeasurer):
  """Force charger output (USB controller) off.
  """
  def __init__(self, ctx):
    super(ChargerOff, self).__init__(ctx)
    self._device = ctx.environment.powersupply

  def __call__(self, timestamp, lastvalue):
    self._device.SetChargerOutputState(False)
    return lastvalue


class ChargerOn(BaseMeasurer):
  """Force charger output (USB controller) on.
  """
  def __init__(self, ctx):
    super(ChargerOn, self).__init__(ctx)
    self._device = ctx.environment.powersupply

  def __call__(self, timestamp, lastvalue):
    self._device.SetChargerOutputState(True)
    return lastvalue


class PowerSupplyOutputOff(BaseMeasurer):
  """Set power supply output off.
  """
  def __init__(self, ctx):
    super(PowerSupplyOutputOff, self).__init__(ctx)
    self._device = ctx.environment.powersupply

  def __call__(self, timestamp, lastvalue):
    self._device.SetOutputState(False)
    return lastvalue


class PowerSupplyOutputOn(BaseMeasurer):
  """Set power supply output on.
  """
  def __init__(self, ctx):
    super(PowerSupplyOutputOn, self).__init__(ctx)
    self._device = ctx.environment.powersupply

  def __call__(self, timestamp, lastvalue):
    self._device.SetOutputState(True)
    return lastvalue


class NullMeasurer(BaseMeasurer):
  """Do nothing. Useful for self-testing.
  """
  def __call__(self, timestamp, lastvalue):
    return lastvalue


class DebugMeasurer(BaseMeasurer):
  """Do nothing. Useful for debugging.
  """
  def __init__(self, context):
    self._datafile = context.datafilename
    self._sleeptime = context.debug.sleep

  def Initialize(self):
    global scheduler
    from pycopia import scheduler
    print >>sys.stderr, "DebugMeasure (%s): Initialize()" % self._datafile

  def Finalize(self):
    print >>sys.stderr, "DebugMeasure (%s): Finalize()" % self._datafile

  def __call__(self, timestamp, value):
    print >>sys.stderr, self._datafile, "->", timestamp, value
    scheduler.sleep(self._sleeptime)
    return value



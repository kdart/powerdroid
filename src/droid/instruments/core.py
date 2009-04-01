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



"""Common components of instrument package.

"""

import sys

import numpy
from pycopia import aid

from droid.util import module
from droid.physics import physical_quantities
PQ = physical_quantities.PhysicalQuantity


ON = aid.Enum(1, "ON")
OFF = aid.Enum(0, "OFF")


# TODO(dart) get from config or storage
from pycopia.dictlib import AttrDict
INSTRUMENTS = {
  "controller": AttrDict(
        object="droid.instruments.gpib.GpibController",
        gpibname="gpib0"),
  "fluke45": AttrDict(
        object="droid.instruments.multimeter.Fluke45",
        port="/dev/ttyS0",
        serial="9600 8N1",
        clicommands="droid.instruments.serialCLI.SerialInstrumentCLI",
        prompt="=>\r\n"),
  "ps1": AttrDict(
        object="droid.instruments.powersupply.Ag66319D",
        clicommands="droid.instruments.powersupplyCLI.Ag66319D_CLI",
        gpibboard=0, gpibpad=7,
        gpibname="ps1"),
  "ps1dvm": AttrDict(
        object="droid.instruments.powersupply.Ag66319dDVM",
        gpibboard=0, gpibpad=7,
        gpibname="ps1"),
  "n4010a": AttrDict(
        object="droid.instruments.testset.N4010a",
        clicommands="droid.instruments.testsetCLI.N4010aCLI",
        gpibboard=0, gpibpad=15,
        gpibname="n4010a"),
  "n4010a_afgen": AttrDict(
        object="droid.instruments.testset.N4010aAudioGenerator",
        clicommands="droid.instruments.testsetCLI.N4010aAudioGeneratorCLI",
        gpibboard=0, gpibpad=15,
        gpibname="n4010a"),
  "n4010a_afana": AttrDict(
        object="droid.instruments.testset.N4010aAudioAnalyzer",
        clicommands="droid.instruments.testsetCLI.N4010aAudioAnalyzerCLI",
        gpibboard=0, gpibpad=15,
        gpibname="n4010a"),
  "ag8960": AttrDict(
        object="droid.instruments.testset.Ag8960",
        clicommands="droid.instruments.testsetCLI.Ag8960CLI",
        gpibboard=0, gpibpad=14,
        gpibname="ag8960"),
  "ag8960_afgen": AttrDict(
        object="droid.instruments.testset.Ag8960AudioGenerator",
        clicommands="droid.instruments.testsetCLI.Ag8960_AFG_CLI",
        gpibboard=0, gpibpad=14),
  "ag8960_afana": AttrDict(
        object="droid.instruments.testset.Ag8960AudioAnalyzer",
        clicommands="droid.instruments.testsetCLI.Ag8960_AFA_CLI",
        gpibboard=0, gpibpad=14),
  "ag8960_mtgen": AttrDict(
        object="droid.instruments.testset.Ag8960MultitoneAudioGenerator",
        clicommands="droid.instruments.testsetCLI.Ag8960_MTG_CLI",
        gpibboard=0, gpibpad=14),
  "ag8960_mtana": AttrDict(
        object="droid.instruments.testset.Ag8960MultitoneAudioAnalyzer",
        clicommands="droid.instruments.testsetCLI.Ag8960_MTA_CLI",
        gpibboard=0, gpibpad=14),
  "dpo4104": AttrDict( # uses USBTMC
        object="droid.instruments.oscilloscope.TekDPO4104Oscilloscope",
        clicommands="droid.instruments.oscilloscope_cli.TekDPOCLI",
        manufacturer="Tektronix",
        model="DPO4104"),
  "mock": AttrDict(object="droid.instruments.mocks.MockDevice"),
}


# TODO(dart) put in config file
GENERICMAP = {
  "afgenerator1": "ag8960_afgen",
  "afgenerator2": "n4010a_afgen",
  "afanalyzer1": "ag8960_afana",
  "afanalyzer2": "n4010a_afana",
  "multitonegen": "ag8960_mtgen",
  "multitoneana": "ag8960_mtana",
  "powersupply": "ps1",
  "dvm": "ps1dvm",
  "bttestset": "n4010a",
  "testset": "ag8960",
  "multimeter": "fluke45",
  "cell_simulator": "ag8960",
  "oscilloscope": "dpo4104",
}



class DeviceError(object):
  """Represents an error code from device.
  """
  def __init__(self, code, string):
    self._code = code
    self._string = string

  code = property(lambda self: self._code)

  def __repr__(self):
    return "DeviceError(%r, %r)" % (self._code, self._string)

  def __str__(self):
    return "%s (%d)" % (self._string, self._code)

  def __int__(self):
    return self._code


class Identity(object):
  def __init__(self, idstring):
    self.parse(idstring)

  def __str__(self):
    return "Manufacturer: %s\nModel: %s\nSerialno: %s\nRevision: %s\n" % (
        self.manufacturer, self.model, self.serialno, self.revision)

  def parse(self, idstring):
    parts = map(str.strip, idstring.split(",", 3))
    self.manufacturer = parts[0]
    self.model = parts[1]
    self.serialno = parts[2]
    self.revision = parts[3]


class ConditionRegister(object):
  """Generic (abstract base) for condition registers."""
  BITS = {}
  def __init__(self, value):
    self._value = int(value)

  def __repr__(self):
    return "%s(%r)" % (self.__class__.__name__, self._value)

  def __str__(self):
    s = []
    val = self._value
    for bit, desc in self.__class__.BITS.items():
      if val & bit:
        s.append(desc)
    return "<%s: %s>" % (self.__class__.__name__, " | ".join(s))

  def __nonzero__(self):
    return bool(self._value)

  def __int__(self):
    return self._value

  def __and__(self, other):
    return self._value & other

  def IsSet(self, bits):
    return bool(self._value & bits)


def ValueCheck(number):
  """Check for NaN and INF special values.

  Substitute numpy equivalents. These values are the special IEEE-488
  values that signal special numbers.
  """
  try:
    number = float(number)
  except (TypeError, ValueError):
    # TODO(dart) what is better to do here?
    sys.stderr.write("ValueCheck: bad value: %r\n" % (number,))
    return numpy.nan
  if number == 9.91E+37:
    return numpy.nan
  elif number == 9.9E+37:
    return numpy.inf
  elif number == -9.9E+37:
    return -numpy.inf
  else:
    return number


def GetUnit(value, unit=None):
  u = PQ(value, unit)
  u.value = ValueCheck(u.value)
  return u


def ParseFloats(astring):
  """Parse a list of returned floats (in GPIB text format)."""
  return [ValueCheck(v) for v in astring.split(",")]


def ParseIntegers(astring):
  """Parse a list of returned floats (in GPIB text format)."""
  return [int(v) for v in astring.split(",")]


def ParseHex(astring):
  """Parse an SCPI style string of hexadecimal values."""
  if len(astring) > 2:
    return [long(v.strip()[2:], 16) for v in astring.split(",")]
  else:
    return []


def GetBoolean(val):
  """For converting a received boolean value to a Python bool."""
  if isinstance(val, str):
    val = val.upper()
    return (val.startswith("ON") or 
        val.startswith("T") or
        val.startswith("1"))
  else:
    return bool(val)


def GetSCPIBoolean(something):
  """For converting something to an SCPI boolean for transmission."""
  if GetBoolean(something):
    return ON
  else:
    return OFF


def GetInstrument(name, logfile=None):
  realname = GENERICMAP.get(name, name)
  devctx = INSTRUMENTS[realname]
  try:
    cls = module.GetObject(devctx.object)
  except ImportError:
    cls = module.GetObject(INSTRUMENTS["mock"].object)
  dev = cls(devctx, logfile=logfile)
  dev._configname = realname
  return dev

def GetCommandClass(name):
  devctx = INSTRUMENTS[GENERICMAP.get(name, name)]
  return module.GetObject(devctx.get("clicommands", 
                "droid.instruments.gpibCLI.GenericInstrument"))


# Instrument classes defined by VISA. Used for type checking and is-a
# relationships.

class Instrument(object):
  pass

class PowerSupply(Instrument):
  pass

class FunctionGenerator(Instrument):
  pass

class Switch(Instrument):
  pass

class Generator(Instrument):
  pass

class DCPowerSupply(PowerSupply):
  pass

class ACPowerSupply(PowerSupply):
  pass

class Scope(Instrument):
  pass

class Oscilloscope(Instrument):
  pass

class SpectrumAanalyzer(Oscilloscope):
  pass

class Meter(Instrument):
  pass

class VoltMeter(Meter):
  pass

class AmpMeter(Meter):
  pass

class PowerMeter(Meter):
  pass

class MultiMeter(Meter):
  pass

class DigitalMultiMeter(Meter):
  pass

class RFSignalGenerator(Generator):
  pass

class AudioGenerator(Generator):
  pass

class FunctionGenerator(Generator):
  pass



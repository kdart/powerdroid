#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

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

_config = None
_instrumentcache = {}

class NoSuchDevice(Exception):
  pass


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


def _GetConfig():
  global _config
  if _config is None:
    from pycopia import basicconfig
    _config = basicconfig.get_config("/etc/droid/powerdroid.conf")
  return _config


def GetInstrument(name, logfile=None):
  global _instrumentcache
  cf = _GetConfig()
  realname = cf.GENERICMAP.get(name, name)
  try:
    inst =  _instrumentcache[realname]
    if inst.closed:
      del _instrumentcache[realname]
    else:
      return inst
  except KeyError:
    pass
  devctx = cf.INSTRUMENTS[realname]
  try:
    cls = module.GetObject(devctx.object)
  except ImportError:
    raise NoSuchDevice(realname)
  dev = cls(devctx, logfile=logfile)
  dev._configname = realname
  dev.realname = realname
  _instrumentcache[realname] = dev
  return dev


def GetCommandClass(name):
  cf = _GetConfig()
  devctx = cf.INSTRUMENTS[cf.GENERICMAP.get(name, name)]
  return module.GetObject(devctx.get("clicommands", 
                "droid.instruments.gpibCLI.GenericInstrument"))


def ClearInstruments():
  global _instrumentcache
  for inst in _instrumentcache.values():
    try:
      inst.close()
    except AttributeError:
      pass
  _instrumentcache = {}


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



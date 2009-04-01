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


#

"""Alternative wrapper for linux-gpib driver and C library.

"""

import array

from pycopia import aid

import _gpib
GpibError = _gpib.GpibError

from droid.instruments import core


Enum = aid.Enum
Enums = aid.Enums

# Timeout values
TIMEOUTS = Enums( "TNever", "T10us", "T30us", "T100us", "T300us",
  "T1ms", "T3ms", "T10ms", "T30ms", "T100ms", "T300ms",
  "T1s", "T3s", "T10s", "T30s", "T100s", "T300s", "T1000s")

(TNever, T10us, T30us, T100us, T300us,
T1ms, T3ms, T10ms, T30ms, T100ms, T300ms,
T1s, T3s, T10s, T30s, T100s, T300s, T1000s) = TIMEOUTS


# Status (sta) bits.
# http://linux-gpib.sourceforge.net/doc_html/r625.html
DCAS =  Enum(0x1, "DCAS")
DTAS =  Enum(0x2, "DTAS")
LACS =  Enum(0x4, "LACS")
TACS =  Enum(0x8, "TACS")
ATN =   Enum(0x10, "ATN")
CIC =   Enum(0x20, "CIC")
REM =   Enum(0x40, "REM")
LOK =   Enum(0x80, "LOK")
CMPL =  Enum(0x100, "CMPL")
EVENT = Enum(0x200, "EVENT")
SPOLL = Enum(0x400, "SPOLL")
RQS =   Enum(0x800, "RQS")
SRQI =  Enum(0x1000, "SRQI")
END =   Enum(0x2000, "END")
TIMO =  Enum(0x4000, "TIMO")
ERR =   Enum(0x8000, "ERR")


class Status(object):
  def __init__(self):
    self._sta = _gpib.ibsta()

  completed = property(lambda self: self._sta & CMPL)
  ended = property(lambda self: self._sta & END)
  timedout = property(lambda self: self._sta & TIMO)
  errored = property(lambda self: self._sta & ERR)
  servicerequested = property(lambda self: self._sta & RQS)

  def __str__(self):
    bits = []
    sta = self._sta
    for bit in [DCAS, DTAS, LACS, TACS, ATN, CIC, REM, LOK,
                 CMPL, EVENT, SPOLL, RQS, SRQI, END, TIMO, ERR]:
      if sta & bit:
        bits.append(str(bit))
    return "< %s >" % " ".join(bits)


# configs
PAD = 0x1 # Sets GPIB primary address. Same as ibpad()    board or device
SAD = 0x2 #Sets GPIB secondary address. Same as ibsad()  board or device
TMO = 0x3 #Sets timeout for io operations. Same as ibmto().  board or device
EOT = 0x4 #If setting is nonzero, EOI is asserted with last byte on writes. Same as ibeot().   
PPC = 0x5 #Sets parallel poll configuration. Same as ibppc().  board
AUTOPOLL = 0x7 #If setting is nonzero then automatic serial polling is enabled.  board
SC = 0xa #If setting is nonzero, board becomes system controller. Same as ibrsc().  board
SRE = 0xb #If setting is nonzero then board asserts REN line. Otherwise REN is unasserted. Same as ibsre().   board
EOSrd = 0xc #If setting is nonzero then reads are terminated on reception of the end-of-string character. See ibeos(), in particular the REOS bit.  board or device
EOSwrt = 0xd #If setting is nonzero then EOI is asserted whenever the end-of-string character is sent. See ibeos(), in particular the XEOS bit.  board or device
EOScmp = 0xe #If setting is nonzero then all 8 bits are used to match the end-of-string character. Otherwise only the least significant 7 bits are used. See ibeos(), in particular the BIN bit. board or device IbcEOSchar  0xf Sets the end-of-string byte. See ibeos().   board or device
PP2 = 0x10 #If setting is nonzero then the board is put into local parallel poll configure mode, and will not change its parallel poll configuration in response to receiving 'parallel poll enable' command bytes from the controller-in-charge. Otherwise the board is put in remote parallel poll configure mode. Some older hardware does not support local parallel poll configure mode.   board
TIMING = 0x11 #Sets the T1 delay. Use setting of 1 for 2 microseconds, 2 for 500 nanoseconds, or 3 for 350 nanoseconds. These values are declared in the header files as the constants T1_DELAY_2000ns, T1_DELAY_500ns, and T1_DELAY_350ns. A 2 microsecond T1 delay is safest, but will limit maximum transfer speeds to a few hundred kilobytes per second.  board
ReadAdjust = 0x13 #If setting is nonzero then byte pairs are automatically swapped during reads. Presently, this feature is unimplemented.  board or device
WriteAdjust = 0x14 #If setting is nonzero then byte pairs are automatically swapped during writes. Presently, this feature is unimplemented.  board or device
EventQueue = 0x15 #If setting is nonzero then the event queue is enabled. The event queue is disabled by default.  board
SPollBit = 0x16 #If the setting is nonzero then the use of the SPOLL bit in ibsta is enabled.  board
SendLLO = 0x17 #If the setting is nonzero then devices connected to this board are automatically put into local lockout mode when brought online with ibfind() or ibdev().  board
EndBitIsNormal = 0x1a #If setting is nonzero then the END bit of ibsta is set on reception of the end-of-string character or EOI (default).  Otherwise END bit is only set on EOI. board or device
UnAddr = 0x1b #If setting is nonzero then UNT (untalk) and UNL (unlisten) commands are automatically sent after a completed io operation using this descriptor. This option is off by default. device
Ist = 0x20 #Sets the individual status bit, a.k.a. 'ist'. Same as ibist().  board
Rsv = 0x21 #Sets the current status byte this board will use to respond to serial polls. Same as ibrsv().   board
BNA = 0x200 #Changes the GPIB interface board used to access a device.  The setting specifies the board index of the new access board. This configuration option is similar to ibbna() except the new board is specified by its board index instead of a name.   device


class GpibDevice(object):
  """Abstract base class for all GPIB device nodes."""
  _id = None # in case _gpib.find throws exception in constructor.
  TIMEOUTS = TIMEOUTS # make list available to clients without needing to import this module.
  (TNever, T10us, T30us, T100us, T300us,
  T1ms, T3ms, T10ms, T30ms, T100ms, T300ms,
  T1s, T3s, T10s, T30s, T100s, T300s, T1000s) = TIMEOUTS

  def __init__(self, devspec, **kwargs):
    """A device on a GPIB/IEEE-488.1 bus.

    The context must have an attribute "gpibname", matching a name in the
    /etc/gpib.conf file.
    """
    global _gpib_module
    if devspec is not None:
      self._id = _gpib.ibdev(devspec.gpibboard, devspec.gpibpad)
      self._set_timeout(T3s)
      self.Initialize(devspec, **kwargs)
    else:
      self._id = None
    self._gpib_module = _gpib # hold a ref here to make GC at exit cleaner.

  def __del__(self):
    self.close()

  def __str__(self):
    return str(self.identify()).strip()

  def close(self):
    self._gpib_module = None
    if self._id is not None:
      _gpib.close(self._id)
      self._id = None

  def GetConfig(self, option):
    try:
      return _gpib.ibask(self._id, option)
    except GpibError:
      return None

  def SetConfig(self, option, setting):
    _gpib.ibconfig(self._id, option, setting)

  def Clone(self, subinstrument):
    inst = subinstrument(None)
    inst._id = self._id
    inst._timeout = self._timeout
    inst.close = aid.NULL # Don't allow clones/subinstruments to close descriptor.
    return inst

  status = property(lambda self: Status())

  def _get_timeout(self):
    return self._timeout

  def _set_timeout(self,  value):
    if value not in TIMEOUTS:
      raise ValueError, "Bad timeout value: %r" % value
    self._timeout = value
    _gpib.tmo(self._id,  int(value))

  timeout = property(_get_timeout, _set_timeout)
  timeout_values = property(lambda self: TIMEOUTS)

  def write(self, string):
    _gpib.write(self._id,  string)

  def writebin(self, string, length):
    _gpib.writebin(self._id, string, length)

  def read(self, len=4096):
    return _gpib.read(self._id, len)

  def readbin(self, len=4096):
    return _gpib.readbin(self._id, len)

  def Initialize(self, devspec, **kwargs):
    pass


class GpibController(GpibDevice):
  """Represents the controller device. 
  
  Perform bus-wide operations using the controller."""

  listener = property(lambda self: _gpib.ibsta() & LACS)
  talker = property(lambda self: _gpib.ibsta() & TACS)
  attention = property(lambda self: _gpib.ibsta() & ATN)
  incharge = property(lambda self: _gpib.ibsta() & CIC)
  remote = property(lambda self: _gpib.ibsta() & REM)
  lockout = property(lambda self: _gpib.ibsta() & LOK)
  completed = property(lambda self: _gpib.ibsta() & CMPL)
  servicerequest = property(lambda self: _gpib.ibsta() & SRQI)

  def wait(self):
    _gpib.wait(self._id, SRQI)

  def clear(self):
    """Assert IFC on the bus to reset the GPIB bus."""
    _gpib.ifc(self._id)

  def remote_enable(self):
    _gpib.ren(self._id, 1)

  def remote_disable(self):
    _gpib.ren(self._id, 0)

  def SendCommands(self, commands):
    _gpib.cmd(self._id, commands)

  def SetAutopoll(self, val):
    return _gpib.ibconfig(self._id, AUTOPOLL, core.GetBoolean(val))

  def GetAutopoll(self):
    return _gpib.ibask(self._id, AUTOPOLL)

  autopoll = property(GetAutopoll, SetAutopoll)

  def Errors(self):
    pass

  def CheckErrors(self):
    pass

  def ClearErrors(self):
    pass


class GpibInstrument(GpibDevice):

  completed = property(lambda self: _gpib.ibsta() & CMPL)
  end = property(lambda self: _gpib.ibsta() & END)
  timedout = property(lambda self: _gpib.ibsta() & TIMO)
  error = property(lambda self: _gpib.ibsta() & ERR)
  servicerequest = property(lambda self: _gpib.ibsta() & RQS)

  def Prepare(self, measurecontext):
    return 0.05 # default (only bus transer time)

  # basic interface wrapper
  def clear(self):
    """Sends the clear command to the device."""
    _gpib.clear(self._id)

  def wait(self):
    _gpib.wait(self._id, RQS)

  def poll(self):
    """Serial polls the device. The status byte is returned."""
    return ord(_gpib.rsp(self._id))

  def trigger(self):
    """Sends a GET (group execute trigger) command to the device."""
    _gpib.trg(self._id)

  def ask(self, string, length=65536):
    _gpib.write(self._id, string)
    return _gpib.readbin(self._id, length)

  def send(self, string):
    _gpib.wait(self._id, CMPL)
    _gpib.writea(self._id, string)

  def receive(self, length=65536):
    _gpib.wait(self._id, CMPL)
    return _gpib.readbin(self._id, length)

  def read_values(self, length=65536):
    text = _gpib.readbin(self._id, length)
    arr = array.array("d")
    for valstring in text.split(","):
      arr.append(core.ValueCheck(valstring))
    return arr

  def identify(self):
    return core.Identity(self.ask("*IDN?", 1024))

  def Reset(self):
    self.clear()
    self.write("*RST")

  def GetError(self):
    errs = self.ask("SYST:ERR?", 4096)
    code, string = errs.split(",", 1)
    return core.DeviceError(int(code), string.strip()[1:-1])

  def Errors(self):
    """Return a list of all queued errors from the device.

    The side effect is the instrument's error queue is emptied.
    """
    rv = []
    err = self.GetError()
    while err.code != 0:
      rv.append(err)
      err = self.GetError()
    return rv

  def CheckErrors(self):
    errors = self.Errors()
    if errors:
      raise GpibError, errors

  def ClearErrors(self):
    """Read and ignore error queue."""
    self.Errors()

  def Options(self):
    return self.ask("*OPT?").split(",")

  def WaitToComplete(self):
    oto = self.timeout
    self.timeout = T300s
    try:
      val = self.ask("*OPC?")
    finally:
      self.timeout = oto
    return self.Errors()

  def _set_SRE(self, val):
    self.write("*SRE %d" % int(val))

  def _get_SRE(self):
    return int(self.ask("*SRE?"))

  SRE = property(_get_SRE, _set_SRE)

  def _get_STB(self):
    return int(self.ask("*STB?"))

  STB = property(_get_STB)

# command bytes, mostly for reference.
GTL = 0x1 # Go to local
SDC = 0x4 # Selected device clear
PPC = 0x5 # Parallel poll configure
GET = 0x8 # Group execute trigger
TCT = 0x9 # Take control
LLO = 0x11  # Local lockout
DCL = 0x14  # Device clear
PPU = 0x15  # Parallel poll unconfigure
SPE = 0x18  # Serial poll enable
SPD = 0x19  # Serial poll disable

MLA0 = 0x20 # 0x20 to 0x3e  # MLA0 to MLA30 My (primary) listen address 0 to 30
MLA1 = 0x21
MLA2 = 0x22
MLA3 = 0x23
MLA4 = 0x24
MLA5 = 0x25
MLA6 = 0x26
MLA7 = 0x27
MLA8 = 0x28
MLA9 = 0x29
MLA10 = 0x2a
MLA11 = 0x2b
MLA12 = 0x2c
MLA13 = 0x2d
MLA14 = 0x2e
MLA15 = 0x2f
MLA16 = 0x30
MLA17 = 0x31
MLA18 = 0x32
MLA19 = 0x33
MLA20 = 0x34
MLA21 = 0x35
MLA22 = 0x36
MLA23 = 0x37
MLA24 = 0x38
MLA25 = 0x39
MLA26 = 0x3a
MLA27 = 0x3b
MLA28 = 0x3c
MLA29 = 0x3d
MLA30 = 0x3e
UNL = 0x3f  # Unlisten

MTA0 = 0x40 # 0x40 to 0x5e MTA0 to MTA30 My (primary) talk address 0 to 30
MTA1 = 0x41
MTA2 = 0x42
MTA3 = 0x43
MTA4 = 0x44
MTA5 = 0x45
MTA6 = 0x46
MTA7 = 0x47
MTA8 = 0x48
MTA9 = 0x49
MTA10 = 0x4a
MTA11 = 0x4b
MTA12 = 0x4c
MTA13 = 0x4d
MTA14 = 0x4e
MTA15 = 0x4f
MTA16 = 0x50
MTA17 = 0x51
MTA18 = 0x52
MTA19 = 0x53
MTA20 = 0x54
MTA21 = 0x55
MTA22 = 0x56
MTA23 = 0x57
MTA24 = 0x58
MTA25 = 0x59
MTA26 = 0x5a
MTA27 = 0x5b
MTA28 = 0x5c
MTA29 = 0x5d
MTA30 = 0x5e

UNT = 0x5f    # Untalk

MSA0 = 0x60   # MSA0 to MSA15, also PPE When following a talk or listen
MSA1 = 0x61   # address, this is 'my secondary address' 0 to 15. When following a parallel
MSA2 = 0x62   # poll configure, this is 'parallel poll enable'. For parallel poll enable,
MSA3 = 0x63   # the least significant 3 bits of the command byte specify which DIO line
MSA4 = 0x64   # the device should use to send its parallel poll response. The fourth least
MSA5 = 0x65   # significant bit (0x8) indicates the 'sense' or polarity the device should
MSA6 = 0x66   # use when responding.
MSA7 = 0x67
MSA8 = 0x68
MSA9 = 0x69
MSA10 = 0x6a
MSA11 = 0x6b
MSA12 = 0x6c
MSA13 = 0x6d
MSA14 = 0x6e
MSA15 = 0x6f
MSA16 = 0x70  # MSA16 to MSA29, also PPD  When following a talk or listen
MSA17 = 0x71  # address, this is 'my secondary address' 16 to 29. When following a
MSA18 = 0x72  # parallel poll configure, this is 'parallel poll disable'.
MSA19 = 0x73
MSA20 = 0x74
MSA21 = 0x75
MSA22 = 0x76
MSA23 = 0x77
MSA24 = 0x78
MSA25 = 0x79
MSA26 = 0x7a
MSA27 = 0x7b
MSA28 = 0x7c
MSA29 = 0x7d
MSA30 = 0x7e  # My secondary address 30


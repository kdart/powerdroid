#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Modem type instruments.

"""

import sys

from pycopia import tty
from pycopia import aid

from droid.instruments import core


class Error(Exception):
  pass

class CommandError(Error):
  pass

class ExecutionError(Error):
  pass

# call states
SETUP = aid.Enum(0, "SETUP")
ONHOOK = aid.Enum(1, "ONHOOK")
ALERTING = aid.Enum(2, "ALERTING")
PROCEED = aid.Enum(2, "PROCEED")
RINGING = aid.Enum(4, "RINGING")
CONNECTED = aid.Enum(6, "CONNECTED")


class CallerID(object):
  def __init__(self, number, type, valid):
    self.number = number
    self.type = type
    self.valid = valid

  def __str__(self):
    if self.valid == 0:
      return self.number
    elif self.valid == 1:
      return "withheld"
    else:
      return "not available"

  def __nonzero__(self):
    return self.valid == 0 and bool(self.number)


class ModemInstrument(object):

  def __init__(self, devspec, logfile=None, **kwargs):
    self._handlers = {}
    self._context = {}
    self._inq = []
    self._calls = {1: (ONHOOK, 0, 0)}
    self.calltype = None
    self.localhangup = None
    self.calls = 0
    self._timeout = devspec.get("timeout", 30.0) # TODO(dart) not used yet
    self._port = tty.SerialPort(devspec.port, setup=devspec.serial)
    # stock handlers
    self._hanguphook = aid.NULL
    self._answerhook = aid.NULL
    self._callhook = aid.NULL
    self._ringhook = aid.NULL
    self._alerthook = aid.NULL
    self.AddHandler("OK", self._OKHandler)
    self.AddHandler("ERROR", self._ErrorHandler)
    self.AddHandler("NO CARRIER", self._NoCarrierHandler)
    self.AddHandler("RINGING", self._RingingHandler)
    self.Initialize(devspec, **kwargs)

  def __del__(self):
    self.close()

  def close(self):
    if self._port is not None:
      self._port.close()
      self._port = None

  context = property(lambda s: s._context)

  @staticmethod
  def _ErrorHandler(self, value):
    raise CommandError("General ERROR")

  @staticmethod
  def _OKHandler(self, value):
    self._ok = True

  @staticmethod
  def _NoCarrierHandler(self, value):
    self.SetCallState(ONHOOK)
    self._hanguphook(self)

  @staticmethod
  def _RingingHandler(self, value):
    self._ringhook(self)
    if self._context.get("autoanswer"):
      self.Answer()

  def SetHangupHook(self, callback):
    if callable(callback):
      self._hanguphook = callback

  def GetHangupHook(self):
    return self._hanguphook

  def DelHangupHook(self):
    self._hanguphook = aid.NULL

  hanguphook = property(GetHangupHook, SetHangupHook, DelHangupHook)

  def SetAnswerHook(self, callback):
    if callable(callback):
      self._answerhook = callback

  def GetAnswerHook(self):
    return self._answerhook

  def DelAnswerHook(self):
    self._answerhook = aid.NULL

  answerhook = property(GetAnswerHook, SetAnswerHook, DelAnswerHook)

  def SetCallHook(self, callback):
    if callable(callback):
      self._callhook = callback

  def GetCallHook(self):
    return self._callhook

  def DelCallHook(self):
    self._callhook = aid.NULL

  callhook = property(GetCallHook, SetCallHook, DelCallHook)

  def SetRingHook(self, callback):
    if callable(callback):
      self._ringhook = callback

  def GetRingHook(self):
    return self._ringhook

  def DelRingHook(self):
    self._ringhook = aid.NULL

  ringhook = property(GetRingHook, SetRingHook, DelRingHook)

  def SetAlertHook(self, callback):
    if callable(callback):
      self._alerthook = callback

  def GetAlertHook(self):
    return self._alerthook

  def DelAlertHook(self):
    self._alerthook = aid.NULL

  alerthook = property(GetAlertHook, SetAlertHook, DelAlertHook)

  def _GetTimeout(self):
    return self._timeout

  def _SetTimeout(self,  value):
    self._timeout = float(value)

  timeout = property(_GetTimeout, _SetTimeout)

  inqueue = property(lambda self: self._port.get_inqueue())

  def Initialize(self, devspec, **kwargs):
    pass

  def Prepare(self, measurecontext):
    self._context = measurecontext.modems
    return 0.20

  def write(self, string):
    self._port.write(string)

  def read(self, len=4096):
    return self._port.read(len)

  def readline(self):
    return self._port.readline()

  def readq(self):
    return self._port.read(self._port.get_inqueue())

  def handleq(self):
    while self._port.get_inqueue():
      self.read_handler()

  def send(self, string):
    self._port.write(string)
    self._port.write("\r")
    self._waitforok()

  def ask(self, string):
    self._port.write(string)
    self._port.write("\r")
    self._waitforok()
    return self._inq.pop()

  def _waitforok(self):
    self._ok = False
    while not self._ok:
      self.read_handler()

  def AddHandler(self, key, handler):
    self._handlers[key] = handler

  def GetCallState(self, callid=1):
    return self._calls[callid][0]

  def SetCallState(self, state, inbandtones=0, channel=0, callid=1):
    self._calls[callid] = (state, inbandtones, channel)
    if state == CONNECTED:
      self._callhook(self)

  callstate = property(GetCallState, SetCallState)

  def GetCalls(self):
    rv = 0
    for cr in self._calls.values():
      if cf[0] == CONNECTED:
        rv += 1
    return rv

  def Dial(self, number=None):
    number = number or self._context.get("dialednumber")
    if number:
      self.calls += 1
      self.send("ATD%s;" % number)
    else:
      raise ValueError("Invalid number: %r" % number)

  def Answer(self):
    self.localhangup = False
    self.send("ATA")
    self._answerhook(self)

  def Hangup(self):
    self.localhangup = True
    self.send("ATH")
    self._hanguphook(self)

  def _Dispatch(self, line):
    if line.find(":") > 0:
      l, r = line.split(":", 1)
      method = self._handlers.get(l)
      if method is not None:
        method(self, r.strip())
      else:
        self._inq.append(line)
    else:
      method = self._handlers.get(line)
      if method is not None:
        method(self, line)
      else:
        self._inq.append(line)

  # powerdroid Instrument interface compatible methods
  def wait(self):
    pass

  def clear(self):
    pass

  def poll(self):
    return 0

  def trigger(self):
    pass

  def identify(self):
    return core.Identity("Modem,unknown,unknown,unknown")

  def GetError(self):
    return core.DeviceError(0, "Not supported")

  def Errors(self):
    """Return a list of all queued errors from the device.
    """
    rv = []
    err = self.GetError()
    while err._code != 0:
      rv.append(err)
      err = self.GetError()
    return rv

  def ClearErrors(self):
    pass

  def GetConfig(self, option):
    return None

  # pycopia asyncio duck interface
  def fileno(self):
    return self._port._fo.fileno()

  def readable(self):
    return True

  def writable(self):
    return False

  def priority(self):
    return False

  def read_handler(self):
    line = self._port.readline().strip()
    if line:
      self._Dispatch(line)

  def write_handler(self):
    pass

  def pri_handler(self):
    pass

  def hangup_handler(self):
    self.close()

  def error_handler(self, ex, val, tb):
    print >>sys.stderr, "Modem handler error: %s (%s)" % (ex, val)



class GSMModem(ModemInstrument):

  def identify(self):
    manu = self.ask("AT+CGMI").replace(",", " ")
    model = self.ask("AT+CGMM")
    serno = self.ask("AT+CGSN")
    rev = self.ask("AT+CGMR")
    return core.Identity("%s,%s,%s,%s" % (manu, model, serno, rev))


class EnforaModem(GSMModem):
  """Enabler-II G Modem"""

  _CPIMAP = {
    0: SETUP, #setup message
    1: ONHOOK, #disconnect message
    2: ALERTING, #alert message
    3: PROCEED, #call proceed message
    4: None, #synchronization message
    5: None, #progress description message
    6: CONNECTED, #connect
    7: None, #reset request for call reestablishment
    8: None, #reset confirm for call reestablishment
    9: None, #call release
    10: None, #call reject
    11: None, #mobile originated call setup
  }

  def Initialize(self, devspec, **kwargs):
    self._callerid = None
    self.send("ATZ")
    self.send("AT$VGR=24") # maximum mic gain.
    self.send("AT$VGT=12") # maximum speaker gain.
    self.send("AT+CRC=1")
    self.send("AT%CPI=1")
    self.send("AT+CLIP=1")
    self.send("AT+CRLP=61,61,78,6")
    self.AddHandler("%CPI", EnforaModem._CPIHandler)
    self.AddHandler("+CRING", EnforaModem._RingHandler)
    self.AddHandler("%CTV", EnforaModem._CTVHandler)
    self.AddHandler("+CLIP", EnforaModem._CLIPHandler)

  @staticmethod
  def _CPIHandler(self, cpidata):
    callid, msg_type, tones, channel = map(int, cpidata.split(","))
    state = EnforaModem._CPIMAP[msg_type]
    if state is not None:
      self.SetCallState(state, tones, channel, callid)
      if state == ALERTING:
        self._alerthook(self)

  @staticmethod
  def _CLIPHandler(self, data):
    parts = data.split(",")
    self._callerid = CallerID(parts[0][1:-1], int(parts[1]), int(parts[-1]))

  callerid = property(lambda s: s._callerid)

  @staticmethod
  def _RingHandler(self, calltype):
    self.calltype = calltype
    self._ringhook(self)
    if self._context.get("autoanswer"):
      self.Answer()

  def GetLastCallTime(self):
    self.send("AT%CTV")
    return self._lastcalltime

  lastcalltime = property(GetLastCallTime)

  @staticmethod
  def _CTVHandler(self, value):
    self._lastcalltime = int(value)



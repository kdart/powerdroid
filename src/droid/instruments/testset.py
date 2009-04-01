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



"""Integrated test sets, or chassis.

Devices in this class are typically multi-function.
"""


from pycopia import scheduler

from droid.instruments import gpib
from droid.instruments import core

# operating modes
OFF = "OFF"
ON = "CELL" # They call it CELL to activate.

# BCH modes
GSM = "GSM"
GPRS = "GPRS"
EGPRS = "EGPRS"

class IntegrityError(Exception):
  pass


class PingReport(object):
  def __init__(self, target, values):
    self.target = target
    self.transmitted = values[0]
    self.received = values[1]
    self.percentloss = values[2]
    self.minimum = core.PQ(values[3], "ms")
    self.average = core.PQ(values[4], "ms")
    self.maximum = core.PQ(values[5], "ms")

  def __nonzero__(self):
    return self.percentloss == 0.0

  def __str__(self):
    target = self.target or "DUT" # None means DUT target.
    return """--- %s ping statistics ---
%s packets transmitted, %s received, %s%% packet loss
rtt min/avg/max = %s/%s/%s""" % (target, 
      self.transmitted, self.received, self.percentloss,
      self.minimum, self.average, self.maximum)


class Application(object):
  def __init__(self, name, model, rev):
    self.name = name
    self.model = model
    self.revision = rev

  def __str__(self):
    return "%r %s Revision %s" % (self.name, self.model, self.revision)


class TestSet(gpib.GpibInstrument):
  """Generic SCPI test chassis."""

  def Initialize(self, ctx, **kwargs):
    self.timeout = gpib.GpibInstrument.T30s


class Measurer(TestSet):
  def Prepare(self, context):
    pass

  def Perform(self):
    pass

  def Finish(self):
    pass

  def Measure(self, context):
    rpt = None
    self.Prepare(context)
    try:
      rpt = self.Perform()
    finally:
      self.Finish()
    return rpt

  def MeasureN(self, context, N):
    rv = []
    self.Prepare(context)
    try:
      while i in xrange(N):
        res = self.Perform()
        rv.append(res)
    finally:
      self.Finish()
    return rv

  def GetTXPower(self):
    return core.ValueCheck(self.ask("CALL:POW?"))

  def SetTXPower(self, power):
    self.write("CALL:POW %f" % float(power))
    self.CheckErrors()

  txpower = property(GetTXPower, SetTXPower, 
      doc="RF transmitter power in dBm")


class AudioGenerator(TestSet):
  pass


class AudioAnalyzer(TestSet):
  pass


class Ag8960(TestSet):
  """The Agilent 8960 test set chassis."""

  # downlink audio modes
  AUDIO_OFF = "NONE"
  AUDIO_ECHO = "ECHO"
  AUDIO_SILENCE = "SID"
  AUDIO_RANDOM = "PRBS15"
  AUDIO_300 = "SIN300"
  AUDIO_1000 = "SIN1000"
  AUDIO_3000 = "SIN3000"
  AUDIO_MULTI = "MULTITONE"

  # connections types
  CONNECTION_AUTO = "AUTO"
  CONNECTION_A = "A"
  CONNECTION_B = "B"
  CONNECTION_ACKB = "ACKB"
  CONNECTION_BLER = "BLER"
  CONNECTION_SRBL = "SRBL"

  def __str__(self):
    s = [str(self.identify()).strip()]
    s.append("   Application: %s" % self.GetCurrentApplication())
    s.append("Operating mode: %s" % self.GetOperatingMode())
    s.append("Data condition: %s" % self.GetDataCondition())
    s.append("Call condition: %s" % self.GetCallCondition())
    return "\n".join(s)

  def GetApplicationList(self):
    al = self.ask("SYST:APPL:CAT?")
    return [name[1:-1] for name in al.split(",")]

  def GetCurrentApplication(self):
    name, mod, rev = self.ask("SYST:CURR:TA:NAME?;MODEL?;REV?").split(";")
    return Application(name[1:-1], mod[1:-1], rev.strip()[1:-1])

  def SetApplication(self, name):
    if name in self.GetApplicationList():
      self.write("SYSTEM:APPLICATION:SELECT:NAME %r" % name)
      # Note that the test set will not function for the next minute.
    else:
      raise ValueError("Invalid application name: %r." % name)

  def Ping(self, target=None, count=5, size=128, timeout=3):
    if target is None:
      self.write("CALL:DATA:PING:SET:DEV DUT")
    else:
      self.write("CALL:DATA:PING:SET:DEV ALT")
      self.write("CALL:DATA:PING:SET:ALT:IP:ADDR %r" % target)
    self.write("CALL:DATA:PING:SET:COUN %d" % count)
    self.write("CALL:DATA:PING:SET:PACK %d" % size)
    self.write("CALL:DATA:PING:SET:TIM %d" % timeout)
    # perform
    self.write("CALL:DATA:PING:START")
    #errors = self.WaitToComplete()
    scheduler.sleep(count * timeout) # XXX
    errors = self.Errors()
    if errors:
      raise gpib.GpibError, errors
    rawres = self.ask("CALL:DATA:PING?")
    return PingReport(target, core.ParseFloats(rawres))

  def Call(self, orignumber=None):
    if orignumber:
      self.write('CALL:CPN "%s"' % orignumber)
    self.write("CALL:ORIG")
    self.CheckErrors()

  def Hangup(self):
    self.write("CALL:END")
    self.CheckErrors()

  def SetOperatingMode(self, mode):
    assert isinstance(mode, str), "Operating mode must be mode string."
    mode = mode.upper()
    if mode not in (OFF, GSM, GPRS, EGPRS):
      raise ValueError("Improper operating mode string.")
    currentmode = self.GetOperatingMode()
    if mode == currentmode:
      return currentmode # Do nothing if requesting current mode.
    self.write("CALL:CELL:OPER:MODE OFF")
    if mode != OFF:
      self.write("CALL:CELL:BCH:SCEL %s" % (mode,))
      self.write("CALL:CELL:OPER:MODE CELL")
    self.CheckErrors()
    return currentmode

  def GetOperatingMode(self):
    opmode = self.ask("CALL:CELL:OPER:MODE?").strip().upper()
    if opmode == OFF:
      return opmode
    cellmode = self.ask("CALL:CELL:BCH:SCEL?").strip().upper()
    return cellmode

  operatingmode = property(GetOperatingMode, SetOperatingMode)

  def ResetOperatingMode(self):
    """Turn operating mode OFF, then back to whatever it was before.
    """
    mode = self.GetOperatingMode()
    self.SetOperatingMode(OFF)
    self.SetOperatingMode(mode)

  def GetConnectionType(self):
    return self.ask("CALL:FUNC:CONN:TYPE?").strip()

  def SetConnectionType(self, newtype):
    self.write("CALL:FUNC:CONN:TYPE %s" % newtype)
    self.CheckErrors()

  connection_type = property(GetConnectionType, SetConnectionType)

  def GetMultiSlotConfig(self):
    raw = self.ask("CALL:PDTC:MSL:CONF?")

  def GetDataCondition(self):
    return DataConditionRegister(self.ask("STAT:OPER:CALL:COMM:DATA:CONDITION?"))

  datacondition = property(GetDataCondition)

  def GetCallCondition(self):
    return GSMConditionRegister(self.ask("STAT:OPER:CALL:GSM:CONDITION?"))

  callcondition = property(GetCallCondition)

    #"STAT:QUESTIONABLE:CALL:GPRS:CONDITION?"

  def SetDownlinkAudio(self, audiomode):
    """Set downlink audio source.

    None means off, otherwise use AUDIO_* constants.
    """
    if audiomode is None:
      audiomode = "NONE"
    else:
      audiomode = audiomode.upper()
    if audiomode == "OFF": # avert a common error 8-o
      audiomode = "NONE"
    self.write("CALL:TCH:DOWN:SPE %s" % audiomode)
    self.CheckErrors()

  def GetDownlinkAudio(self):
    return self.ask("CALL:TCH:DOWN:SPE?").strip()

  downlinkaudio = property(GetDownlinkAudio, SetDownlinkAudio)

  def GetSpeechEchoDelay(self):
    return core.GetUnit(self.ask("CALL:TCH:DOWN:SPE:LOOP:DEL?"), "s")

  def SetSpeechEchoDelay(self, value):
    self.write("CALL:TCH:DOWN:SPE:LOOP:DEL %.2f" % float(value))

  echo_delay = property(GetSpeechEchoDelay, SetSpeechEchoDelay)

  def GetIPCounters(self):
    raw = self.ask("CALL:COUN:MS:IP:ALL?")
    return IPCountersReport(*core.ParseFloats(raw))

  def IsPDPAttached(self):
    return "PDP" == self.ask("CALL:STAT:DATA?").strip()

  def IsCallActive(self):
    rv = int(self.ask("CALL:CONN?"))
    self.CheckErrors()
    return rv

  def IsAttached(self):
    return core.GetBoolean(self.ask("CALL:ATT?"))

  def GetIMEI(self):
    return self.ask("CALL:MS:REP:IMEI?").strip()

  IMEI = property(GetIMEI)

  def GetIMSI(self):
    return self.ask("CALL:MS:REP:IMSI?").strip()

  IMSI = property(GetIMSI)

  def GetUSFBler(self):
    raw = self.ask("CALL:STAT:PDTCH:USFB:ALL?")
    return USFBlerReport(core.ParseFloats(raw))

  usfbler = property(GetUSFBler)

  def ResetCounters(self):
    self.write("SYST:MEAS:RESET")

  def GetMobileStationInfo(self):
    msi = MobileStationInfo()
    msi.update(self)
    return msi

  MS = property(GetMobileStationInfo)

  def GetOutputState(self):
    return bool(int(self.ask("CALL:CELL:POW:STAT:GSM?")))

  def SetOutputState(self, state):
    self.write("CALL:CELL:POW:STAT:GSM %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  outputstate = property(GetOutputState, SetOutputState, 
      doc="RF output state")

  def GetTXPower(self):
    return core.ValueCheck(self.ask("CALL:POW?"))

  def SetTXPower(self, power):
    self.write("CALL:POW %f" % float(power))
    self.CheckErrors()

  txpower = property(GetTXPower, SetTXPower, 
      doc="RF transmitter power in dBm")

  def DataThroughputMonitor(self):
    pass # TODO(dart)

  def ClearScreen(self):
    self.write("DISP:WIND:ERR:CLE")

  def Prepare(self, measurecontext):
    myctx = measurecontext.testsets
    callplan = measurecontext.callplan
    self.SetProfile(myctx.profile, myctx.txpower)
    self.write("CALL:ORIG:TIM +30")
    self.write("DISP:WIND:ERR:CLE")
    self.SetDownlinkAudio(myctx.downlinkaudio)
    if callplan.include:
      self.write("CALL:CPN:INCL INCL")
      self.write('CALL:CPN "%s"' % callplan.orignumber)
      self.write("CALL:CPN:PLAN %s" % callplan.plan.upper())
      self.write("CALL:CPN:TYPE %s" % callplan.numbertype.upper())
      self.write("CALL:CPN:PRES %s" % callplan.presentation.upper())
      self.write("CALL:CPN:SCR %s" % callplan.screening.upper())
    else:
      self.write("CALL:CPN:INCL EXCL")
    self.CheckErrors()
    return 5.0

  def SetProfile(self, name, txpower=-75.0):
    profilemethod = {
      "GSM": self._PrepareProfile0,
      "GPRS": self._PrepareProfile1,
      "EGPRS": self._PrepareProfile2,
      "EDGE": self._PrepareProfile3,
      "EDGE_PBC": self._PrepareProfile4,
      "EDGEHP": self._PrepareProfileX}.get(name.upper())
    if not profilemethod:
      raise ValueError("Bad profile number for testset")
    self.Reset()
    self.ClearErrors()
    self.write("CALL:CELL:OPER:MODE OFF")
    self.write("DISP:WIND:ERR:CLE")
    self.write("SYST:MEAS:RESET")
    # common settings that differ from reset mode.
    self.write("CALL:POW %s" % txpower) # dBm
    self.write("CALL:LAC +1")
    self.write("CALL:MCC +1")
    self.write("CALL:MNC +1")
    self.write("CALL:BCC +5")
    self.write("CALL:BAND PGSM")
    self.write("CALL:TCH:BAND PGSM")
    self.write("CALL:PDTCH:BAND PGSM")
    self.write("CALL:PDTCH:DTM:BAND PGSM")
    self.write("CALL:BCH:TYPE COMB")
    self.write("CALL:BCH:ARFCN +20")
    self.write("CALL:TCH:ARFCN +30")
    self.write("CALL:PDTCH:ARFCN +30")
    self.write("CALL:PBCCH 0")
    # power control
    self.write("CALL:MS:TXL +25") # not default, but saves power.
    self.write("CALL:PDTCH:PZER:LEV 0")
#    self.write("CALL:PDTCH:PRED:MODE A")
    self.write("CALL:PDTCH:PRED:LEV1 0")
    self.write("CALL:PDTCH:PRED:LEV2 0")
    self.write("CALL:PDTCH:PRED:BURS1 PRL1")
    self.write("CALL:PDTCH:PRED:BURS2 PRL1")
    self.write("CALL:PDTCH:PRED:BURS3 PRL1")
    self.write("CALL:PDTCH:PRED:BURS4 PRL1")
    self.write("CALL:PDTCH:PRED:BURS5 PRL1")
#    self.write("CALL:PDTCH:PRED:UNUS OFF") # PRL1 PRL2
    self.write("CALL:PDTCH:MS:TXL:BURS1 15")
    self.write("CALL:PDTCH:MS:TXL:BURS2 15")
    self.write("CALL:PDTCH:MS:TXL:BURS3 15")
    self.write("CALL:PDTCH:MS:TXL:BURS4 15")
    # timing
    self.write("CALL:MS:TADV +0")
    self.write("CALL:ORIG:TIM 10")
#    self.write("CALL:CELL:TBFLOW:T3192 MS500")
    self.write("CALL:TBFL:UPL:EXT OFF")
    profilemethod()
    self.CheckErrors()
    self.write("CALL:CELL:POW:STAT:GSM 1")
    self.write("CALL:CELL:OPER:MODE CELL")
    return 1.0

  def _PrepareProfile0(self):
    """GSM"""
    # cell id indicates profile to operator
    self.write("CALL:BCH:CID +0")
    self.write("CALL:CELL:BCH:SCEL GSM")
    self.write("CALL:BCH:MS:TXL +0")

  def _PrepareProfile1(self):
    """GPRS"""
    self.write("CALL:BCH:CID +1")
    self.write("CALL:CELL:BCH:SCEL GPRS")

  def _PrepareProfile2(self):
    """EGPRS"""
    self.write("CALL:BCH:CID +2")
    self.write("CALL:CELL:BCH:SCEL EGPRS")

  def _PrepareProfile3(self):
    """EGPRS / EDGE"""
    self.write("CALL:BCH:CID +3")
    self.write("CALL:CELL:BCH:SCEL EGPRS")
    self.write("CALL:PDTC:MSL:FIRS:DOWN:LOOP +1")
    self.write("CALL:PDTC:DTM:MCSC MCS8,MCS8")
    self.write("CALL:PDTC:DTM:MSL:CONF D3U2")
    self.write("CALL:PDTC:MCSC MCS8,MCS8")
    self.write("CALL:PDTC:MCSC:PSCH PS1")
    self.write("CALL:PDTC:MSL:CONF D3U2")

  def _PrepareProfile4(self):
    """EGPRS / EDGE with PBC"""
    self.write("CALL:BCH:CID +4")
    self.write("CALL:CELL:BCH:SCEL EGPRS")
    self.write("CALL:PDTC:MSL:FIRS:DOWN:LOOP +1")
    self.write("CALL:PDTC:DTM:MCSC MCS8,MCS8")
    self.write("CALL:PDTC:DTM:MSL:CONF D3U2")
    self.write("CALL:PDTC:MCSC MCS8,MCS8")
    self.write("CALL:PDTC:MCSC:PSCH PS1")
    self.write("CALL:PDTC:MSL:CONF D3U2")
    self.write("CALL:PBCCH 1")
    self.write("CALL:PBCCH:MS:TXL +0")

  def _PrepareProfileX(self):
    """EGPRS / EDGE with higher power uplink.

    This simulates being distant from a cell, but it just kills battery
    life.
    """
    self.write("CALL:BCH:CID +99")
    self.write("CALL:CELL:BCH:SCEL EGPRS")
    self.write("CALL:MS:TXL +5")
    self.write("CALL:PDTC:DTM:CSW:MS:TXL +5")
    self.write("CALL:PDTC:DTM:MS:TXL:BURS1 +5")
    self.write("CALL:PDTC:DTM:MS:TXL:BURS2 +5")
    self.write("CALL:PDTC:MS:TXL:BURS1 +5")
    self.write("CALL:PDTC:MS:TXL:BURS2 +5")
    self.write("CALL:TCH:TSL +5")
    self.write("CALL:PDTC:MSL:FIRS:DOWN:LOOP +1")
    self.write("CALL:PDTC:DTM:MCSC MCS8,MCS8")
    self.write("CALL:PDTC:DTM:MSL:CONF D3U2")
    self.write("CALL:PDTC:MCSC MCS8,MCS8")
    self.write("CALL:PDTC:MCSC:PSCH PS1")
    self.write("CALL:PDTC:MSL:CONF D3U2")

  def GetAudioGenerator(self):
    return self.Clone(Ag8960AudioGenerator)

  def GetAudioAnalyzer(self):
    return self.Clone(Ag8960AudioAnalyzer)

  def GetMultitoneAudioGenerator(self):
    return self.Clone(Ag8960MultitoneAudioGenerator)

  def GetMultitoneAudioAnalyzer(self):
    return self.Clone(Ag8960MultitoneAudioAnalyzer)

  def GetEGPRSBitErrorMeasurer(self):
    return self.Clone(EGPRSBitErrorMeasurer)


class MobileStationInfo(object):

  def __str__(self):
    s = ["Mobile Info:"]
    for name, value in self.__dict__.items():
      if not name.startswith("_"):
        s.append("%15.15s: %s" % (name, value))
    return "\n".join(s)

  def update(self, testset):
    for name in ("IMEI", "IMSI", "LAC", "MCC"):
      setattr(self, name, testset.ask("CALL:MS:REP:%s?" % name).strip())
    setattr(self, "rxquality", 
        core.ValueCheck(testset.ask("CALL:MS:REP:MEAS:PACCH:RXQ:AVER?")))
    setattr(self, "cvalue", 
        core.ValueCheck(testset.ask("CALL:MS:REP:MEAS:PACCH:CVAL:AVER?")))
    setattr(self, "mclass", 
        core.ValueCheck(testset.ask("CALL:MS:REP:MCL:EGPRS?")))


class IPCountersReport(object):
  def __init__(self, tx_packets, tx_bytes, rx_packets, rx_bytes):
    self.tx_packets = core.PQ(tx_packets, "n")
    self.tx_bytes = core.PQ(tx_bytes, "B")
    self.rx_packets = core.PQ(rx_packets, "n")
    self.rx_bytes = core.PQ(rx_bytes, "B")

  def __repr__(self):
    return "IPCounterReport(%r, %r, %r, %r)" % (
        self.tx_packets, self.tx_bytes, self.rx_packets, self.rx_bytes)

  def __str__(self):
    return ("TX:\n Packets: %.1f\n Bytes: %.1f\n"
        "RX:\n Packets: %.1f\n Bytes: %.1f" % (
        self.tx_packets, self.tx_bytes, self.rx_packets, self.rx_bytes))

  def __sub__(self, other):
    return self.__class__( 
        self.tx_packets - other.tx_packets,
        self.tx_bytes - other.tx_bytes,
        self.rx_packets - other.rx_packets,
        self.rx_bytes - other.rx_bytes)

  def __div__(self, scalar):
    return self.__class__( 
        self.tx_packets / scalar,
        self.tx_bytes / scalar,
        self.rx_packets / scalar,
        self.rx_bytes / scalar)


class USFBlerReport(object):
  def __init__(self, parts):
    self.assigned_bler = parts[0]
    self.assigned_blocks = parts[1]
    self.unassigned_bler = parts[2]
    self.unassigned_blocks = parts[3]

  def __str__(self):
    return ("%s%% USF BLER (assigned) over %s blocks\n"
    "%s%% USF BLER (unassigned) over %s blocks" % (
        self.assigned_bler, self.assigned_blocks,
        self.unassigned_bler, self.unassigned_blocks))



class CommonConditionRegister(core.ConditionRegister):
  BITS = {
    128: "BS Originating",
    8: "Alerting (ringing)",
    4: "Connected",
    2: "Idle",
  }


class DataConditionRegister(core.ConditionRegister):
  BITS = {
    16384: "Ping active",
    2048: "Data Connection Suspended",
    1024: "Data Connection Dormant",
    512: "Data Connection Open",
    256: "PDP Active",
    128: "Starting Data Connection",
    16: "CSD Active",
    8: "Data Transferring",
    4: "Attached",
    2: "Data Idle",
  }


class GSMConditionRegister(core.ConditionRegister):
  BITS = {
    256: "BS Disconnecting",
    128: "BS Originating",
    64: "Call Control Status Changing",
    32: "TCH Assignment in Progress",
    16: "BCH Changing",
    8: "Alerting (ringing)",
    4: "Call Connected/CSD active",
    2: "Idle",
  }

  def IsRinging(self):
    return self.IsSet(8)

  ringing = property(IsRinging)

  def IsConnected(self):
    return self.IsSet(4)

  connected = property(IsConnected)

  def IsIdle(self):
    return self.IsSet(2)


##### BT test set #####

class N4010QuestionableBluetoothLink(core.ConditionRegister):
  BITS = {
    64: "SCO connection with DUT",
    32: "Acting as a signal generator (link 2)",
    16: "Acting as a signal generator (bluetooth)",
    8: "Acting as a slave",
    4: "Loopback test mode with DUT.",
    2: "Transmitter test mode with DUT.",
    1: "ACL connection with DUT",
  }


class N4010QuestionableIntegrity(core.ConditionRegister):
  BITS = {
    128: "Over temperature",
    32: "RF over range",
    16: "ADC over range",
    2: "out of calibration",
  }


class N4010QuestionableFrequency(core.ConditionRegister):
  BITS = {
    2: "Frequency reference is unlocked.",
  }


class N4010QuestionableCalibration(core.ConditionRegister):
  BITS = {
    1: "Self calibration failed.",
  }


class N4010QuestionableSequence(core.ConditionRegister):
  BITS = {
    1: "Test Passed.",
  }

class N4010OperLinkCondition(core.ConditionRegister):
  BITS = {
    1: "Calibrating",
    16: "Measuring",
    32: "Waiting for trigger",
    256: "Paused",
    512: "Running a sequence",
    1024: "(Link summary)",
    2048: "Being configured before test.",
  }

class N4010OperBluetoothLink(core.ConditionRegister):
  BITS = {
    1: "Inquiring",
    2: "Paging",
    4: "Connecting as a slave",
    8: "Disconnecting from the DUT",
    16: "Incoming call alert (headset).",
    32: "Alerting (gateway).",
    64: "Hands free profile.", # not supported yet
  }


class BluetoothDeviceInfo(object):

  def __str__(self):
    s = ["Bluetooth device:"]
    for name in self.__dict__.keys():
      if not name.startswith("_"):
        s.append("%20.20s: %r" % (name, getattr(self, name)))
    return "\n".join(s)


class N4010a(TestSet):
  "The N4010A Wireless Connectivity Test Set."""

  # audio modes
  LOOPBACK = "LOOP" # internal loopback to DUT
  INOUT = "INOUT" # external front panel connectors
  GENERATOR = "GEN" # internal audio generator and analyzer

  # audio codecs that may be set
  CODEC_CVSD = "CVSD"
  CODEC_ALAW = "ALAW"
  CODEC_MULAW = "MULAW"

  # headset roles
  ROLE_HEADSET = "HEAD"
  ROLE_GATEWAY = "AGAT"

  # profiles
  PROFILE_NONE = "NONE"
  PROFILE_HEADSET = "HEAD"

  # link types
  LINKTYPE_ACL = "ACL"
  LINKTYPE_SCO = "SCO"
  LINKTYPE_TEST = "TEST"

  # operating modes
  MODE_LINK = "LINK"
  MODE_RFANALYZER = "RFA"
  MODE_RFGENERATOR = "RFG"

  def __str__(self):
    s = ["N4010 settings:"]
    try:
      s.append(" Transmit power: %s" % self.GetTXPower())
      s.append(" Operating mode: %s" % self.GetOperatingMode())
      s.append("      Link type: %s" % self.GetLinkType())
      s.append("        Profile: %s" % self.GetProfile())
      s.append("           Role: %s" % self.GetRole())
      s.append("     My address: 0x%X" % self.GetBDAddress())
      dutaddr = self.GetDUTAddress() # might be None
      if dutaddr:
        s.append("    DUT address: 0x%X" % dutaddr)
      s.append("    Audio route: %s" % self.GetAudioRoute())
      s.append("            PIN: %s" % self.GetDUTPIN())
      s.append("      Scanning?: %s" % self.GetScanning())
      s.append("  Authenticate?: %s" % self.GetAuthentication())
      s.append("    Encryption?: %s" % self.GetEncryption())
      s.append("    Autoanswer?: %s" % self.GetAutoAnswer())
      s.append("    ActiveCall?: %s" % self.IsCallActive())
    except gpib.GpibError, errors:
      s.append("******")
      s.append("Errors: %s" % (errors,))
    return "\n".join(s)

  def GetOperatingMode(self):
    return self.ask("INST:SEL?").strip()[1:-1] # strip quotes

  def SetOperatingMode(self, mode):
    mode = mode[-1].upper()
    if mode == "K":
      self.write('INST:SEL "LINK"')
    elif mode == "A":
      self.write('INST:SEL "RFA"')
    elif mode == "G":
      self.write('INST:SEL "RFG"')
    else:
      raise ValueError("Valid operating modes: LINK, RFA, RFG")
    self.CheckErrors()

  operatingmode = property(GetOperatingMode, SetOperatingMode)

  def GetBDAddress(self):
    rawaddr = self.ask("LINK:STE:BDAD?")
    return long(rawaddr[2:], 16)

  def SetBDAddress(self, address):
    self.write("LINK:STE:BDAD #H%012X" % long(address))
    self.CheckErrors()

  address = property(GetBDAddress, SetBDAddress, 
      doc="The Bluetooth Device Address for the test set.")

  def GetTXPower(self):
    return core.ValueCheck(self.ask("LINK:TX:POW:LEV?"))

  def SetTXPower(self, power):
    self.write("LINK:TX:POW:LEV %f" % float(power))
    self.CheckErrors()

  txpower = property(GetTXPower, SetTXPower, doc="Transmit power in dBm")

  def GetRXPowerRange(self):
    return core.ValueCheck(self.ask("LINK:RX:POW:RANG?"))

  def SetRXPowerRange(self, power):
    self.write("LINK:RX:POW:RANG %f" % float(power))
    self.CheckErrors()

  rxpower = property(GetRXPowerRange, SetRXPowerRange, 
      doc="Receive power threshold, in dBm.")

  def GetAudioRoute(self):
    return self.ask("LINK:AUD:ROUT?").strip()

  def SetAudioRoute(self, route):
    """Set the audio path.

    Args:
       route (string enum) one of:
         LOOP - Transmits the received audio signal back to the transmitting
            device.
         INOUT - Enables the Test Set's external audio connections
            providing a signal path to external audio equipment.
         GEN - Connects the Test Set's Audio Analyzer to the received
            audio path and the Audio Generator to the transmit audio path.
    """
    route = route[0].upper()
    if route == "L":
      self.write("LINK:AUD:ROUT LOOP")
    elif route in ("I", "O"): # or OUTIN for the memory impaired
      self.write("LINK:AUD:ROUT INOUT")
    elif route == "G":
      self.write("LINK:AUD:ROUT GEN")
    else:
      raise ValueError("Bad audio route value.")
    self.CheckErrors()

  audioroute = property(GetAudioRoute, SetAudioRoute,
      doc="Audio signal path.")

  def GetProfile(self):
    return self.ask("CONF:LINK:PROF?").strip()

  def SetProfile(self, profile):
    profile = profile[0].upper()
    if profile == "N":
      self.write("CONF:LINK:PROF NONE")
    elif profile == "H":
      self.write("CONF:LINK:PROF HEAD")
    else:
      raise ValueError("Bad profile value: %s." % profile)
    self.CheckErrors()

  profile = property(GetProfile, SetProfile,
      doc="select and de-select the headset profile (NONE or HEAD).")

  def GetLinkType(self):
    return self.ask("LINK:TYPE?").strip()

  def SetLinkType(self, linktype):
    linktype = linktype[0].upper()
    if linktype == "A":
      self.write("LINK:TYPE ACL")
    elif linktype == "S":
      self.write("LINK:TYPE SCO")
    elif linktype == "T":
      self.write("LINK:TYPE TEST")
    else:
      raise ValueError("Bad link type value: %s." % linktype)
    self.CheckErrors()

  linktype = property(GetLinkType, SetLinkType)

  def GetRole(self):
    return self.ask("CONF:LINK:PROF:HEAD:ROLE?").strip()

  def SetRole(self, role):
    role = role[0].upper()
    if role == "H":
      self.write("CONF:LINK:PROF:HEAD:ROLE HEAD")
    elif role in ("A", "G"): # or use Gateway
      self.write("CONF:LINK:PROF:HEAD:ROLE AGAT")
    else:
      raise ValueError("Bad role value: %s. Use headset or gateway" % role)
    self.CheckErrors()

  role = property(GetRole, SetRole,
      doc="Set role to ROLE_HEADSET or ROLE_GATEWAY")

  def ActivateRole(self):
    self.write("LINK:PROF:ACT")
    self.ask("*OPC?")
    self.CheckErrors()

  def DeactivateRole(self):
    self.write("LINK:PROF:DEAC")
    self.ask("*OPC?")
    self.CheckErrors()

  def GetMicrophoneGain(self):
    return int(self.ask("CONF:LINK:PROF:HEAD:AGAT:MGA?"))

  def SetMicrophoneGain(self, gain):
    gain = int(gain)
    if gain >= 0 or gain <= 10:
      self.write("CONF:LINK:PROF:HEAD:AGAT:MGA %s" % gain)
      self.CheckErrors()
    else:
      raise ValueError("gain must be [0..10]")

  def GetSpeakerGain(self):
    return int(self.ask("CONF:LINK:PROF:HEAD:AGAT:SGA?"))

  def SetSpeakerGain(self, gain):
    gain = int(gain)
    if gain >= 0 or gain <= 10:
      self.write("CONF:LINK:PROF:HEAD:AGAT:SGA %s" % gain)
      self.CheckErrors()
    else:
      raise ValueError("gain must be [0..10]")

  def GetDUTAddress(self):
    try:
      return long(self.ask("LINK:EUT:BDAD?")[2:-1], 16)
    except ValueError: # might be "----------"
      return None

  def SetDUTAddress(self, address):
    self.write("LINK:EUT:BDAD #H%012X" % long(address))
    self.CheckErrors()

  def DelDUTAddress(self):
    self.write("LINK:EUT:BDAD:CLEAR")
    self.CheckErrors()

  dutaddress = property(GetDUTAddress, SetDUTAddress, DelDUTAddress,
      "DUT bluetooth address.")

  def GetDUTPIN(self):
    return int(self.ask("LINK:EUT:PIN?"))

  def SetDUTPIN(self, pin):
    pin = int(pin)
    if pin > 0 and pin <= 9999:
      return self.write("LINK:EUT:PIN %s" % pin)
    else:
      raise ValueError("Bad range for PIN")

  dutpin = property(GetDUTPIN, SetDUTPIN,
      doc="DUT PIN (integer).")

  def GetDUTStandard(self):
    return self.ask("LINK:EUT:LMPV?").strip()

  dutstandard = property(GetDUTStandard, 
      doc="DUT's Bluetooth standard level")

  def GetScanning(self):
    return bool(int(self.ask("LINK:CONF:SCAN?")))

  def SetScanning(self, flag):
    self.write("LINK:CONF:SCAN %s" % core.GetSCPIBoolean(flag))
    self.CheckErrors()

  scanning = property(GetScanning, SetScanning,
      doc="Allows the N4010A to be discoverable and act as a slave device.")

  def GetAuthentication(self):
    return bool(int(self.ask("LINK:CONN:AUTH:STAT?")))

  def SetAuthentication(self, flag):
    """
      When the authentication is set 'on', the Test Set requests a PIN
      from the DUT. The value returned from the DUT must match that
      specified by the test set's PIN for a successful connection.  If
      authentication is set 'off' the DUT may attempt to pair with the
      Test Set by requesting a PIN. The PIN specified by the test set's
      PIN must match that expected by the DUT for a successful connection.
    """
    self.write("LINK:CONN:AUTH:STAT %s" % core.GetSCPIBoolean(flag))
    self.CheckErrors()

  authentication = property(GetAuthentication, SetAuthentication,
      doc="Authentication mode.")

  def GetEncryption(self):
    return bool(int(self.ask("LINK:CONN:ENCR?")))

  def SetEncryption(self, flag):
    self.write("LINK:CONN:ENCR %s" % core.GetSCPIBoolean(flag))
    self.CheckErrors()

  encryption = property(GetEncryption, SetEncryption,
      doc="Enable or disable the encryption process.")

  def GetAudioCodec(self):
    return self.ask("LINK:AUD:AFOR?").strip()

  def SetAudioCodec(self, value):
    value = value[0].upper()
    if value == "C":
      self.write("LINK:AUD:AFOR CVSD")
    elif value == "A":
      self.write("LINK:AUD:AFOR ALAW")
    elif value == "M":
      self.write("LINK:AUD:AFOR MULAW")
    self.CheckErrors()

  audiocodec = property(GetAudioCodec, SetAudioCodec,
      doc="Type of encoding used for audio signals (CVSD | ALAW | MULAW)")

  def SetupHeadsetProfile(self):
    self.SetOperatingMode("LINK")
    self.SetTXPower(0.0)
    self.SetRXPowerRange(-55.0)
    self.SetLinkType("SCO")
    self.SetProfile("headset")
    self.SetRole("headset")
    self.SetAutoAnswer(True)
    self.SetScanning(True)

  def ActivateHeadsetProfile(self, dutaddress):
    if not self.GetProfile().upper().startswith("HEAD"):
      self.SetupHeadsetProfile()
    self.SetDUTAddress(dutaddress)
    self.ActivateRole()

  def GetAudioGenerator(self):
    return self.Clone(N4010aAudioGenerator)

  def GetAudioAnalyzer(self):
    return self.Clone(N4010aAudioAnalyzer)

  def Discover(self, timeout=None):
    if timeout is not None:
      self.write("LINK:INQ:DUR %f" % float(timeout))
    else:
      timeout = float(self.ask("LINK:INQ:DUR?"))
    ot = self.timeout
    self.timeout = self.T300s
    rv = []
    self.write("LINK:CONT:INQ:IMM")
    scheduler.sleep(timeout + 1.0)
    self.CheckErrors()
    addtext = self.ask("LINK:INQ:BDAD:RESP?").strip()
    if not addtext:
      return rv
    addresses = core.ParseHex(addtext)
    for addr in addresses:
      dev = BluetoothDeviceInfo()
      dev.address = addr
      self.SetDUTAddress(addr)
      self.write("LINK:CONT:EUT:FEAT:IMM")
      self.ask("*OPC?")
      self.CheckErrors()
      scheduler.sleep(1.0)
      dev.features = core.ParseHex(self.ask("LINK:EUT:FEAT?"))
      dev.acl3 = core.GetBoolean(self.ask("LINK:EUT:FEAT:ACL3?"))
      dev.acl5 = core.GetBoolean(self.ask("LINK:EUT:FEAT:ACL5?"))
      dev.pcon = core.GetBoolean(self.ask("LINK:EUT:FEAT:PCON?"))
      dev.sco = core.GetBoolean(self.ask("LINK:EUT:FEAT:SCO?"))
      if dev.sco:
        dev.scohv2 = core.GetBoolean(self.ask("LINK:EUT:FEAT:SCO:HV2?"))
        dev.scohv3 = core.GetBoolean(self.ask("LINK:EUT:FEAT:SCO:HV3?"))
      dev.powerclass = self.ask("LINK:EUT:PCL?").strip()
      dev.pin = self.ask("LINK:EUT:PIN?").strip()
      rv.append(dev)
      dev.version = self.GetDUTStandard()
    self.timeout = ot
    self.CheckErrors()
    return rv

  def Disconnect(self):
    """Disconnect the bluetooth link."""
    self.write("LINK:CONT:DISC:IMM")
    self.CheckErrors()

  def GetAutoAnswer(self):
    return bool(int(self.ask("LINK:PROF:HEAD:HEAD:AANS:STAT?")))

  def SetAutoAnswer(self, flag):
    self.write("LINK:PROF:HEAD:HEAD:AANS:STAT %s" % core.GetSCPIBoolean(flag))

  autoanswer = property(GetAutoAnswer, SetAutoAnswer,
      doc="If set, automatically answer an incoming call.")

  def Answer(self):
    """Answer a call."""
    self.write("LINK:PROF:HEAD:HEAD:ACAL")
    self.CheckErrors()

  def Hangup(self):
    """Hangup an active call."""
    self.write("LINK:PROF:HEAD:HEAD:ENDC")
    self.CheckErrors()

  def IsCallActive(self):
    status = self.GetQuestionableBluetoothLink()
    if status.IsSet(65): # both an ACL and SCO connection active.
      return True
    else:
      return False

  def Prepare(self, measurecontext):
    self.ClearErrors()
    myctx = measurecontext.bttestsets
    if myctx.use:
      self.ActivateHeadsetProfile(myctx.btaddress)
      self.SetAutoAnswer(myctx.autoanswer)
    return 1.0

  # Conditions

  def StatusPreset(self):
    self.write("STAT:PRES")
    self.ask("*OPC?")
    self.CheckErrors()

  def GetQuestionableIntegrity(self):
    return N4010QuestionableIntegrity(self.ask("STAT:QUES:INT:COND?"))

  questionable_integrity = property(GetQuestionableIntegrity)

  def GetQuestionableFrequency(self):
    return N4010QuestionableFrequency(self.ask("STAT:QUES:FREQ:COND?"))

  def GetQuestionableCalibration(self):
    return N4010QuestionableCalibration(self.ask("STAT:QUES:CAL:COND?"))

  def GetQuestionableBluetoothLink(self):
    return N4010QuestionableBluetoothLink(self.ask("STAT:QUES:LINK:BLU:COND?"))

  def GetQuestionableSequence(self):
    return N4010QuestionableSequence(self.ask("STAT:QUES:SEQ:COND?"))

  def GetAllQuestionable(self):
    rv = []
    quest = int(self.ask("STAT:QUES:COND?"))
    if quest & 32:
      rv.append(self.GetQuestionableFrequency())
    if quest & 256:
      rv.append(self.GetQuestionableCalibration())
    if quest & 512:
      rv.append(self.GetQuestionableIntegrity())
    if quest & 1024:
      rv.append(self.GetQuestionableBluetoothLink())
    if quest & 2048:
      rv.append(self.GetQuestionableSequence())
    return rv

  questionable_condition = property(GetAllQuestionable)

  def GetOperBluetoothLink(self):
    return N4010OperBluetoothLink(self.ask("STAT:OPER:LINK:BLU:COND?"))

  def GetAllOperCondition(self):
    rv = []
    oper = int(self.ask("STAT:OPER:COND?"))
    rv.append(N4010OperLinkCondition(oper))
    if oper & 1024:
      rv.append(self.GetOperBluetoothLink())
    return rv

  condition = property(GetAllOperCondition)


class Ag8960AudioGenerator(AudioGenerator):

  COUPLING_AC = "AC"
  COUPLING_DC = "DC"

  def Initialize(self, ctx, **kwargs):
    self.write("SYST:AUD:OUTP:SOUR AFG")
    self.CheckErrors()

  def Prepare(self, measurecontext):
    myctx = measurecontext.audiogenerator
    self.SetFrequency(myctx.frequency)
    self.SetPulsed(myctx.pulsed)
    self.SetVoltage(myctx.voltage)
    self.SetCoupling(myctx.coupling)
    self.SetOutputState(myctx.outputstate)
    return 10.0

  def __str__(self):
    s = ["AG8960 Audio Generator settings:"]
    s.append("Output on?: %s" % self.GetOutputState())
    s.append("   Voltage: %s peak" % self.GetVoltage())
    s.append("  Coupling: %s" % self.GetCoupling())
    s.append(" Frequency: %s" % self.GetFrequency())
    s.append("   Pulsed?: %s" % self.GetPulsed())
    return "\n".join(s)

  def GetCoupling(self):
    return self.ask("AFG:COUP?").strip()

  def SetCoupling(self, coupling):
    coupling = coupling[0].upper()
    if coupling == "A":
      self.write("AFG:COUP AC")
    elif coupling == "D":
      self.write("AFG:COUP DC")
    else:
      raise ValueError("Invalid coupling value")

  coupling = property(GetCoupling, SetCoupling, 
      doc="Coupling (AC or DC) of front panel audio port.")

  def GetFrequency(self):
    return core.GetUnit(self.ask("AFG:FREQ?"), "Hz")

  def SetFrequency(self, freq):
    self.write("AFG:FREQ %s" % freq)
    self.CheckErrors()

  frequency = property(GetFrequency, SetFrequency,
      doc="Audio frequency (1 Hz to 20 kHz, resolution 0.1 Hz)")

  def GetPulsed(self):
    return bool(int(self.ask("AFG:PULS:STAT?")))

  def SetPulsed(self, flag):
    self.write("AFG:PULS:STAT %s" % core.GetSCPIBoolean(flag))
    self.CheckErrors()

  pulsed = property(GetPulsed, SetPulsed,
      doc="Output is pulsed at 10 Hz, with 50% duty cycle (or not).")

  def GetVoltage(self):
    return core.GetUnit(self.ask("AFG:VOLT:AMPL?"), "V")

  def SetVoltage(self, voltage):
    """Set peak voltage. 0 - 9 V pk."""
    self.write("AFG:VOLT:AMPL %s" % voltage)
    self.CheckErrors()

  voltage = property(GetVoltage, SetVoltage, 
      doc="Audio amplitute, in volts peak.")

  def GetPowerLevel(self):
    return None

  def SetPowerLevel(self, level):
    # TODO(dart) convert dBm0 to voltage
    raise NotImplementedError("Specify voltage instead")

  power = property(GetPowerLevel, SetPowerLevel,
      doc="Audio power level in dBm0 (not supported)")

  def GetOutputState(self):
    return bool(int(self.ask("AFG:VOLT:STAT?")))

  def SetOutputState(self, state):
    self.write("AFG:VOLT:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  outputstate = property(GetOutputState, SetOutputState, 
      doc="Audio generator output state")


class Ag8960AudioAnalyzer(AudioAnalyzer):
  """Audio analyzer portion of Agilent 8960."""

  COUNT_CONTINUOUS = 0

  # bandpass filter selections
  FILTER_NONE = "NONE"
  FILTER_BANDPASS = "TBP"
  FILTER_CMESSAGE = "CMES"
  FILTER_BPASS50 = "BPAS50"
  FILTER_BPAS300 = "BPAS300"

  # detector types
  DETECTOR_RMS = "RMS"
  DETECTOR_PEAK = "PEAK"

  def Prepare(self, measurecontext):
    myctx = measurecontext.audioanalyzer
    self.SetMultiState(myctx.multimeasure)
    self.SetMeasureCount(myctx.measurecount)
    self.SetSINADFrequency(myctx.frequency)
    self.SetSINADState(myctx.dosinad)
    self.SetFrequencyState(myctx.dofrequency)
    self.SetExpectedVoltage(myctx.expected_voltage)
    self.SetDetectorType(myctx.detectortype)
    self.SetFilterType(myctx.filtertype)
    self.SetFilterFrequency(myctx.frequency)
    self.SetMeasureContinuous(myctx.continuous)
    return 10.0

  def __str__(self):
    s = ["AG8960 Audio Analyzer settings:"]
    s.append("     Detector type: %s" % self.GetDetectorType())
    s.append("  Expected Voltage: %s peak" % self.GetExpectedVoltage())
    use_filter = self.GetFilterState()
    s.append("        Use filter: %s" % use_filter)
    if use_filter:
      filt_type = self.GetFilterType()
      s.append("       Filter type: %s" % filt_type)
      if filt_type == "TBP":
        s.append("  Filter frequency: %s" % self.GetFilterFrequency())
    s.append(" Measure Frequency: %s" % self.GetFrequencyState())
    measure_sinad = self.GetSINADState()
    s.append("     Measure SINAD: %s" % measure_sinad)
    if measure_sinad:
      s.append("   SINAD frequency: %s" % self.GetSINADFrequency())
    s.append("    Use deemphasis: %s" % self.GetDemphasisState())
    use_expandor = self.GetExpandorState()
    s.append("      Use expandor: %s" % use_expandor)
    if use_expandor:
      s.append("  Expandor voltage: %s" % self.GetExpandorVoltage())
    ms = self.GetMultiState()
    s.append(" Multi-measurement: %s" % ms)
    if ms:
      s.append("     measure-count: %s" % self.GetMeasureCount())
    s.append("   Measure timeout: %s" % self.GetMeasureTimeout())
    return "\n".join(s)

  def GetMeasureCount(self):
    return int(self.ask("SET:AAUDIO:COUNT:NUMB?"))

  def SetMeasureCount(self, count):
    if count:
      self.write("SET:AAUDIO:COUNT:NUMB %s" % count)
      self.SetMultiState(True)
    else:
      self.SetMultiState(False)

  measure_count = property(GetMeasureCount, SetMeasureCount)

  def GetMeasureContinuous(self):
      return bool(int(self.ask("SETUP:AAUDIO:CONTINUOUS?")))

  def SetMeasureContinuous(self, state):
    self.write("SETUP:AAUDIO:CONTINUOUS %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  continuous = property(GetMeasureContinuous, SetMeasureContinuous)

  def GetMultiState(self):
    return bool(int(self.ask("SET:AAUDIO:COUNT:STAT?")))

  def SetMultiState(self, state):
    self.write("SET:AAUDIO:COUNT:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  multi_state = property(GetMultiState, SetMultiState)

  def Perform(self):
    self.write("INIT:AAUDIO")
    return self.CheckIntegrity()

  def GetFilterType(self):
    """Return NONE | TBP | CMES | BPAS50 | BPAS300 """
    return self.ask("SET:AAUDIO:FILT:TYPE?").strip()

  def SetFilterType(self, filttype):
    """Set filter to one of FILTER_*"""
    self.write("SET:AAUDIO:FILT:TYPE %s" % filttype.upper())
    self.CheckErrors()

  def DelFilterType(self):
    self.write("SET:AAUDIO:FILT:TYPE NONE")
    self.CheckErrors()

  filter_type = property(GetFilterType, SetFilterType, DelFilterType)

  def GetFilterState(self):
      return bool(int(self.ask("SET:AAUDIO:FILT:STAT?")))

  def SetFilterState(self, state):
    # will reset to TBP filter type
    self.write("SET:AAUDIO:FILT:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  filter_state = property(GetFilterState)

  def GetFilterFrequency(self):
    return core.GetUnit(self.ask("SET:AAUDIO:FILT:FREQ?"), "Hz")

  def SetFilterFrequency(self, freq):
    self.write("SET:AAUDIO:FILT:FREQ %s" % freq)
    self.CheckErrors()

  def DelFilterFrequency(self):
      self.write("SET:AAUDIO:FILT:TYPE NONE")

  filter_frequency = property(GetFilterFrequency, SetFilterFrequency,
      DelFilterFrequency)

  def GetDemphasisState(self):
    return bool(int(self.ask("SET:AAUDIO:DEMP:STAT?")))

  def SetDemphasisState(self, state):
    self.write("SET:AAUDIO:DEMP:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  deemphasis = property(GetDemphasisState, SetDemphasisState)

  def GetExpandorState(self):
    return bool(int(self.ask("SET:AAUDIO:EXPANDOR:STAT?")))

  def SetExpandorState(self, state):
    self.write("SET:AAUDIO:EXPANDOR:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  expandor_state = property(GetExpandorState, SetExpandorState)

  def GetExpandorVoltage(self):
    return core.GetUnit(self.ask("SET:AAUDIO:EXPANDOR:RLEV?"), "V")

  def SetExpandorVoltage(self, voltage):
    if voltage:
      self.write("SET:AAUDIO:EXPANDOR:RLEV %s" % voltage)
      self.SetExpandorState(True)
    else:
      self.SetExpandorState(False)
    self.CheckErrors()

  expandor_voltage = property(GetExpandorVoltage, SetExpandorVoltage)

  def GetFrequencyState(self):
    return bool(int(self.ask("SET:AAUDIO:FREQ:STAT?")))

  def SetFrequencyState(self, state):
    self.write("SET:AAUDIO:FREQ:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  frequency_state = property(GetFrequencyState, SetFrequencyState)

  def GetSINADState(self):
    return bool(int(self.ask("SET:AAUDIO:SDIS:STAT?")))

  def SetSINADState(self, state):
    self.write("SET:AAUDIO:SDIS:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  sinad_state = property(GetSINADState, SetSINADState)

  def GetSINADFrequency(self):
    return core.GetUnit(self.ask("SET:AAUDIO:SDIS:FREQ?"), "Hz")

  def SetSINADFrequency(self, freq):
    self.write("SET:AAUDIO:SDIS:FREQ %s" % freq)
    self.CheckErrors()

  sinad_frequency = property(GetSINADFrequency, SetSINADFrequency)

  def GetTimeoutState(self):
    return bool(int(self.ask("SET:AAUDIO:TIME:STAT?")))

  def SetTimeoutState(self, state):
    self.write("SET:AAUDIO:TIME:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  def GetMeasureTimeout(self):
    return core.GetUnit(self.ask("SET:AAUDIO:TIMEOUT:TIME?"), "s")

  def SetMeasureTimeout(self, value):
    if value:
      self.write("SET:AAUDIO:TIMEOUT:TIME %s" % value)
    else:
      self.SetTimeoutState(False)
    self.CheckErrors()

  measure_timeout = property(GetMeasureTimeout, SetMeasureTimeout)

  def GetExpectedVoltage(self):
    return core.GetUnit(self.ask("SET:AAUDIO:EXP:VOLT:PEAK?"), "V")

  def SetExpectedVoltage(self, voltage):
    """Set max. expected peak voltage (clipping level). 

    0 mV to 20 V peak
    """
    self.write("SET:AAUDIO:EXP:VOLT:PEAK %s" % voltage)

  voltage_expected = property(GetExpectedVoltage, SetExpectedVoltage)

  def GetDetectorType(self):
    return self.ask("SET:AAUDIO:DET:TYPE?").strip()

  def SetDetectorType(self, detector_type):
    if detector_type.upper() in ("RMS", "PEAK"):
      self.write("SET:AAUDIO:DET:TYPE %s" % detector_type)
    else:
      raise ValueError("Detector type must be RMS or PEAK")

  detector_type = property(GetDetectorType, SetDetectorType)

  # measurements
  def GetFrequency(self):
    if self.GetFrequencyState():
      return core.GetUnit(self.ask("FETC:AAUDIO:FREQ:AVER?"), "Hz")
    else:
      return None

  frequency = property(GetFrequency)

  def GetSINAD(self):
    """Return SINAD in dB."""
    if self.GetSINADState():
      return core.ValueCheck(self.ask("FETC:AAUDIO:SIN:AVER?"))
    else:
      return None

  sinad = property(GetSINAD)

  def GetDistortion(self):
    """Return distortion in percentage."""
    return core.ValueCheck(self.ask("FETC:AAUDIO:DIST:AVER?")) # percentage

  distortion = property(GetDistortion)

  def GetVoltage(self):
    return core.GetUnit(self.ask("FETC:AAUDIO:VOLT:AVER?"), "V") # rms

  voltage = property(GetVoltage)

  def GetIntegrity(self):
    return IntegrityIndicator(self.ask("FETC:AAUDIO:INT?"))

  def CheckIntegrity(self):
    integrity = self.GetIntegrity()
    if integrity:
      return integrity
    else:
      raise IntegrityError, integrity



class IntegrityIndicator(object):
  """http://wireless.agilent.com/rfcomms/refdocs/gsmgprs/prog_gen_integ.php"""

  # Integrity Indicator Number
  _INTEGRITY_VALUES = {
    0: "Normal",
    1: "No Result Available",
    2: "Measurement Timeout",
    3: "Hardware Not Installed",
    4: "Hardware Error",
    5: "Over Range",
    6: "Under Range",
    7: "Burst Short",
    8: "Trigger Early or Fall Early",
    9: "Trigger Late or Rise Late",
    10: "Signal Too Noisy",
    11: "Sync Not Found",
    12: "Oven Out of Range",
    13: "Unidentified Error",
    14: "PCM Full Scale Warning",
    15: "Questionable Result for Phase 1 Mobile",
    16: "Questionable Result",
    17: "Can not Correlate",
    18: "Frequency Out Of Range",
    19: "Uncalibrated Due To Temperature",
    20: "Potential Receiver Saturation",
    21: "Parameter Error",
    22: "Unsupported Configuration",
    23: "Call Processing Operation Failed",
    24: "Calibration Error",
    25: "Burst Not Found",
    26: "Missing Loopback Packets or AT Buffer Overflow",
    27: "No AT Loopback Packets",
    28: "Questionable MS-to-Cell Data",
    30: "Trigger Missed",
    31: "Dual Measurement Request",
    32: "Measurement Not Licensed",
  }

  def __init__(self, value):
    self._value = int(value)

  def __nonzero__(self):
    return self._value == 0

  def __int__(self):
    return self._value

  def __str__(self):
    if self._value == 0:
      return "Normal, result is accurate."
    else:
      reason = IntegrityIndicator._INTEGRITY_VALUES.get(self._value, "UNKNOWN")
      return "Bad measurement: %s(%d)." % (reason, self._value)

  def __repr__(self):
    return "%s(%r)" % (self.__class__.__name__, self._value)



class Ag8960MultitoneAudioAnalyzer(AudioAnalyzer):

  MEASURE_UPLINK = "UPL"
  MEASURE_DOWNLINK = "DOWN"
  MEASURE_ECHO = "ECHO"

  def Prepare(self, ctx):
    myctx = ctx.multitoneanalyzer
    self.SetMeasureMode(myctx.measuremode)
    self.SetExpectedVoltage(myctx.expected_voltage)
    self.SetFrequencyAsGenerator(myctx.usegenerator)
    if not myctx.usegenerator:
      self.SetFrequency(myctx.frequencies)
    self.SetMultiState(myctx.multimeasure)
    self.SetMeasureCount(myctx.measurecount)
    self.SetMeasureContinuous(myctx.continuous)
    if myctx.measuremode.upper().startswith("DOWN"):
      self.write("CALL:TCH:DOWN:SPE MULTITONE")
    else:
      self.write("CALL:TCH:DOWN:SPE NONE")
    return 10.0

  def __str__(self):
    s = ["AG8960 Multitone Audio Analyzer settings:"]
    mmode = self.GetMeasureMode()
    refmode = self.GetReferenceMode()
    s.append("       Measure mode: %s" % mmode)
    s.append("     Reference Mode: %s" % refmode)
    if mmode.startswith("UPL"):
      if refmode.startswith("ABS"):
        s.append("     0 dB ref level: %s %%" % 
            self.GetAbsoluteReferenceLevelUplink())
      else:
        s.append("     Reference Tone: %s" % self.GetReferenceTone())
    elif mmode.startswith("DOW"):
      if refmode.startswith("ABS"):
        s.append("     0 dB ref level: %s" % 
            self.GetAbsoluteReferenceLevelDownlink())
      else:
        s.append("     Reference Tone: %s" % self.GetReferenceTone())
    s.append("   Expected Voltage: %s peak" % self.GetExpectedVoltage())
    ms = self.GetMultiState()
    s.append("  Multi-measurement: %s" % ms)
    if ms:
      s.append("      measure-count: %s" % self.GetMeasureCount())
    s.append("    Measure timeout: %s" % self.GetMeasureTimeout())
    frag = self.GetFrequencyAsGenerator()
    s.append(" Freq as generator?: %s" % frag)
    if not frag:
      s.append("        Frequencies: %s" % ", ".join(map(
          str, self.GetFrequency())))
    s.append("        Continuous?: %s" % self.GetMeasureContinuous())
    return "\n".join(s)

  def SetFrequencyAsGenerator(self, state):
    """Links the frequency and state of each analyzer tone to the
    corresponding value specified for the generator.  
    """
    self.write("SET:MTA:ANAL:FREQ:ALL:GEN %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  def GetFrequencyAsGenerator(self):
    return bool(int(self.ask("SET:MTA:ANAL:FREQ:ALL:GEN?")))

  frequencies_as_generator = property(GetFrequencyAsGenerator, 
      SetFrequencyAsGenerator)

  def SetFrequency(self, value=None):
    """Set analyzer notch frequencies. 

    Must supply a list of 20 frequencies. The special value None will set
    them to the same set as the multitone generator.

    Range: 10 to 4000 Hz
    Resolution: 10 Hz

    A None value in the list disables that slot.
    """
    if type(value) is None:
      self.write("SET:MTA:ANAL:FREQ:ALL:GEN 1")
    elif isinstance(value, (list, tuple)):
      if not len(value) == 20:
        raise ValueError("Must supply value for all 20 tones.")
      # replace None values with -1
      while 1:
        try:
          i = value.index(None)
          value[i] = -1
        except ValueError:
          break
      self.write("SET:MTA:ANAL:FREQ:ALL:GEN 0")
      self.write("SET:MTA:ANAL:FREQ:ALL %s" % ",".join(map(str, value)))
    else:
      raise ValueError(
          "MTA analyzer freq: must supply None, or list of frequencies.")
    self.CheckErrors()

  def GetFrequency(self):
    raw = self.ask("SET:MTA:ANAL:FREQ:ALL?")
    values = core.ParseFloats(raw)
    # replace -1 values with None
    while 1:
      try:
        i = values.index(-1.0)
        values[i] = None
      except ValueError:
        break
    return values

  frequencies = property(GetFrequency, SetFrequency)

  def GetTimeoutState(self):
    return bool(int(self.ask("SET:MTA:TIME:STAT?")))

  def SetTimeoutState(self, state):
    self.write("SET:MTA:TIME:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  def GetMeasureTimeout(self):
    return core.GetUnit(self.ask("SET:MTA:TIMEOUT:TIME?"), "s")

  def SetMeasureTimeout(self, value):
    if value:
      self.write("SET:MTA:TIMEOUT:TIME %s" % value)
    else:
      self.SetTimeoutState(False)
    self.CheckErrors()

  measure_timeout = property(GetMeasureTimeout, SetMeasureTimeout)

  def GetMeasureCount(self):
    return int(self.ask("SET:MTA:COUNT:NUMB?"))

  def SetMeasureCount(self, count):
    if count:
      self.write("SET:MTA:COUNT:NUMB %s" % count)
      self.SetMultiState(True)
    else:
      self.SetMultiState(False)

  measure_count = property(GetMeasureCount, SetMeasureCount)

  def GetMultiState(self):
    return bool(int(self.ask("SET:MTA:COUNT:STAT?")))

  def SetMultiState(self, state):
    self.write("SET:MTA:COUNT:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  multi_state = property(GetMultiState, SetMultiState)

  def GetMeasureContinuous(self):
      return bool(int(self.ask("SET:MTA:CONT?")))

  def SetMeasureContinuous(self, state):
    self.write("SET:MTA:CONT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  continuous = property(GetMeasureContinuous, SetMeasureContinuous)

  def GetUpperLimits(self):
    raw = self.ask("SET:MTA:LEV:ALL:LIM:UPP?")
    return core.ParseFloats(raw)

  def SetUpperLimits(self, value):
    """Set audio tone mask upper limits, in dB.
    Range: 100 to -100 dB
    Resolution: 1 dB
    """
    if isinstance(value, (list, tuple)):
      if not len(value) == 20:
        raise ValueError("Must supply value for all 20 tones.")
      self.write("SET:MTA:LEV:ALL:LIM:UPP %s" % ",".join([str(int(v)) for v in value]))
    else:
      raise ValueError("Must supply a list of limits, in dB.")
    self.CheckErrors()

  limits_upper = property(GetUpperLimits, SetUpperLimits)

  def GetLowerLimits(self):
    raw = self.ask("SET:MTA:LEV:ALL:LIM:LOW?")
    return core.ParseFloats(raw)

  def SetLowerLimits(self, value):
    """Set audio tone mask lower limits, in dB.
    Range: 100 to -100 dB
    Resolution: 1 dB
    """
    if isinstance(value, (list, tuple)):
      if not len(value) == 20:
        raise ValueError("Must supply value for all 20 tones.")
      self.write("SET:MTA:LEV:ALL:LIM:LOW %s" % ",".join([str(int(v)) for v in value]))
    else:
      raise ValueError("Must supply a list of limits, in dB.")
    self.CheckErrors()

  limits_lower = property(GetLowerLimits, SetLowerLimits)

  def GetMeasureMode(self):
    return self.ask("SET:MTA:MEAS:MODE?").strip()

  def SetMeasureMode(self, mode):
    """Set measure mode.

    Values are one of UPLink, DOWNlink, or ECHO.
    """
    self.write("SET:MTA:MEAS:MODE %s" % mode.upper())
    self.CheckErrors()

  measure_mode = property(GetMeasureMode, SetMeasureMode)

  def GetExpectedVoltage(self):
    return core.GetUnit(self.ask("SET:MTA:PEAK:VOLT?"), "V")

  def SetExpectedVoltage(self, voltage):
    """Set max. expected peak voltage (clipping level). 

    Range: 1 mV to 20 V peak
    Resolution: 1 mV
    """
    self.write("SET:MTA:PEAK:VOLT %s" % voltage)

  voltage_expected = property(GetExpectedVoltage, SetExpectedVoltage)

  def GetReferenceMode(self):
    return self.ask("SET:MTA:REF:MODE?").strip()

  def SetReferenceMode(self, value):
    """Set 0dB reference mode to relative or absolute.

    Value is one of ABSolute or RELative.
    """
    self.write("SET:MTA:REF:MODE %s" % value.upper())
    self.CheckErrors()

  reference_mode = property(GetReferenceMode, SetReferenceMode)

  def GetReferenceTone(self):
    return int(self.ask("SET:MTA:REF:REL:TONE?"))

  def SetReferenceTone(self, tone):
    """Set tone index to be used as reference in relative reference mode.
    Range: 1 to 20
    Resolution: 1
    """
    self.write("SET:MTA:REF:REL:TONE %s" % tone)
    self.CheckErrors()

  reference_tone = property(GetReferenceTone, SetReferenceTone)

  def GetSettlingTime(self):
    return core.ValueCheck(self.ask("SET:MTA:SETT?"))

  def SetSettlingTime(self, value):
    self.write("SET:MTA:SETT %s" % value)

  settling_time = property(GetSettlingTime, SetSettlingTime)

  def GetSINADState(self):
    return bool(int(self.ask("SET:MTA:SDIS:STAT?")))

  def SetSINADState(self, state):
    """State of SINAD/Distortion measurement.

    Audio level, SINAD, and distortion results are available when the
    state is ON.
    """
    self.write("SET:MTA:SDIS:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  sinad_state = property(GetSINADState, SetSINADState)

  def GetAbsoluteReferenceLevelDownlink(self):

    return core.GetUnit(self.ask("SET:MTA:REF:ABS:LEV:DOWN?"), "V")

  def SetAbsoluteReferenceLevelDownlink(self, value):
    """Reference level, when making absolute measurements for uplink.

    Value is a voltage.
    Range: 1 mV to 5 V RMS
    Resolution: 0.1 mV

    Note: Agilent manual is wrong, it doesn't say what the device actually
    does.
    """
    if (self.GetReferenceMode().startswith("ABS")
        and self.GetMeasureMode().startswith("DOWN")):
      self.write("SET:MTA:REF:ABS:LEV:DOWN %s" % value)
    else:
      raise ValueError("Reference mode must be ABSolute, and mode must be DOWNlink")

  reference_level_downlink = property(GetAbsoluteReferenceLevelDownlink, 
      SetAbsoluteReferenceLevelDownlink)

  def GetAbsoluteReferenceLevelUplink(self):
    return core.ValueCheck(self.ask("SET:MTA:REF:ABS:LEV:UPL?")) # percentage

  def SetAbsoluteReferenceLevelUplink(self, value):
    """Reference level, when making absolute measurements on downlink.

    Value is a percentage.
    """
    if (self.GetReferenceMode().startswith("ABS")
        and self.GetMeasureMode().startswith("UPL")):
      self.write("SET:MTA:REF:ABS:LEV:UPL %s" % value)
    else:
      raise ValueError("Reference mode must be ABSolute, and mode must be UPLlink")

  reference_level_uplink = property(GetAbsoluteReferenceLevelUplink, 
      SetAbsoluteReferenceLevelUplink)

  # measurements
  def Perform(self):
    self.write("INIT:MTA")
    return self.CheckIntegrity()

  def GetIntegrity(self):
    return IntegrityIndicator(self.ask("FETC:MTA:INT?"))

  def CheckIntegrity(self):
    integrity = self.GetIntegrity()
    if integrity:
      return integrity
    else:
      raise IntegrityError, integrity

  def GetSINAD(self):
    """Returns the average SINAD measurement for audio tone 1.

    The value is in dB units.
    Returns nan if SINAD measurement was not enabled.
    """
    return core.ValueCheck(self.ask("FETC:MTA:SIN:AVER?")) # in dB

  sinad = property(GetSINAD)

  def GetDistortion(self):
    """Return distortion in percentage."""
    return core.ValueCheck(self.ask("FETC:MTA:DIST:AVER?")) # percentage

  distortion = property(GetDistortion)

  def GetVoltage(self):
    """Returns the total average measured audio level.

    Unit is Volts RMS if measurement mode is downlink. 
    Unit is percentage if measurement mode is uplink.
    """
    if self.GetMeasureMode().startswith("DOW"):
      return core.GetUnit(self.ask("FETC:MTA:VOLT:AVER?"), "V") # Vrms
    else:
      return float(self.ask("FETC:MTA:VOLT:AVER?")) # percentage

  voltage = property(GetVoltage)

  def GetFrequency(self):
    """Returns the average frequency measurement result for audio tone 1.
    """
    return core.GetUnit(self.ask("FETC:MTA:FREQ:AVER?"), "Hz")

  frequency = property(GetFrequency)

  def GetLevels(self):
    """Returns the measured average audio levels.

    A list of the measured levels, in dB, is returned for all 20 audio
    channels. A nan value is returned for channels that are disabled.
    """
    return core.ParseFloats(self.ask("FETC:MTA:LEV?"))
# FETC:MTA[:ALL]?

  levels = property(GetLevels)

  def GetLevelDisposition(self):
    """Returns information about whether the multi-tone audio level
    measurement results exceeded the mask limits.

    Returns:
    True: Passed
    False: Failed
    NAN: results can not be determined
    """
    val = core.ValueCheck(self.ask("FETC:MTA:LEV:LIM:FAIL?"))
    if val == 0.0:
      return True
    if val == 1.0:
      return False
    return val

  disposition = property(GetLevelDisposition)


class Ag8960MultitoneAudioGenerator(AudioGenerator):

  PRESET_NONE = "NONE" # generator freqency settings do not match one of the preset states
  PRESET_MTA140 = "MTA140" # sets the first tone to 300 Hz and all others at increments of 140 Hz
  PRESET_MTA100 = "MTA100" # sets the first tone to 300 Hz and all others at increments of 100 Hz
  PRESET_SIN300 = "SIN300" # sets the first tone to 300 Hz and turns all others off
  PRESET_SIN1000 = "SIN1000" # sets the first tone to 1 kHz and turns all others off
  PRESET_SIN3000 = "SIN3000" # sets the first tone to 3 kHz and turns all others off
  PRESET_ALLOFF = "AOFF" # turns all tones off

  def Prepare(self, measurecontext):
    myctx = measurecontext.multitonegenerator
    self.SetFrequency(myctx.preset)
    self.SetUplinkState(myctx.uplinkstate)
    if myctx.uplinkstate:
      self.SetUplinkLevels(myctx.uplinklevels)
    self.SetDownlinkState(myctx.downlinkstate)
    if myctx.downlinkstate:
      self.SetDownlinkLevels(myctx.downlinklevels)
    return 10.0

  def __str__(self):
    s = ["AG8960 Multitone Audio Generator settings:"]
    s.append("          Preset: %s" % self.GetPreset())
    s.append("     Frequencies: %s" % ", ".join(map(str, self.GetFrequency())))
    uls = self.GetUplinkState()
    s.append("      Do uplink?: %s" % uls)
    if uls:
      totup, uplevels = self.GetUplinkLevels()
      s.append("    Uplink total: %s" % totup)
      s.append("   Uplink levels: %s" % ", ".join(map(str, uplevels)))
    dls = self.GetDownlinkState()
    s.append("    Do downlink?: %s" % dls)
    if dls:
      totdown, downlevels = self.GetDownlinkLevels()
      s.append("  Downlink total: %s %%" % totdown)
      s.append(" Downlink levels: %s" % ", ".join(map(str, downlevels)))
    return "\n".join(s)

  def GetPreset(self):
    return self.ask("SET:MTA:GEN:FREQ:PRES?").strip()

  def SetPreset(self, preset_value):
    self.write("SET:MTA:GEN:FREQ:PRES %s" % preset_value)

  def DelPreset(self):
    self.write("SET:MTA:GEN:FREQ:PRES NONE")

  preset = property(GetPreset, SetPreset, DelPreset)

  def SetFrequency(self, value):
    """Set the multitone generator to a preset, or a list of 20 frequencies.

    Range: 10 to 4000 Hz
    Resolution: 10 Hz
    A None value in the list means no frequency for that slot.
    """
    if type(value) is str:
      self.write("SET:MTA:GEN:FREQ:PRES %s" % value)
    elif isinstance(value, (list, tuple)):
      if not len(value) == 20:
        raise ValueError("Must supply value for all 20 tones.")
      # replace None values with -1
      while 1:
        try:
          i = value.index(None)
          value[i] = -1
        except ValueError:
          break
      self.write("SET:MTA:GEN:FREQ:PRES NONE")
      self.write("SET:MTA:GEN:FREQ:ALL %s" % ",".join(map(str, value)))
    else:
      raise ValueError(
          "MTA freq: must supply preset string, or list of frequencies.")
    self.CheckErrors()

  def GetFrequency(self):
    raw = self.ask("SET:MTA:GEN:FREQ:ALL?")
    values = core.ParseFloats(raw)
    # replace -1 values with None
    while 1:
      try:
        i = values.index(-1.0)
        values[i] = None
      except ValueError:
        break
    return values

  frequencies = property(GetFrequency, SetFrequency)

  def GetUplinkState(self):
    return bool(int(self.ask("SET:MTA:GEN:LEV:UPL:ALL:TOT:STAT?")))

  def SetUplinkState(self, state):
    self.write("SET:MTA:GEN:LEV:UPL:ALL:TOT:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  uplink_state = property(GetUplinkState, SetUplinkState)

  def GetDownlinkState(self):
    return bool(int(self.ask("SET:MTA:GEN:LEV:DOWN:ALL:TOT:STAT?")))

  def SetDownlinkState(self, state):
    self.write("SET:MTA:GEN:LEV:DOWN:ALL:TOT:STAT %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  downlink_state = property(GetDownlinkState, SetDownlinkState)

  def SetDownlinkLevels(self, levels):
    """Set relative power levels of tones.

    Range: 0 to 70 %
    Resolution: 0.1%

    If a scalar is given then make that the total, and set all tones
    evenly such that the sum is the given level.

    If a list is given, then it must have 20 elements, each one setting a
    level for the tone. The sum of all levels must be less than 70%.

    """
    if isinstance(levels, (int, float)):
      self.write("SET:MTA:GEN:LEV:DOWN:ALL:TOT %s" % levels)
    elif isinstance(value, (list, tuple)):
      if not len(value) == 20:
        raise ValueError("Must supply value for all 20 tones.")
      # replace None values with -1
      while 1:
        try:
          i = value.index(None)
          value[i] = -1
        except ValueError:
          break
      self.write("SET:MTA:GEN:LEV:DOWN:ALL %s" % ",".join(map(str, value)))
    self.CheckErrors()

  def GetDownlinkLevels(self):
    raw = self.ask("SET:MTA:GEN:LEV:DOWN:ALL?")
    total = core.ValueCheck(self.ask("SET:MTA:GEN:LEV:DOWN:ALL:TOT?")) # percentage
    values = core.ParseFloats(raw)
    # replace -1 values with None
    while 1:
      try:
        i = values.index(-1.0)
        values[i] = None
      except ValueError:
        break
    return total, values

  downlink_levels = property(GetDownlinkLevels, SetDownlinkLevels)

  def SetUplinkLevels(self, levels):
    """Set audio total level, or individual levels.

    Args:
      levels: 
       if (int or float) set total power distributed over all
        frequencies evenly.
       if a sequence it must be length 20 and supply each frequencies
         uplink voltage level.

      Range: 0 to 5 V RMS
      Resolution: 0.1 mV
    """
    if isinstance(levels, (int, float)):
      self.write("SET:MTA:GEN:LEV:UPL:ALL:TOT %s" % levels)
    elif isinstance(value, (list, tuple)):
      if not len(value) == 20:
        raise ValueError("Must supply value for all 20 tones.")
      # replace None values with -1
      while 1:
        try:
          i = value.index(None)
          value[i] = -1
        except ValueError:
          break
      self.write("SET:MTA:GEN:LEV:UPL:ALL %s" % ",".join(map(str, value)))
    self.CheckErrors()

  def GetUplinkLevels(self):
    raw = self.ask("SET:MTA:GEN:LEV:UPL:ALL?")
    total = core.GetUnit(self.ask("SET:MTA:GEN:LEV:UPL:ALL:TOT?"), "V")
    values = core.ParseFloats(raw)
    # replace -1 values with None
    while 1:
      try:
        i = values.index(-1.0)
        values[i] = None
      except ValueError:
        break
    return total, values

  uplink_levels = property(GetUplinkLevels, SetUplinkLevels)


class N4010aAudioGenerator(AudioGenerator):

  def Prepare(self, measurecontext):
    myctx = measurecontext.audiogenerator
    self.write("SEQ:NORM:ACT 2")
    self.SetOutputState(myctx.outputstate)
    self.SetFrequency(myctx.frequency)
    self.SetPowerLevel(myctx.power)
    self.CheckErrors()
    return 5.0

  def __str__(self):
    s = ["N4010a Audio Generator settings:"]
    s.append("Output on?: %s" % self.GetOutputState())
    s.append("     Power: %s dBm0" % self.GetPowerLevel())
    s.append(" Frequency: %s" % self.GetFrequency())
    return "\n".join(s)

  def GetCoupling(self):
    return None

  def SetCoupling(self, coupling):
    return None

  coupling = property(GetCoupling, SetCoupling, 
      doc="Coupling (AC or DC) of front panel audio port.")

  def GetFrequency(self):
    return core.GetUnit(self.ask("LINK:CONF:AUD:FREQ?"), "Hz")

  def SetFrequency(self, freq, unit="Hz"):
    freq = core.GetUnit(freq, unit).inUnitsOf("Hz").value
    if freq % 125.0 == 0.0:
      self.write("LINK:CONF:AUD:FREQ %s" % freq)
      self.CheckErrors()
    else:
      raise ValueError("Frequency must be multiple of 125 Hz.")

  frequency = property(GetFrequency, SetFrequency,
      doc="Audio frequency (125 Hz to 4 kHz, resolution 125 Hz)")

  def GetPulsed(self):
    return False

  def SetPulsed(self, flag):
    pass

  pulsed = property(GetPulsed, SetPulsed,
      doc="Pulsed output is not supported.")

  def GetVoltage(self):
    return None
    # TODO(dart) convert dBm0 to volts RMS.

  def SetVoltage(self, voltage):
    raise NotImplementedError("Specify power instead")

  voltage = property(GetVoltage, SetVoltage, 
      doc="Audio amplitute, in volts rms.")

  def GetPowerLevel(self):
    """Return audio level in dBm0."""
    return core.ValueCheck(self.ask("LINK:CONF:AUD:LEV?"))

  def SetPowerLevel(self, level):
    self.write("LINK:CONF:AUD:LEV %.2f" % float(level))
    self.CheckErrors()

  power = property(GetPowerLevel, SetPowerLevel,
      doc="Audio power level in dBm0 (-70.0 dBm0 to 3 dBm0, resolution 0.01 dBm0)")

  def GetOutputState(self):
    return self.ask("LINK:AUD:ROUT?").startswith("GEN")

  def SetOutputState(self, state):
    if core.GetBoolean(state):
      self.write("LINK:AUD:ROUT GEN")
    else:
      self.write("LINK:AUD:ROUT LOOP")
    self.CheckErrors()

  outputstate = property(GetOutputState, SetOutputState, 
      doc="Audio generator output state, off is looped.")



class N4010aAudioAnalyzer(AudioAnalyzer):

  def Prepare(self, measurecontext):
    self.write("LINK:AUD:ROUT GEN")
    self.write("SEQ:NORM:ACT 2")
    self.CheckErrors()
    return 5.0

  def Perform(self):
    self.write("INIT")
    rv =  bool(int(self.ask("SEQ:DONE? AUD")))
    self.CheckErrors()
    return rv

  def __str__(self):
    s = ["N4010a Audio Analyzer settings:"]
    s.append(" Measure timeout: %s" % self.GetMeasureTimeout())
    s.append("   Measure count: %s" % self.GetMeasureCount())
    return "\n".join(s)

  def GetMeasureTimeout(self):
    return core.ValueCheck(self.ask("LINK:CONF:AUD:TIM?"))

  def SetMeasureTimeout(self, value):
    self.write("LINK:CONF:AUD:TIM %s" % value)

  measure_timeout = property(GetMeasureTimeout,
      SetMeasureTimeout)

  def GetMeasureCount(self):
    return core.ValueCheck(self.ask("LINK:CONF:AUD:AVER?"))

  def SetMeasureCount(self, count):
      self.write("LINK:CONF:AUD:AVER %s" % count)

  measure_count = property(GetMeasureCount, SetMeasureCount)

  # measurements
  def GetDistortion(self):
    return self.ask("FETC:AUD:DIST?") # percentage

  distortion = property(GetDistortion,
      doc="Total harmonic distortion plus noise of the received audio tone.")

  def GetFrequency(self):
    return core.GetUnit(self.ask("FETC:AUD:FREQ?"), "Hz")

  frequency = property(GetFrequency)

  def GetLevel(self):
    return float(self.ask("FETC:AUD:LEV?")) # in dBm0

  level = property(GetLevel)

  def GetSINAD(self):
    return float(self.ask("FETC:AUD:SIN?")) # in dB

  sinad = property(GetSINAD)



class EGPRSBitErrorMeasurer(Measurer):
  """Performs an EGPRS Switched Radio Block (SRB) loopback BER measurement."""

  def __str__(self):
    s = ["EGPRS Bit Error settings:"]
    s.append("        Bit count: %s" % self.GetBitCount())
    s.append("   Transmit power: %s" % self.GetTXPower())
    useto = self.GetMeasureTimeoutState()
    s.append("     Use timeout?: %s" % useto)
    if useto:
      s.append("  Measure timeout: %s" % self.GetMeasureTimeout())
    clds = self.GetCloseLoopDelayState()
    s.append("loop close delay?: %s" % clds)
    if clds:
      s.append("      Start delay: %s" % self.GetCloseLoopDelay())
    auto = self.GetAutoFrameDelayState()
    s.append("  Auto frm delay?: %s" % auto)
    if not auto:
      s.append("     Manual delay: %s" % self.GetManualFrameDelay())
    return "\n".join(s)

  def GetMeasureTimeout(self):
    return core.ValueCheck(self.ask("SET:SBER:TIM:TIME?"))

  def SetMeasureTimeout(self, value):
    self.write("SET:SBER:TIM:TIME %s" % value)

  measure_timeout = property(GetMeasureTimeout,
      SetMeasureTimeout)

  def GetMeasureTimeoutState(self):
    return bool(int(self.ask("SET:SBER:TIM:STAT?")))

  def SetMeasureTimeoutState(self, state):
    self.write("SET:SBER:TIM:STAT %s" % core.GetSCPIBoolean(state))

  measure_timeout_state = property(GetMeasureTimeoutState,
      SetMeasureTimeoutState)

  def Prepare(self, context):
    measctx = context.measure
    # save alterted config
    self._channels = (self.ask("CALL:PDTC:DTM:MSL:CONF?"), 
        self.ask("CALL:PDTC:MSL:CONF?"))
    self._oldpower = core.ValueCheck(self.ask("CALL:POW?"))

    # Manual says this is required
    self.write("CALL:PDTC:MSL:CONF D1U1")
    self.write("CALL:PDTC:DTM:MSL:CONF D1U1")
    self.ClearErrors()

    if measctx.timeout:
      self.write("SET:SBER:TIM:STIME %s" % measctx.timeout)
    else:
      self.write("SET:SBER:TIM:STAT OFF")

    myctx = measctx.srbber
    self.write("CALL:POW %f" % myctx.txpower)
    if myctx.delay:
      self.write("SET:SBER:CLSD:STIME %s" % myctx.delay)
    else:
      self.write("SET:SBER:CLSD:STAT OFF")
    self.write("SET:SBER:COUN %s" % myctx.count)
    if myctx.framedelay >= 0:
      self.write("SET:SBER:LDC:AUTO OFF")
      self.write("SET:SBER:MAN:DEL %s" % myctx.framedelay)
    else:
      self.write("SET:SBER:LDC:AUTO ON")
    self.StartData()
    self.CheckErrors()

  def StartData(self):
    self.write("CALL:FUNC:CONN:TYPE SRBL")
    while not int(self.ask("CALL:TRAN:STAT?")):
      self.write("CALL:FUNC:DATA:START")
      self.ask("CALL:FUNC:DATA:STAR:OPC?")
      self.CheckErrors()

  def Perform(self):
    ot = self.timeout
    self.timeout = self.T100s
    try:
      self.write("INIT:SBER")
      raw = self.ask("FETCH:SBER?")
    finally:
      self.timeout = ot
    self.CheckErrors()
    integrity, bits_tested, error_ratio, error_count = raw.split(",")
    integrity = IntegrityIndicator(integrity)
    if integrity:
      return BitErrorReport(bits_tested, error_ratio, error_count)
    else:
      raise IntegrityError, integrity

  def Finish(self):
#    self.write("CALL:CELL:OPER:MODE OFF")
    self.write("CALL:FUNC:DATA:STOP")
    self.write("CALL:FUNC:CONN:TYPE AUTO")
    self.write("CALL:PDTC:DTM:MSL:CONF %s; CALL:PDTC:MSL:CONF %s" % self._channels)
#    self.write("CALL:PDTC:DTM:MSL:CONF %s" % self._channels[0])
#    self.write("CALL:PDTC:MSL:CONF %s" % self._channels[1])
    self.write("CALL:POW %f" % self._oldpower)
#    self.write("CALL:CELL:OPER:MODE CELL")
    self.CheckErrors()

  def GetBitCount(self):
    return core.ValueCheck(self.ask("SET:SBER:COUN?"))

  def SetBitCount(self, value):
    self.write("SET:SBER:COUN %s" % value)
    self.CheckErrors()

  bitcount = property(GetBitCount, SetBitCount)

  def GetAutoFrameDelayState(self):
      return bool(int(self.ask("SET:SBER:LDC:AUTO?")))

  def SetAutoFrameDelayState(self, state):
    self.write("SET:SBER:LDC:AUTO %s" % core.GetSCPIBoolean(state))
    self.CheckErrors()

  autoframedelay_state = property(GetAutoFrameDelayState,
      SetAutoFrameDelayState)

  def GetManualFrameDelay(self):
    return int(self.ask("SET:SBER:MAN:DEL?"))

  def SetManualFrameDelay(self, value):
    self.write("SET:SBER:MAN:DEL %d" % value)
    self.CheckErrors()

  burstdelay_manual = property(GetManualFrameDelay, SetManualFrameDelay)

  def GetCloseLoopDelay(self):
    return core.ValueCheck(self.ask("SET:SBER:CLSD:TIME?"))

  def SetCloseLoopDelay(self, value):
    self.write("SET:SBER:CLSD:TIME %s" % value)

  closeloopdelay = property(GetCloseLoopDelay, SetCloseLoopDelay)

  def GetCloseLoopDelayState(self):
    return bool(int(self.ask("SET:SBER:CLSD:STAT?")))

  def SetCloseLoopDelayState(self, state):
    self.write("SET:SBER:CLSD:STAT %s" % core.GetSCPIBoolean(state))

  closeloopdelay_state = property(GetCloseLoopDelayState,
      SetCloseLoopDelayState)

  # measured values
  def GetBurstDelay(self):
    return core.ValueCheck(self.ask("FETC:SBER:DEL?"))

  burstdelay_actual = property(GetBurstDelay)

  def GetRatio(self):
    return core.ValueCheck(self.ask("FETC:SBER:RAT?"))

  BER = property(GetRatio)

  def GetErrorBits(self):
    return core.ValueCheck(self.ask("FETC:SBER:COUN?"))

  errored_bits = property(GetErrorBits)

  def GetTestedBits(self):
    return core.ValueCheck(self.ask("FETC:SBER:BITS?"))

  tested_bits = property(GetTestedBits)



class BitErrorReport(object):
  def __init__(self, bits_tested, error_ratio, error_count):
    self.bits_tested = core.ValueCheck(bits_tested)
    self.error_ratio = core.ValueCheck(error_ratio)
    self.error_count = core.ValueCheck(error_count)

  def __str__(self):
    return "BER %s%% (%s bit errors over %s bits)" % (
        self.error_ratio, self.error_count, self.bits_tested)




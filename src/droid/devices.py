#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
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



"""Device models and controllers.
"""

import re
import sys

from pycopia import aid
from pycopia import dictlib
from pycopia import textutils
from pycopia import timelib
from pycopia import scheduler
from pycopia import proctools
from pycopia.OS.Linux import event

from droid import adb
from droid import errors
from droid import constants


OFF = constants.OFF
ON = constants.ON
UNKNOWN = constants.UNKNOWN

ALT = event.ALT
META = event.META
COMPOSE = event.COMPOSE
SHIFT = event.SHIFT

class BuildID(object):
  """Holder for Android build information."""
  def __init__(self, builddict):
    self.product = builddict["ro.product.device"]
    self.type = builddict["ro.build.type"]
    self.id = builddict["ro.build.version.incremental"]
    self.branch = builddict["ro.build.id"]

  def __str__(self):
    return """
   Product: %s
      Type: %s
  Build id: %s
    Branch: %s""" % (self.product, self.type, self.id, self.branch)

  def __getitem__(self, key):
    return self.__dict__[key]


class APNInfo(object):
  """Holder for APN information.

  Args:
    name
    mcc
    mnc
    accesspointname
    user
    password
    server
    proxy
    port
    mmsc
    iscurrent
  """
  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)


class TimeInfoReport(object):
  def __init__(self, realtime, uptime, awake, asleep):
    self.realtime = float(realtime) / 1000.0
    self.uptime = float(uptime) / 1000.0
    self.asleeptime = self.realtime - self.uptime
    self.awake = int(awake) # percentage
    self.asleep = int(asleep) # percentage

  def __str__(self):
    return """Uptime: %s\n Awake: %s (%s %%)\nAsleep: %s (%s %%)""" % (
        FormatTime(self.realtime), 
        FormatTime(self.uptime), self.awake, 
        FormatTime(self.asleeptime), self.asleep)

#  def __sub__(self, other):
#    return self.__class__(realadj, uptimeadj, awake, asleep)


def FormatTime(seconds):
  minutes, seconds = divmod(seconds, 60.0)
  hours, minutes = divmod(minutes, 60.0)
  return "%02.0f:%02.0f:%02.2f" % (hours, minutes, seconds)



class EventScript(object):
  """Manages recorded system events.

  This is also an iterable object, to iterate over stored events.

  Args:
    filename (string, optional): If given, immediatly read the file with
    that name to populate the event list.
  """
  def __init__(self, sourcename="unknown", filename=None):
    self._events = []
    self.sourcename = sourcename
    if filename is not None:
      self.ReadFile(filename)

  def __str__(self):
    return "\n".join(["%s %s %s %s" % t for t in self._events])

  def ReadFile(self, fname):
    """Read events from a file.

    Args:
      fname (string): The name of a file to read from.
    """
    text = open(fname).read()
    self.Parse(text)

  def WriteFile(self, fname):
    """Write the contained events to a file.

    Args:
      fname (string): The name of the file to write to.
    """
    fo = open(fname, "w")
    fo.write("# %s\n" % self.sourcename)
    try:
      for delta_t, evtype, evcode, evvalue in self._events:
        fo.write("%s %s %s %s\n" % (delta_t, evtype, evcode, evvalue))
    finally:
      fo.close()

  def Append(self, delta_t, evtype, evcode, evvalue):
    """Append a new event to the event list.

    Args:
      delta_t (float): The difference in time between this event and the
      last one.
      evtype (int): The type of the event, as defined in events.h.
      evcode (int): The code corresponding to the type, as defined in events.h.
      evvalue (int): The value of the event.
    """
    if evtype in (1, 2, 3): # keyboard; relative motion, abs. motion events
      self._events.append((delta_t, evtype, evcode, evvalue))
      return None # handled
    return False

  def Parse(self, text):
    """Parse a chunk of text containing lines of event codes."""
    evlist = self._events
    for line in text.splitlines():
      try:
        delta_t, evtype, evcode, evvalue = self._Parseline(line)
      except ValueError: # unpack error, probably comment
        pass
      else:
        evlist.append((delta_t, evtype, evcode, evvalue))

  def _Parseline(self, line):
    (tstext, evtype, evcode, evvalue) = line.split()
    return float(tstext), int(evtype), int(evcode), int(evvalue)

  def Perform(self, device):
    """Send the stored events to the DUT

    Args:
      device (instance of EventDevice): the device client
      object to use to send stored events.
    """
    for delta_t, evtype, evcode, evvalue in self._events:
      if delta_t > 0.1:
        scheduler.sleep(delta_t)
      device.SendEvent(evtype, evcode, evvalue)

  def __iter__(self):
    return iter(self._events)



class EventDevice(object):
  """Represents an event device node on a DUT."""
  def __init__(self, adb, devid):
    self._adb = adb
    self._devid = devid

  def write(self, evtype, code, value):
    self._adb.ShellCommand("sendevent /dev/input/event%d %s %s %s" % (
          self._devid, evtype, code, value))



class EventGeneratorMixin(object):

  def SendEvent(self, evtype, code, value):
    self._adb.ShellCommand("sendevent %s %s %s %s" % (
        self._devnode, evtype, code, value))

  def GetEvent(self):
    """Get a single kernel event from the device."""
    cmd = "shell:getevent -c 1 %s" % self._devnode
    sock = self._adb.Connect(cmd)
    try:
      data = sock.recv(20)
    finally:
      sock.close()
    return self._ParseEvent(data)

  def GetEvents(self, handler, count=0):
    """Get a number of events from the device. 

    Args:
      handler (callable): Gets the parameters (delta_t, type, code, value)
          for each event read from DUT.
      count (int): number of events to capture. Zero means run until
      interrupted (caller will get a KeyboardInterrupt exception). 
    """
    s = ["shell:getevent", self._devnode]
    if count:
      s.insert(1, "-t %d" % (count,))
    cmd = " ".join(s)
    sock = self._adb.Connect(cmd)
    last_timestamp = timelib.now()
    data = sock.recv(20)
    try:
      while data:
        try:
          timestamp, evtype, evcode, evvalue = self._ParseEvent(data)
        except ValueError:
          print >>sys.stdout, "GetEvents: Error parsing event data:", repr(data)
        else:
          if handler(timestamp - last_timestamp, evtype, evcode, evvalue) is None:
            last_timestamp = timestamp
        data = sock.recv(20)
    finally:
      sock.close()

  def RunEventScript(self, script):
    """Perform an event script using this event writer.

    Args:
      script: an instance of EventScript.
    """
    script.Perform(self)

  @staticmethod
  def _ParseEvent(line):
    (evtype, evcode, evvalue) = line.split()
    return timelib.now(), int(evtype, 16), int(evcode, 16), int(evvalue, 16)


class AndroidKeyGenerator(event.KeyEventGenerator, EventGeneratorMixin):
  def __init__(self, controller, keymap, eventdevice):
    keydevice = EventDevice(controller, eventdevice)
    super(AndroidKeyGenerator, self).__init__(keydevice, keymap=keymap)
    self._adb = controller
    self._devnode = "/dev/input/event%d" % eventdevice

  def KeyPress(self, code):
    self._adb.ShellCommand("sendevent %s 1 %s 1" % (self._devnode, code))

  def KeyRelease(self, code):
    self._adb.ShellCommand("sendevent %s 1 %s 0" % (self._devnode, code))


class AndroidTSGenerator(event.AbsoluteMotionGenerator, EventGeneratorMixin):
  def __init__(self, controller, eventdevice):
    touchdevice = EventDevice(controller, eventdevice)
    super(AndroidTSGenerator, self).__init__(touchdevice)
    self._adb = controller
    self._devnode = "/dev/input/event%d" % eventdevice


class AndroidNavGenerator(event.RelativeMotionGenerator, EventGeneratorMixin):
  def __init__(self, controller, eventdevice):
    nav = EventDevice(controller, eventdevice)
    super(AndroidNavGenerator, self).__init__(nav)
    self._adb = controller
    self._devnode = "/dev/input/event%d" % eventdevice


def _GetStateValue(value):
  """Allow for "loose" state setting."""
  if isinstance(value, aid.Enum):
    if value in (ON, OFF, UNKNOWN):
      return value
    else:
      raise ValueError("Invalid state Enum: %r" % (value,))
  elif isinstance(value, str):
    value = value.lower()
    if value in ("yes", "on", "true"):
      return ON
    elif value in ("no", "off", "false"):
      return OFF
    else:
      return UNKNOWN
  else:
    if value: # Python boolean check
      return ON
    else:
      return OFF


class DeviceStates(dictlib.AttrDict):
  """Generic holder of device states and values. 

  Same as AttrDict, but provides a more appropriate string representation,
  and state-setting helper methods.
  """
  def __str__(self):
    s = ["  States:"]
    for name, value in self.items():
      s.append("%11.11s: %s" % (name, value))
    return "\n".join(s)

  def GetStateStrings(self):
    return ["%s%s" % t for t in self.iteritems()]

  def SetState(self, statename, value, setter=None, resetter=None):
    value = _GetStateValue(value)
    current = dict.__getitem__(self, statename)
    if current != value:
      if setter is not None:
        if setter(value):
          dict.__setitem__(self, statename, value)
      else:
        dict.__setitem__(self, statename, value)

  def GetState(self, statename):
    return dict.__getitem__(self, statename)


class Device(object):
  """Base class for all device type objects."""
  pass


class BatteryInfo(object):
  AC_ONLINE_PATH = "/sys/class/power_supply/ac/online"
  USB_ONLINE_PATH = "/sys/class/power_supply/usb/online"
  BATTERY_STATUS_PATH = "/sys/class/power_supply/battery/status"
  BATTERY_HEALTH_PATH = "/sys/class/power_supply/battery/health"
  BATTERY_PRESENT_PATH = "/sys/class/power_supply/battery/present"
  BATTERY_CAPACITY_PATH = "/sys/class/power_supply/battery/capacity"
  BATTERY_VOLTAGE_PATH = "/sys/class/power_supply/battery/batt_vol"
  BATTERY_TEMP_PATH = "/sys/class/power_supply/battery/batt_temp"
  BATTERY_TECH_PATH = "/sys/class/power_supply/battery/technology"
  BATTERY_CHRG_ENA_PATH = "/sys/class/power_supply/battery/charging_enabled"

  def __init__(self, controller):
    self.Update(controller)

  def Update(self, controller):
    cmd = "cat %s" % (" ".join(
        [self.AC_ONLINE_PATH,
        self.USB_ONLINE_PATH,
        self.BATTERY_STATUS_PATH,
        self.BATTERY_HEALTH_PATH,
        self.BATTERY_PRESENT_PATH,
        self.BATTERY_CAPACITY_PATH, 
        self.BATTERY_VOLTAGE_PATH, 
        self.BATTERY_TEMP_PATH, 
        self.BATTERY_TECH_PATH, 
        self.BATTERY_CHRG_ENA_PATH, 
        ]
    ))
    lines = controller.ShellCommandOutput(cmd).splitlines()
    self.ac_online = bool(int(lines[0]))
    self.usb_online = bool(int(lines[1]))
    self.status = lines[2]
    self.health = lines[3]
    self.present = bool(int(lines[4]))
    self.capacity = int(lines[5])
    self.voltage = float(lines[6]) / 1000.0
    self.temperature = float(lines[7]) / 10.0
    self.technology = lines[8]
    self.charging_enabled = bool(int(lines[9]))

  def __str__(self):
    s = ["Battery state:",
        "   AC powered: %s" % self.ac_online,
        "  USB powered: %s" % self.usb_online,
        "   technology: %s" % self.technology,
        "       status: %s" % self.status,
        "       health: %s" % self.health,
        "      present: %s" % self.present,
        "     capacity: %s" % self.capacity,
        "      voltage: %.3f V" % self.voltage,
        "  temperature: %.2f C" % self.temperature,
        "     charging: %s" % self.charging_enabled,
        ]
    return "\n".join(s)


class LEDInfo(object):
  LCD_BRIGHTNESS = "/sys/class/leds/lcd-backlight/brightness"
  KEYBOARD_BRIGHTNESS = "/sys/class/leds/keyboard-backlight/brightness"
  BUTTONS_BRIGHTNESS = "/sys/class/leds/button-backlight/brightness"

  def __init__(self, controller):
    self.Update(controller)

  def Update(self, controller):
    cmd = "cat %s" % (" ".join(
        [self.LCD_BRIGHTNESS,
        self.KEYBOARD_BRIGHTNESS,
        self.BUTTONS_BRIGHTNESS,
        ]
        ))
    lines = controller.ShellCommandOutput(cmd).split("\n\0") # these have nulls
    self.lcd_brightness = int(lines[0])
    self.keyboard_brightness = int(lines[1])
    self.buttons_brightness = int(lines[2])

  def __str__(self):
    s = ["LED state:",
        "        LCD brightness: %s" % self.lcd_brightness,
        "   Keyboard brightness: %s" % self.keyboard_brightness,
        "    Buttons brightness: %s" % self.buttons_brightness,
        ]
    return "\n".join(s)


class MobileDevice(Device):
  """General mobile device.

  Devices also keep track of the devices state.
  """

  _INPUTMAP = {}

  def __init__(self, devid, serialno=None, logfile=None):
    super(MobileDevice, self).__init__()
    self._devid = devid
    self._controller = None
    self._keygenerator = None
    self.serialno = serialno
    self._build = None
    self._btaddress = None
    self.account = None # Gmail/XMPP account name.
    self.password = None
    self.hostname = None
    self.logfile = logfile
    # Set some initial states.
    self._states = DeviceStates({
      "usb":  ON,
      "power":  UNKNOWN,
      "radio":  ON,
      "wifi":  UNKNOWN,
      "bluetooth":  UNKNOWN,
      "airplane":  OFF,
      "call":  UNKNOWN,
      "audio":  UNKNOWN,
      "sync":  UNKNOWN,
      "xmpp":  UNKNOWN, # Persistent XMPP connection setting.
      "updates":  OFF, # account actively being updated with mail?
      "lid":  ON, # default to closed... TODO(dart) verify somehow.
    })
    self.IsUSBActive() # set power state if we can.
    self._cpueater_pid = None

  indexnumber = property(lambda s: s._devid) # read-only index number.
  states = property(lambda self: self._states)
  statestrings = property(lambda self: self._states.GetStateStrings())

  def __str__(self):
    s = [
      "%s:" % self.__class__.__name__,
      "     Build: %s" % self._build,
      "  Serialno: %s" % self.serialno,
      "   account: %s" % self.account,
      str(self._states),
    ]
    return "\n".join(s)

  def ToggleState(self, name):
    if self._states[name] == ON:
      self._states[name] = OFF
    else:
      self._states[name] = ON

  def StateON(self, name):
    self._states[name] = ON

  def StateOFF(self, name):
    self._states[name] = OFF

  def AddState(self, name, initial=ON):
    self._states[name] = initial

  def IsStateON(self, name):
    return self._states[name] == ON

  def IsStateOFF(self, name):
    return self._states[name] == OFF

  def UpdateAPN(self, apninfo):
    pass

  def IsUSBActive(self):
    pass

  def GetBuild(self):
    """Retrieve the build information from the DUT.

    Returns:
      BuildID object, populated with the build information.
    """
    if self._build is None:
      if self._controller is None:
        return None
      try:
        if self._controller.GetState() == adb.DEVICE:
            self._build = BuildID(self._controller.GetBuild())
      except adb.AdbError:
        self._controller = None
        return None
    return self._build

  def SetBuild(self, builddict):
    self._build = BuildID(builddict)

  def DelBuild(self):
    self._build = None

  build = property(GetBuild, SetBuild, DelBuild, 
      "The DUT build information.")

  def ConnectUSB(self):
    """Tell us that the USB cable was just connected."""
    self._states.usb = ON

  def DisconnectUSB(self):
    """Tell us that the USB cable was just disconnected."""
    self._states.usb = OFF
    self._controller = None
    self._keygenerator = None

  def IsUSBConnected(self):
    """Indicate what programmed USB connect state is."""
    return self._states.usb == ON

  def PowerOff(self):
    """Tell us that power is off."""
    self._states.power = OFF

  def PowerOn(self):
    """Tell us that power is on."""
    self._states.power = ON
    self._states.radio = ON
    self._states.call = OFF

  def IsPoweredOn(self):
    return self._states.power == ON

  def RadioOn(self, use_ui=False):
    """Tell us to turn the radio on, and update the state."""
    if self._states.radio != ON:
      if use_ui:
        self.PressKey(107, hold=2.0) # END key
        self.DownKey()
        self.DownKey()
        self.CenterKey()
      else:
        self._controller.ShellCommand("start ril-daemon")
      self._states.radio = ON

  def RadioOff(self, use_ui=False):
    """Tell us to turn the radio off, and update the state."""
    if self._states.radio != OFF:
      if use_ui:
        self.PressKey(107, hold=2.0) # END key
        self.DownKey()
        self.DownKey()
        self.CenterKey()
      else:
        self._controller.ShellCommand("stop ril-daemon")
      self._states.radio = OFF

  def IsRadioOn(self):
    return self._states.radio == ON

  def AudioOn(self):
    """Tell us external audio signal is being sent on downlink."""
    self._states.audio = ON

  def AudioOff(self):
    """Tell us external audio signal is NOT being sent on downlink."""
    self._states.audio = OFF

  def IsAudioOn(self):
    return self._states.audio == ON

  def CallActive(self):
    """Tell us phone has call set up."""
    self._states.call = ON

  def CallInactive(self):
    """Tell us we hung up the active call."""
    self._states.call = OFF

  def IsCallActive(self):
    return self._states.call == ON

  def XMPPOn(self):
    """Tell us device is in persistent XMPP mode.."""
    self._states.xmpp = ON

  def XMPPOff(self):
    """Tell us device is not in persistent XMPP mode."""
    self._states.xmpp = OFF

  def IsXMPPPersistent(self):
    return self._states.xmpp == ON

  def LidClosed(self):
    """Tell us device lid is closed."""
    self._states.lid = ON

  def LidOpened(self):
    """Tell us device lid has been."""
    self._states.lid = OFF

  def IsLidOpen(self):
    return self._states.lid == OFF

  def IsLidClosed(self):
    return self._states.lid == ON

  def SyncingOn(self):
    """Tell us syncing is turned on."""
    self._states.sync = ON

  def SyncingOff(self):
    """Tell us syncing is turned off."""
    self._states.sync = OFF

  def IsSyncingOn(self):
    return self._states.sync == ON

  def UpdatesOn(self):
    """Tell us device account is being updated with mails."""
    self._states.updates = ON

  def UpdatesOff(self):
    """Tell us device account is not being updated with mails."""
    self._states.updates = OFF

  def IsUpdatesOn(self):
    return self._states.updates == ON

  def HasAccount(self):
    return self.account is not None

  def SetAccount(self, account, password):
    self.account = account
    self.password = password
    # Device turns these on be default when an account is added.
    if account is None: # setting to None indicates account removed.
      self.hostname = None
      self._states.sync = OFF
      self._states.xmpp = OFF
    else:
      self.hostname = textutils.identifier(account.split("@")[0])
      self._states.sync = ON
      self._states.xmpp = ON


class TMobileDash(MobileDevice):
  """Interace to T-mobile Dash device."""
  pass


class AndroidDevice(MobileDevice):
  APNDBFILE = \
    "/data/data/com.android.providers.telephony/databases/telephony.db"
  ACCOUNTDBFILE = \
    "/data/data/com.google.android.googleapps/databases/accounts.db"
  SETTINGSDBFILE = \
    "/data/data/com.android.providers.settings/databases/settings.db"

  def IsUSBActive(self):
    """Determine if device is actually connected to USB and powered on.
    """
    try:
      self.ActivateUSB()
    except (adb.AdbError, KeyError):
      return False
    else:
      self._states.power = ON
      return True

  def GetState(self):
    if self._controller:
      return self._controller.GetState()
    else:
      raise errors.OperationalError("Not connected to USB")

  def GetBatteryInfo(self):
    if self._controller is not None:
      return BatteryInfo(self._controller)
    else:
      return None

  def GetLEDInfo(self):
    if self._controller is not None:
      return LEDInfo(self._controller)
    else:
      return None

  def IsRunning(self):
    return self.GetState() == adb.DEVICE

  def IsOffline(self):
    return self.GetState() == adb.OFFLINE

  def IsBootloader(self):
    return self.GetState() == adb.BOOTLOADER

  def ActivateUSB(self):
    if self._controller is None:
      adbclient = adb.AdbClient()
      controller = adbclient.GetDevice(self._devid)
      self.serialno = controller.serial
      self._controller = controller

      devnum = self._INPUTMAP.get("keypad")
      if devnum is not None:
        self._keygenerator = AndroidKeyGenerator(controller, self._KEYMAP,
            devnum)
      else:
        self._keygenerator = None

      devnum = self._INPUTMAP.get("synaptics-rmi-touchscreen")
      if devnum is not None:
        self._touchgenerator = AndroidTSGenerator(controller, devnum)
      else:
        self._touchgenerator = None

      devnum = self._INPUTMAP.get("trout-nav")
      if devnum is not None:
        self._navgenerator = AndroidNavGenerator(controller, devnum)
      else:
        self._navgenerator = None

#      TODO(dart) compass...
      self._compassgenerator = None
      self._states.usb = ON

  def UpdateAPN(self, apninfo):
    SQL = aid.mapstr("INSERT INTO carriers "
        "(name, numeric, mcc, mnc, apn, "
        "user, server, password, proxy, port, "
        "mmsc, current) "
        "VALUES ('%(name)s', '%(numeric)s', '%(mcc)s', '%(mnc)s', '%(apn)s', "
        "'%(user)s', '%(server)s', '%(password)s', '%(proxy)s', '%(port)s', "
        "'%(mmsc)s', %(current)s);")
    SQL.name = apninfo.name
    SQL.numeric = "%03d%03d" % (apninfo.mcc, apninfo.mnc) # strange...
    SQL.mcc = "%03d" % apninfo.mcc
    SQL.mnc = "%03d" % apninfo.mnc # TODO(dart) could be 2 or 3 digits
    SQL.apn = apninfo.accesspointname
    SQL.user = apninfo.user
    SQL.password = apninfo.password
    SQL.server = apninfo.server
    SQL.proxy = apninfo.proxy
    SQL.port = apninfo.port
    SQL.mmsc = apninfo.mmsc
    SQL.current = apninfo.iscurrent

    cmd = 'sqlite3 -batch %s "%s"' % (self.APNDBFILE, SQL)
    self._controller.ShellCommand(cmd)
    return str(SQL)

  def GetBluetoothAddress(self):
    if self._btaddress is None:
      self._btaddress = 100996019768 # TODO(dart) get dynamically
    return self._btaddress

  btaddress = property(GetBluetoothAddress)

  def Netperf(self, *args):
    cmd = 'netperf %s' % " ".join(args)
    return self._controller.ShellCommandOutput(cmd)

  def Netserver(self, *args):
    cmd = 'netserver %s' % " ".join(args)
    return self._controller.ShellCommandOutput(cmd)

  def StartCPUEater(self):
    """Starts the CPU eater program. 

    You will get an error if this is not an eng build.
    """
    self._cpueater_pid = self._controller.ShellCommandOutput("cpueater").strip()

  def StopCPUEater(self):
    if self._cpueater_pid is not None:
      self._controller.ShellCommand("kill %s" % self._cpueater_pid)
      self._cpueater_pid = None

  def IsCPUEaterRunning(self):
    return bool(self._cpueater_pid)

  def BugReport(self, stream):
    self._controller.BugReport(stream)

  def Keyboard(self, keys):
    """Press sequence of keys and codes on keyboard."""
    if self._keygenerator:
      self._keygenerator(keys)
    else:
      raise errors.OperationalError("Not connected to USB")

#  def Playback(self, script, settings=False):
#    if settings:
#      self.StartSettings()
#    script.Perform(self._controller)

  def Record(self, source, script_object, count=0):
    srcobj = self.GetSource(source)
    srcobj.GetEvents(script_object.Append, count)

  def GetSource(self, name):
    if name.startswith("key"):
      srcobj = self._keygenerator
    elif name.startswith("nav"):
      srcobj = self._navgenerator
    elif name.startswith("tou"):
      srcobj = self._touchgenerator
    elif name.startswith("com"):
      srcobj = self._compassgenerator
    else:
      raise ValueError("Must supply input source name.")
    return srcobj

  def UpdateSoftware(self, zipfilename, wipe=False, flash=False):
    """Update the software image from a built zip file. 

    Args:
      zipfilename (string): the path name to a zip file containing and
          Android software image. e.g.: sooner-img-12345.zip
      wipe (boolean, optional): True means wipe the data partition.
      flash (boolean, optional): True means flash the user.img file to
          device.
    """
    raise NotImplementedError("Implement in subclass")

  def GoHome(self):
    """Put the UI in the default position.

    This "should" work on both old and new UI.
    """
    self.HomeKey()
    self.HomeKey() # twice, in case screen was off.
    # Can't predict how far up or over current place will be. This
    # "presses" right and down key enough times to make sure the current
    # selection ends up in bottom right.
    for i in xrange(6):
      self.RightKey()
    for i in xrange(10):
      self.DownKey()
    self.CenterKey()

  def Start(self, activity, extra=None):
    if extra is not None:
      extraflags = " ".join(['-e %s "%s"' % t for t in extra.items()])
    else:
      extraflags = ""
    rv = self._controller.ShellCommandOutput(
        "am start -n %s %s" % (activity, extraflags))
    scheduler.sleep(2.0)
    return rv

  def StartSettings(self):
    rv = self._controller.ShellCommandOutput(
        "am start -n com.android.settings/.SettingsTwo")
    scheduler.sleep(3.0)
    return rv

  def PressKey(self, code, delay=0.0, hold=0.0, 
        shift=False, alt=False, sym=False):
    cont = self._keygenerator
    if sym:
      cont.KeyPress(127)
    if alt:
      cont.KeyPress(56)
    if shift:
      cont.KeyPress(42)
    cont.KeyPress(code)
    if hold:
      scheduler.sleep(hold)
    cont.KeyRelease(code)
    if shift:
      cont.KeyRelease(42)
    if alt:
      cont.KeyRelease(56)
    if sym:
      cont.KeyRelease(127)
    if delay:
      scheduler.sleep(delay)

  def GetTimeInfo(self):
    text = self._controller.ShellCommandOutput("timeinfo")
    return TimeInfoReport(*text.split())

  def GetProp(self, name):
    return self._controller.ShellCommandOutput("getprop %s" % name)

  def SetProp(self, name, value):
    self._controller.ShellCommand("setprop %s %s" % (name, value))

  def IsBootComplete(self):
    return bool(self.GetProp("dev.bootcomplete").strip())



class SoonerDevice(AndroidDevice):

  _KEYMAP = { # sooner key map
   '!': ALT | event.KEY_Y,
   '"': ALT | event.KEY_K,
   '#': ALT | event.KEY_A,
   '$': ALT | event.KEY_I,
   '%': ALT | event.KEY_M,
   '&': ALT | event.KEY_U,
   '(': ALT | event.KEY_O,
   ')': ALT | event.KEY_P,
   '*': ALT | event.KEY_Q,
   '+': ALT | event.KEY_T,
   ':': ALT | event.KEY_DOT,
   '<': ALT | event.KEY_B,
   '>': ALT | event.KEY_N,
   '?': ALT | event.KEY_SLASH,
   '@': event.KEY_EMAIL,
   '^': SHIFT | ALT | event.KEY_V,
   '_': SHIFT | ALT | event.KEY_G,
   '{': SHIFT | ALT | event.KEY_H,
   '|': SHIFT | ALT | event.KEY_COMMA,
   '}': SHIFT | ALT | event.KEY_J,
   '~': SHIFT | ALT | event.KEY_K,
   "'": ALT | event.KEY_L,
   ',': event.KEY_COMMA,
   '-': ALT | event.KEY_G,
   '.': event.KEY_DOT,
   '/': event.KEY_SLASH,
   ';': ALT | event.KEY_COMMA,
   '=': ALT | event.KEY_V,
   '[': ALT | event.KEY_H,
   ']': ALT | event.KEY_J,
   '\t': ALT | event.KEY_SPACE,
  }

  _DIALMAP = textutils.maketrans("123456789", "wersdfzxc")

  def UpdateSoftware(self, zipfilename, wipe=False, flash=False):
    self._controller.Update(zipfilename, wipe, flash)
    if wipe:
      scheduler.sleep(60) # time to reach home screen.
      # default settings
      self.SetAccount(None, None)
    self._build = None

  def Call(self, number="6502849239"):
    if self._controller is not None:
      number = number.translate(self._DIALMAP)
      number = number.replace("0", "<EMAIL>") # zero button is on EMAIL key
      self._keygenerator("<HOME>" + number + "<SEND>")
      self.CallActive()
    else:
      raise errors.OperationalError("Call: no usb connection.")

  def Hangup(self):
    if self._controller is not None:
      self.Unlock()
      self.EndKey()
      self.CallInactive()
    else:
      raise errors.OperationalError("Hangup: no usb connection.")

  def AnswerCall(self):
    # Twice, in case the display is off.
    self.PressKey(231) # SEND key
    self.PressKey(231)

  def Reboot(self, bootloader=False):
    self._controller.Reboot(bootloader)
    retries = 3
    while retries:
      scheduler.sleep(2)
      try:
        if bootloader:
          self._controller.WaitForBootloader()
        else:
          self._controller.WaitForDevice()
      except adb.AdbError: # may or may not get this error first time.
        retries -= 1
      else:
        break

  # special keys for sooner
  def HomeKey(self, delay=0.0):
    self.PressKey(102, delay)

  def UpKey(self, delay=0.0):
    self.PressKey(103, delay)

  def DownKey(self, delay=0.0):
    self.PressKey(108, delay)

  def LeftKey(self, delay=0.0):
    self.PressKey(105, delay)

  def RightKey(self, delay=0.0):
    self.PressKey(106, delay)

  def CenterKey(self, delay=0.0):
    self.PressKey(232, delay) # REPLY

  def PowerKey(self, delay=0.0):
    self.PressKey(116, delay) # POWER key

  def CallKey(self, delay=0.0):
    self.PressKey(231, delay) # SEND key

  def EndKey(self, delay=0.0):
    self.PressKey(107, delay) # END ends call

  def BackKey(self, delay=0.0):
    self.PressKey(158, delay) # BACK key

  def MenuKey(self, delay=0.0):
    self.PressKey(229, delay) # KBDILLUMDOWN key

  def StarKey(self, delay=0.0):
    self.PressKey(230, delay) # KBDILLUMUP key

  def PowerOff(self):
    self.PowerKey()
    self.PowerKey()
    self.DownKey()
    self.DownKey()
    try:
      self.CenterKey()
    except adb.AdbError: # no more device!
      pass

  # XXX deprecated below, will be removed soon. Recorded events will be
  # used instead.
  def ToggleSyncState(self):
    self.StartSettings()
    kbd = self._keygenerator
    kbd("s") # jump to s'es.
    kbd("<DOWN><DOWN>")
    kbd("<REPLY>") # entering sync config (third s)
    kbd("<UP>")    # up to "master" control.
    kbd("<REPLY>") # toggle it.
    kbd("<DOWN>")  # in multiselect menu.
    kbd("<RIGHT><DOWN><DOWN><REPLY><UP><UP>")
    kbd("<RIGHT><DOWN><DOWN><REPLY><UP><UP>")
    kbd("<RIGHT><DOWN><DOWN><REPLY><UP><UP>")
    kbd("<RIGHT><DOWN><DOWN><REPLY><UP><UP>")
    kbd("<BACK><BACK>")

  def ToggleGmailLS(self):
    self.StartSettings()
    kbd = self._keygenerator
    kbd("s") # jump to s'es.
    kbd("<DOWN><DOWN>")
    kbd("<REPLY>") # entering sync config (third s)
    kbd("<RIGHT><RIGHT><DOWN><DOWN><REPLY><UP><UP>")
    kbd("<BACK><BACK>")

  def ToggleXMPP(self):
    self.StartSettings()
    kbd = self._keygenerator
    kbd("g") # jump to G's
    kbd("<DOWN><REPLY>") # skip to Gtalk Settings, enter it.
    kbd("<REPLY>") # already on checkbox, toggle it.
    kbd("<BACK><BACK>")


#### dream


class DreamDevice(AndroidDevice):

  def UpdateSoftware(self, zipfilename, wipe=False, flash=False):
    cmd = "fastboot %s update %s" % (aid.IF(wipe, "-w", ""), zipfilename,)
    pm = proctools.get_procmanager()
    proc = pm.spawnpipe(cmd)
    output = proc.read()
    errors = proc.readerr()
    proc.close()
    status = proc.wait()
    if wipe:
      self.SetAccount(None, None)
    self._build = None
    return status, output, errors

  def Reboot(self, bootloader=False):
    if self._controller is not None:
      if bootloader:
        cmd = "reboot bootloader"
      else:
        cmd = "reboot"
      try:
        scheduler.timeout(self._controller.ShellCommand, (cmd,))
      except (adb.AdbError, scheduler.TimeoutError):
        pass
    else:
      raise errors.OperationalError("Reboot: no usb connection.")

  def AnswerCall(self, delay=1.0):
    self.PressKey(231, 0)
    self.PressKey(231, delay)

  def Call(self, number="6502849239"):
    if self._controller is not None:
      self.Unlock()
      self.HomeKey()
      self.CallKey()
      if self._states.lid == OFF: # open
        self.Touch(3000, 300)
      else:
        self.Touch(300, 300)
      scheduler.sleep(2)
      self._keygenerator(number)
      self.CallKey()
      self.CallActive()
    else:
      raise errors.OperationalError("Call: no usb connection.")

  def Hangup(self):
    if self._controller is not None:
      self.Unlock()
      self.EndKey()
      self.CallInactive()
    else:
      raise errors.OperationalError("Hangup: no usb connection.")

  # special keys for trout
  def HomeKey(self, delay=1.0):
    self.PressKey(102, delay)

  # These are not actually key events, but nav device
  # events. The API is the same, however, for automation.
  # Screen orientation changes depending on Lid state, but event layer
  # does not change. 
  def UpKey(self, delay=1.0):
    if self._states.lid == OFF: # open
      self._navgenerator.MoveRight(3)
    else:
      self._navgenerator.MoveUp(3)
    if delay:
      scheduler.sleep(delay)

  def DownKey(self, delay=1.0):
    if self._states.lid == OFF: # open
      self._navgenerator.MoveLeft(3)
    else:
      self._navgenerator.MoveDown(3)
    if delay:
      scheduler.sleep(delay)

  def LeftKey(self, delay=1.0):
    if self._states.lid == OFF: # open
      self._navgenerator.MoveUp(3)
    else:
      self._navgenerator.MoveLeft(3)
    if delay:
      scheduler.sleep(delay)

  def RightKey(self, delay=1.0):
    if self._states.lid == OFF: # open
      self._navgenerator.MoveDown(3)
    else:
      self._navgenerator.MoveRight(3)
    if delay:
      scheduler.sleep(delay)

  def CenterKey(self, delay=1.0):
    self._navgenerator.SendEvent(event.EV_KEY, event.BTN_MOUSE, 1)
    self._navgenerator.SendEvent(event.EV_KEY, event.BTN_MOUSE, 0)
    if delay:
      scheduler.sleep(delay)

  def PowerKey(self, delay=1.0):
    pass

  def CallKey(self, delay=1.0):
    self.PressKey(231, delay) # SEND key

  def EndKey(self, delay=1.0):
    self.PressKey(107, delay) # END ends call

  def BackKey(self, delay=1.0):
    self.PressKey(158, delay) # BACK key

  def MenuKey(self, delay=1.0):
    self.PressKey(139, delay) #  MENU key

  def StarKey(self, delay=1.0):
    pass

  def CameraKeySoft(self, hold=1.0, delay=1.0):
    self.PressKey(211, delay, hold=hold)

  def CameraKeyHard(self, delay=1.0):
    self.KeyPress(212)
    self.PressKey(211, 0.5)
    self.KeyRelease(212)
    if delay:
      scheduler.sleep(delay)

  def VolumeUp(self, delay=1.0):
    self.PressKey(115, delay)

  def VolumeDown(self, delay=1.0):
    self.PressKey(114, delay)

  def MoveUp(self, ticks=1):
    self._navgenerator.MoveUp(ticks)

  def MoveDown(self, ticks=1):
    self._navgenerator.MoveDown(ticks)

  def MoveLeft(self, ticks=1):
    self._navgenerator.MoveLeft(ticks)

  def MoveRight(self, ticks=1):
    self._navgenerator.MoveRight(ticks)

  def OpenLid(self):
    if not self.IsLidOpen():
      self._keygenerator.SendEvent(event.EV_SW, event.SW_LID, 0)
      self.LidOpened()
      return True
    return False

  def CloseLid(self):
    if not self.IsLidClosed():
      self._keygenerator.SendEvent(event.EV_SW, event.SW_LID, 1)
      self.LidClosed()
      return True
    return False

  def ToggleLid(self):
    if self._states.lid == OFF:
      self.CloseLid()
    elif self._states.lid == ON:
      self.OpenLid()
    else: # UNKNOWN state, make closed
      self._keygenerator.SendEvent(event.EV_SW, event.SW_LID, 1)
      self.LidClosed()

  def Touch(self, x, y):
    """Hey, it works."""
    self._touchgenerator.SendEvent(0, 0, 0)
    self._touchgenerator.SendEvent(3, 0, x) # x
    self._touchgenerator.SendEvent(3, 1, y) # y
    self._touchgenerator.SendEvent(3, 24, 83)
    self._touchgenerator.SendEvent(3, 28, 1)
    self._touchgenerator.SendEvent(1, 330, 1)
    self._touchgenerator.SendEvent(0, 0, 0)
    self._touchgenerator.SendEvent(3, 0, x)
    self._touchgenerator.SendEvent(3, 1, y)
    self._touchgenerator.SendEvent(3, 24, 87)
    self._touchgenerator.SendEvent(0, 0, 0)
    self._touchgenerator.SendEvent(3, 0, x)
    self._touchgenerator.SendEvent(3, 1, y)
    self._touchgenerator.SendEvent(0, 0, 0)
    self._touchgenerator.SendEvent(3, 0, x)
    self._touchgenerator.SendEvent(3, 1, y)
    self._touchgenerator.SendEvent(3, 24, 58)
    self._touchgenerator.SendEvent(0, 0, 0)
    self._touchgenerator.SendEvent(3, 24, 8)
    self._touchgenerator.SendEvent(3, 28, 6)
    self._touchgenerator.SendEvent(1, 330, 0)
    self._touchgenerator.SendEvent(0, 0, 0)
    self._touchgenerator.SendEvent(3, 24, 0)
    self._touchgenerator.SendEvent(3, 28, 0)
    self._touchgenerator.SendEvent(0, 0, 0)

  def Unlock(self):
    self.MenuKey()
    self.MenuKey()
    self.BackKey()

  def ToggleSyncState(self):
    self.Unlock()
    self.Start("com.android.settings/"
        "com.android.settings.SyncSettings")
    scheduler.sleep(2.0)
    self.DownKey() # activate nav mode without doing anything else
    self.UpKey()
    self.UpKey()
    self.CenterKey() # toggle master setting
    scheduler.sleep(1.0)
    self.BackKey()
    self.ToggleState("sync")
    self.ToggleState("xmpp")

  def ToggleWifiState(self):
    self.Unlock()
    self.StartSettings()
    self.DownKey() # activates nav mode
    self.UpKey() 
    self.CenterKey()
    scheduler.sleep(3.0)
    self.BackKey()
    self.ToggleState("wifi")

  def ToggleBluetoothState(self):
    self.Unlock()
    self.StartSettings()
    self.UpKey()
    for i in range(5):
      self.DownKey()
    self.CenterKey()
    scheduler.sleep(3.0)
    self.BackKey()
    self.ToggleState("bluetooth")

  def ToggleAirplaneMode(self):
    self.Unlock()
    self.StartSettings()
    self.UpKey()
    self.DownKey()
    self.DownKey()
    self.CenterKey()
    scheduler.sleep(3.0)
    self.BackKey()
    self.ToggleState("airplane")

  def SetupWizard(self, name, password, use_ui=False):
    if use_ui:
      kbd = self._keygenerator
      self.OpenLid()
      scheduler.sleep(1.0)
      kbd(name)
      kbd("<ENTER>")
      scheduler.sleep(1.0)
      kbd(password)
      kbd("<ENTER>")
      scheduler.sleep(1.0)
      self.RightKey()
      self.CenterKey()
    else:
      sql = ("DELETE FROM accounts;\n "
          "INSERT INTO accounts (username, password, flags) "
          "VALUES ('%s', '%s', %d);") % (name,
                                         password.encode('base64').strip(),
                                         1)
      cmd = 'sqlite3 -batch %s "%s"' % (self.ACCOUNTDBFILE, sql)
      self._controller.ShellCommand(cmd)
    self.SetAccount(name, password)

  def SetGservicesSetting(self, name, value):
    sql = "insert into gservices(name,value) values ('%s','%s');" % (name, value)
    return SQLQuery(self._controller, self.SETTINGSDBFILE, sql)

  def GetGservicesSetting(self, name):
    sql = "select 'VALUE['||value||']' from gservices where name='%s';" % name
    result = SQLQuery(self._controller, self.SETTINGSDBFILE, sql)
    match = _SQL_VALUE_RE.search(result)
    return match and match.group(1) or ""

_SQL_VALUE_RE = re.compile(r"VALUE\[(.*)\]")

def SQLQuery(adb, db, sql):
  cmd = 'sqlite3 -batch %s "%s"' % (db, sql)
  return adb.ShellCommandOutput(cmd)


_DREAM_KEYMAP_V3 = {
   '!': SHIFT | event.KEY_1,
   '"': ALT | event.KEY_K,
   '#': SHIFT | event.KEY_3,
   '$': SHIFT | event.KEY_4,
   '%': SHIFT | event.KEY_5,
   '^': SHIFT | event.KEY_6,
   '&': SHIFT | event.KEY_7,
   '*': SHIFT | event.KEY_8,
   '(': SHIFT | event.KEY_9,
   ')': SHIFT | event.KEY_0,
   '+': ALT | event.KEY_O,
   ':': ALT | event.KEY_H,
   '<': ALT | event.KEY_N,
   '>': ALT | event.KEY_M,
   '?': SHIFT | event.KEY_COMMA,
   '@': event.KEY_EMAIL,
   '_': ALT | event.KEY_E,
   '{': ALT | event.KEY_F,
   '|': ALT | event.KEY_S,
   '}': ALT | event.KEY_G,
   '\\': ALT | event.KEY_D,
   '~': ALT | event.KEY_EMAIL,
   "'": ALT | event.KEY_L,
   ',': event.KEY_COMMA,
   '-': ALT | event.KEY_I,
   '.': event.KEY_DOT,
   '/': ALT | event.KEY_DOT,
   ';': ALT | event.KEY_J,
   '=': ALT | event.KEY_P,
   '[': ALT | event.KEY_V,
   ']': ALT | event.KEY_B,
   '\t': ALT | event.KEY_Q,
   '\0': SHIFT | ALT | event.KEY_W,
   u'ç': SHIFT | ALT | event.KEY_C,
   u' ́': SHIFT | ALT | event.KEY_E, # combining
   u'¥': SHIFT | ALT | event.KEY_F,
   u'€': SHIFT | ALT | event.KEY_R,
   u'ß': SHIFT | ALT | event.KEY_S,
   u'£': SHIFT | ALT | event.KEY_T,
   u'…': SHIFT | ALT | event.KEY_DOT,
   u'•': SHIFT | ALT | event.KEY_EMAIL,
   u'¡': SHIFT | ALT | event.KEY_Y,
  }


_DREAM_KEYMAP_V2 = {
   '!': SHIFT | event.KEY_1,
   '"': ALT | event.KEY_K,
   '#': SHIFT | event.KEY_3,
   '$': SHIFT | event.KEY_4,
   '%': SHIFT | event.KEY_5,
   '^': SHIFT | event.KEY_6,
   '&': SHIFT | event.KEY_7,
   '*': SHIFT | event.KEY_8,
   '(': SHIFT | event.KEY_9,
   ')': SHIFT | event.KEY_0,
   '+': ALT | event.KEY_O,
   ':': ALT | event.KEY_H,
   '<': ALT | event.KEY_N,
   '>': ALT | event.KEY_M,
   '?': SHIFT | event.KEY_SLASH,
   '@': event.KEY_EMAIL,
   '_': ALT | event.KEY_U,
   '{': ALT | event.KEY_T,
   '|': ALT | event.KEY_E,
   '}': ALT | event.KEY_Y,
   '\\': SHIFT | ALT | event.KEY_SLASH,
   '~': SHIFT | ALT | event.KEY_K,
   "'": ALT | event.KEY_L,
   ',': event.KEY_COMMA,
   '-': ALT | event.KEY_I,
   '.': event.KEY_DOT,
   '/': event.KEY_SLASH,
   ';': ALT | event.KEY_J,
   '=': ALT | event.KEY_P,
   '[': ALT | event.KEY_F,
   ']': ALT | event.KEY_G,
   '\t': ALT | event.KEY_SPACE,
   '\0': SHIFT | ALT | event.KEY_D,
   u'ç': SHIFT | ALT | event.KEY_C,
   u' ́': SHIFT | ALT | event.KEY_E,
   u'¥': SHIFT | ALT | event.KEY_F,
   u'€': SHIFT | ALT | event.KEY_R,
   u'ß': SHIFT | ALT | event.KEY_S,
   u'£': SHIFT | ALT | event.KEY_T,
   u'…': SHIFT | ALT | event.KEY_DOT,
   u'•': SHIFT | ALT | event.KEY_EMAIL,
   u'¡': SHIFT | ALT | event.KEY_Y,
  }


_EVENTDEV_RE = re.compile(r"add device (\d+): /dev/input/event(\d+)")
_KEYPADNAME_RE = re.compile(r"(\w+)-keypad-v(\d)")

def GetDeviceClass(devid):
  adbclient = adb.AdbClient()
  controller = adbclient.GetDevice(devid)
  devrpt = controller.ShellCommandOutput("getevent -S")
  pstate = 0
  devmap = {}
  for line in devrpt.splitlines():
    mo = _EVENTDEV_RE.search(line)
    if mo:
      devnum = int(mo.group(2))
      pstate = 1
    elif pstate == 1:
      pstate = 0
      name = line.split()[1][1:-1]
      kpmo = _KEYPADNAME_RE.search(name)
      if kpmo:
        model = kpmo.group(1)
        kptype = int(kpmo.group(2))
        if model.startswith("trout"):
          if kptype == 2:
            klass = DreamDevice
            klass._KEYMAP = _DREAM_KEYMAP_V2
            klass._REVISION = 2
          elif kptype == 3:
            klass = DreamDevice
            klass._KEYMAP = _DREAM_KEYMAP_V3
            klass._REVISION = 3
          else:
            raise ValueError("Don't know about device with keypad: %r" % name)
        elif model.startswith("sardine5"): # untested
          klass = SoonerDevice
          klass._REVISION = 5
        else:
          raise ValueError("Don't know about keypad model: %r" % model)
        devmap[name.split("-")[1]] = devnum
      else:
        devmap[name] = devnum
  klass._INPUTMAP = devmap
  return klass


def GetDevice(device_id):
  """Constructor for Android device objects.

  Does dynamic inspection of DUT, returns AndroidDevice class instance
  with proper attributes set reflecting devices keymapping and input
  device mapping.
  """
  try:
    device_id = int(device_id)
  except ValueError:
    pass # probably a serial no. string
  try:
    devclass = GetDeviceClass(device_id)
  except adb.AdbError:
    return None
  else:
    return devclass(device_id)



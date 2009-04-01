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



"""Command tool commands for devices.
"""


import os

from pycopia import getopt
from pycopia import CLI

from droid import adb
from droid import devices


# NOTE: the methods in these classes follow the CLI API. The CLI framework
# uses them to define the available commands, and also formats the doc
# strings in its own way. These methods are not intended to be called by
# other code, but implement the available interactive commands. Therefore,
# they are different from the Google style guide.

class AdbClientCommands(CLI.BaseCommands):

  def _reset_scopes(self):
    dm = self._obj.GetDevices()
    sernos = dm.GetSerialNumbers()
    self.add_completion_scope("use", sernos)
    self.add_completion_scope("settings", ["gservice"])

  def ls(self, argv):
    """ls
  List available devices."""
    dm = self._obj.GetDevices()
    self._print(str(dm))

  def use(self, argv):
    """use <device_id>
  Interact with specific device."""
    opts, longopts, args = self.getopt(argv, "")
    dev = devices.GetDevice(args[0])
    cmd = self.clone(AndroidCommands)
    if dev.build:
      cmd._setup(dev, "%s-%s> " % (dev.build.product, dev.serialno))
    else:
      cmd._setup(dev, "unknown-%s> " % (dev.serialno,))
    raise CLI.NewCommand, cmd


class AndroidCommands(CLI.GenericCLI):

  def _reset_scopes(self):
    self.add_completion_scope("toggle", ["sync", "lid", "wifi", 
        "airplane", "bluetooth"])
    self.add_completion_scope("account", ["setup", "delete", "add"])
    self.add_completion_scope("getevents", 
        [ "keyboard", "navigator", "touchscreen", "compass"])

  def initialize(self):
    self._logcatproc = None
    self._logcatfile = None

  # default action is to run command on DUT.
  def default_command(self, argv):
    cmd = " ".join(argv)
    try:
      text = self._obj._controller.ShellCommandOutput(cmd)
      self._print(text)
    except KeyboardInterrupt:
      pass

  ls = default_command # override 'ls' here since it's also built-in

  def reboot(self, argv):
    """reboot [bootloader]
  Reboot the device."""
    if len(argv) > 1 and argv[1].startswith("b"):
      bootloader = True
    else:
      bootloader = False
    self._obj.Reboot(bootloader)
    raise CLI.CommandQuit

  def bootcomplete(self, argv):
    """bootcomplete
  Tell if boot process is complete."""
    if self._obj.IsBootComplete():
      self._print("Boot has completed.")
    else:
      self._print("Boot still in progress.")

  def getprop(self, argv):
    """getprop <key>
  Return the value of property with name <key>."""
    rv = self._obj.GetProp(argv[1])
    self._print(rv)
    return rv

  def setprop(self, argv):
    """setprop <key> <value>
  Set the value of property with name <key> to <value>."""
    self._obj.SetProp(argv[1], argv[2])
    self._print(rv)
    return rv

  def state(self, argv):
    """state
  Show current state."""
    self._print(self._obj.GetState())

  def bugreport(self, argv):
    """bugreport [<filename>]
  Emit bug report to stdout, or a file if a name is given."""
    if len(argv) > 1:
      filename = argv[1]
      fo = open(filename, "w")
      doclose = True
    else:
      fo = self._ui._io
      doclose = False
    try:
      self._obj.BugReport(fo)
    finally:
      if doclose:
        fo.close()

  def dumpstate(self, argv):
    """dumpstate
  Emit state."""
    self._obj._controller.DumpState(self._ui._io)

  def dumpsys(self, argv):
    """dumpsys
  Emit system state."""
    self._obj._controller.DumpSys(self._ui._io)

  def logcat(self, argv):
    """logcat [options] [filterspecs]
  Emit logcat. Write to stdout if no file name is given. If a file name is
  given, write to that file in the background. If the special name "stop"
  is given the stop writing and close the file.

  options include:
    -s              Set default filter to silent.
                    Like specifying filterspec '*:s'
    -f <filename>   Log to file. Default to stdout
    -v <format>     Sets the log print format, where <format> is one of:

                    brief process tag thread raw time threadtime long

    -b <buffer>     request alternate ring buffer, defaults to 'main'  

  filterspecs are a series of 
    <tag>[:priority]

  where <tag> is a log component tag (or * for all) and priority is:
    V    Verbose
    D    Debug
    I    Info
    W    Warn
    E    Error
    F    Fatal
    S    Silent (supress all output)

  '*' means '*:d' and <tag> by itself means <tag>:v

  If not specified on the commandline, filterspec is set from ANDROID_LOG_TAGS.
  If no filterspec is found, filter defaults to '*:I'

  If not specified with -v, format is set from ANDROID_PRINTF_LOG
  or defaults to "brief"
  """
    fname = None
    lcargs = []
    opts, longopts, args = self.getopt(argv, "sf:v:b:")
    for opt, optarg in opts:
      # passthrough opts
      if opt == "-s":
        lcargs.append("-s")
      elif opt == "-v":
        lcargs.append("-v %s" % (optarg,))
      elif opt == "-b":
        lcargs.append("-b %s" % (optarg,))
      # our opts
      elif opt == "-f":
        fname = optarg
    lcargs.append(" ".join(args))

    bufsize = int(longopts.get("bufsize", -1))

    if fname:
      self._logcatproc = self._obj._controller.LogcatFile(
          fname, bufsize, " ".join(lcargs))
      self._logcatfile = fname
    else:
      if args and args[0].startswith("stop") and self._logcatproc is not None:
        self._logcatproc.kill()
        self._logcatproc.wait()
        self._logcatproc = None
        self._logcatfile = None
      elif self._logcatfile is not None:
        self._print("Currently streaming logcat to %r." % (
            self._logcatfile,))
      else:
        try:
          self._obj._controller.Logcat(self._ui._io, " ".join(lcargs))
        except KeyboardInterrupt:
          pass

  def poweroff(self, argv):
    """poweroff
  Turn the device off. You won't be able to use it after this."""
    self._obj.PowerOff()
    raise CLI.CommandQuit

  def radio(self, argv):
    """radio [-u] on|off
  Control radio, on or off. 
  -u = use user interface. Otherwise, runs control program."""
    useui = False
    opts, longopts, args = self.getopt(argv, "u")
    for opt, arg in opts:
      if opt == "-u":
        useui = True
    subcmd = args[0]
    if subcmd == "on":
      self._obj.RadioOn(useui)
    elif subcmd == "off":
      self._obj.RadioOff(useui)
    else:
      self._ui.error('Must use "on" or "off".')

  def cpueater(self, argv):
    """cpueater [start|stop]
  Start or stop the "cpueater" process on the DUT.
  If no command supplied then show the current state."""
    if len(argv) > 1:
      cmd = argv[1]
      if cmd == "start":
        self._obj.StartCPUEater()
      else:
        self._obj.StopCPUEater()
    else:
      if self._obj.IsCPUEaterRunning():
        self._print("CPU eater is running.")
      else:
        self._print("CPU eater is NOT running.")

  def timeinfo(self, argv):
    """timeinfo
  Report time information from DUT."""
    self._print(self._obj.GetTimeInfo())

  def addapn(self, argv):
    """addapn
  Add the testbed APN info from the database."""
    from droid.storage import Storage
    cf = Storage.GetConfig()
    self._obj.UpdateAPN(cf.environment.APNINFO)
    self._print("Added APN info for %r." % cf.environment.APNINFO.name)

  def touch(self, argv):
    """touch <x> <y>
  Touch the screen at the given coordinates."""
    x = int(argv[1])
    y = int(argv[2])
    self._obj.Touch(x, y)

  def kbd(self, argv):
    """kbd <text>
  Send text, converted to keystrokes, to device. You can also send key
  codes in angle brackets. For example:

    <HOME><LEFT><LEFT><LEFT><LEFT><REPLY>

  Enters the applications menu.
  """
    text = " ".join(argv[1:])
    self._obj.Keyboard(text)

  def dial(self, argv):
    """dial <phonenumber>
  Dial the given phone number."""
    self._obj.Call(argv[1])

  def answer(self, argv):
    """answer
  Answer an alerting device."""
    self._obj.AnswerCall()

  def hangup(self, argv):
    """hangup
  Hang up an active call."""
    self._obj.Hangup()

  def home(self, argv):
    """home
  Go to home screen, in the default position."""
    self._obj.GoHome()

  def homekey(self, argv):
    """homekey
  Press the HOME key."""
    self._obj.HomeKey()

  def upkey(self, argv):
    """upkey
  Press the UP key."""
    self._obj.UpKey()

  def downkey(self, argv):
    """downkey
  Press the DOWN key."""
    self._obj.DownKey()

  def leftkey(self, argv):
    """leftkey
  Press the LEFT key."""
    self._obj.LeftKey()

  def rightkey(self, argv):
    """rightkey
  Press the RIGHT key."""
    self._obj.RightKey()

  def centerkey(self, argv):
    """centerkey
  Press the CENTER key."""
    self._obj.CenterKey()

  def menukey(self, argv):
    """menukey
  Press the MENU key."""
    self._obj.MenuKey()

  def starkey(self, argv):
    """menukey
  Press the STAR key."""
    self._obj.StarKey()

  def backkey(self, argv):
    """backkey
  Press the BACK key."""
    self._obj.BackKey()

  def powerkey(self, argv):
    """powerkey
  Press the Power button."""
    self._obj.PowerKey()

  def callkey(self, argv):
    """callkey
  Press the CALL key."""
    self._obj.CallKey()

  def endkey(self, argv):
    """end
  Press the END key."""
    self._obj.EndKey()

  def openlid(self, argv):
    """openlid
  Simulates opening a lid."""
    self._obj.OpenLid()

  def closelid(self, argv):
    """closelid
  Simulates closing a lid."""
    self._obj.CloseLid()

  def cyclelid(self, argv):
    """cyclelid
  Simulates opening and then closing a lid."""
    self._obj.OpenLid()
    self._print("Lid opened, waiting 5 seconds...")
    CLI.timer.sleep(5)
    self._obj.CloseLid()
    self._print("Lid closed.")

  def volume(self, argv):
    """volume up|down
  Change the volume by pressing volume keys."""
    direction = argv[1].lower()
    if direction.startswith("u"):
      self._obj.VolumeUp()
    if direction.startswith("d"):
      self._obj.VolumeDown()

  def camera(self, argv):
    """camera [hard]
  Press the camera key. By default press soft, press hard if hard flag
  given."""
    if len(argv) > 1 and argv[1].startswith("h"):
      self._obj.CameraKeyHard()
    else:
      self._obj.CameraKeySoft()

  def toggle(self, argv):
    """toggle <setting>
  Toggle the setting, by name.
  Currently available:
    sync
    wifi
    bluetooth
    airplane
    lid
  """
    setting = argv[1]
    if setting.startswith("sy"):
      self._obj.ToggleSyncState()
    elif setting.startswith("wi"):
      self._obj.ToggleWifiState()
    elif setting.startswith("bl"):
      self._obj.ToggleBluetoothState()
    elif setting.startswith("ai"):
      self._obj.ToggleAirplaneMode()
    elif setting.startswith("li"):
      self._obj.ToggleLid()
    else:
      self._ui.error("No such setting value.")

  def account(self, argv):
    """account [add|del|setup] [<name> <password>]
  Add or delete a GAIA account on device. The setup subcommand performs
  the setup wizard operation."""

    useui = False
    opts, longopts, args = self.getopt(argv, "u")
    for opt, arg in opts:
      if opt == "-u":
        useui = True
    cmd = args[0]
    if cmd.startswith("add"):
      name = args[1]
      password = args[2]
      self._obj.AddAccount(name, password)
    elif cmd.startswith("set"):
      name = args[1]
      password = args[2]
      self._obj.SetupWizard(name, password, useui)
    elif cmd.startswith("del"):
      self._obj.RemoveAccount()
    else:
      self._ui.error("Must add or delete account.")

  def battery(self, argv):
    """battery
  Get battery information."""
    self._print(self._obj.GetBatteryInfo())

  def leds(self, argv):
    """leds
  Get LED brightness information."""
    self._print(self._obj.GetLEDInfo())

  def start(self, argv):
    """start [--extra=option ...] <activity>
  Start an Android activity. Provide the full path."""
    opts, longopts, args = self.getopt(argv, "")
    self._obj.Start(args[0], longopts)

  def update(self, argv):
    """update [-w] [-f] <zipfile>
  Update the device with the given built zipfile.
  Options:
    -w -- wipe the data partition.
    -f -- Flash the data partition with userdata from zipfile.  """
    wipe = False
    flash = False
    opts, longopts, args = self.getopt(argv, "wf")
    for opt, optarg in opts:
      if opt == "-w":
        wipe = True
      elif opt == "-f":
        flash = True
    self._obj.UpdateSoftware(args[0], wipe, flash)

  def getevents(self, argv):
    """getevents <source>
  Print kernel-level events from the given source. Ctl-C to stop.
  Source can be one of:
    keyboard
    navigator (trackball)
    touchscreen
    compass
    """
    srcobj = self._obj.GetSource(argv[1])
    if srcobj is not None:
      try:
        # GetEvents is an infinite loop. User press Ctl-C To interrupt and
        # we get control back here.
        srcobj.GetEvents(self._PrintEvent)
      except KeyboardInterrupt:
        pass
    else:
      self._ui.error("Source not available.")

  def _PrintEvent(self, ts, evtype, evcode, evvalue):
    self._print("%s %s %s %s" % (ts, evtype, evcode, evvalue))

  def record(self, argv):
    """record [-s] <source> <filename>
  Record device input events and record them to the given file name.
  Ctl-C (Interrupt) stops recording.
  If option -s is given then put device into the settings menu first."""

    opts, longopts, args = self.getopt(argv, "s")
    for opt, arg in opts:
      if opt == "-s":
        self._obj.StartSettings()
    fname = args[1]
    source = args[0]
    script = devices.EventScript(source)
    try:
      self._obj.Record(source, script)
    except KeyboardInterrupt:
      pass
    script.WriteFile(fname)

  def playback(self, argv):
    """playback [-s] <filename>
  Play keystrokes back that were previously recorded.
  If option -s is given then start from the settings menu."""
    settings = False
    opts, longopts, args = self.getopt(argv, "s")
    for opt, arg in opts:
      if opt == "-s":
        settings = True
    fname = args[0]
    script = devices.EventScript(filename=fname)
    self._obj.Playback(script, settings)

  def shell(self, argv):
    """shell [<command>]
  Run a shell command. Start an interactive shell if no command is given."""
    if len(argv) > 1:
      cmd = " ".join(argv[1:])
      text = self._obj._controller.ShellCommandOutput(cmd)
      self._print(text)
    else:
      sock = self._obj._controller.Connect("shell:")
      # Basically, set up a FileCLI in order to use its interact method.
      cmd = self.clone(CLI.FileCLI)
      cmd._setup(sock)
      try:
        cmd.interact(["interact"])
      finally:
        sock.close()
  interact = shell # alias

  def settings(self, argv):
    """settings
  Start the settings app."""
    self._print(self._obj.StartSettings())

  def gservice(self, argv):
    """gservice <name> [<value>]
  Get or set a GService parameter.
  Some examples:
    gservice gtalk_heartbeat_interval_ms 300000
    gservice gtalk_max_server_heartbeat_time 2400000 """
    argc = len(argv)
    if argc >= 3:
      name = argv[1]
      value = argv[2]
      self._obj.SetGservicesSetting(name, value)
    elif argc == 2:
      name = argv[1]
      self._print(self._obj.GetGservicesSetting(name))
    else:
      raise CLI.CLISyntaxError("Must supply name, or name and value.")



def androidsh(argv):
  """androidsh [-d <index>] [-s <serial_no>] [-?hD] [<scriptfilename>]

  Provides an interactive session to an Android device connected via adb.

  Options:
   -d    = Device index to use (default 1).
   -r    = Device revision: sooner: 0, dream v2: 2, dream v3: 3
   -s    = Device serial number.
   -?    = This help text.
   -D    = Enable debugging.
"""

  serial_no = None
  device_id = 1

  try:
    optlist, longopts, args = getopt.getopt(argv[1:], "?hDd:")
  except getopt.GetoptError:
    print androidsh.__doc__
    return
  for opt, optarg in optlist:
    if opt in ("-?", "-h"):
      print androidsh.__doc__
      return
    elif opt == "-s":
      serial_no = optarg
    elif opt == "-d":
      device_id = int(optarg)
    elif opt == "-D":
      from pycopia import autodebug

  if serial_no is not None:
    dev = devices.GetDevice(serial_no)
  else:
    dev = devices.GetDevice(device_id)

  io = CLI.ConsoleIO()
  ui = CLI.UserInterface(io)
  cmd = AndroidCommands(ui)
  cmd._setup(dev, "%s-%s> " % (dev.build.product, device_id,))
  parser = CLI.CommandParser(cmd, 
        historyfile=os.path.expandvars("$HOME/.hist_androidsh"))
  if args:
    scriptfilename = args[0]
    text = open(scriptfilename).read()
    parser.feed(text)
  else:
    parser.interact()


def adbsh(argv):
  """adbsh [-?hD]

  Provides an interactive session for ADB.

  Options:
   -?    = This help text.
   -D    = Enable debugging.
"""
  try:
    optlist, longopts, args = getopt.getopt(argv[1:], "?hD")
  except getopt.GetoptError:
    print adbsh.__doc__
    return
  for opt, optarg in optlist:
    if opt in ("-?", "-h"):
      print adbsh.__doc__
      return
    elif opt == "-D":
      from pycopia import autodebug

  client = adb.AdbClient()
  io = CLI.ConsoleIO()
  ui = CLI.UserInterface(io)
  cmd = AdbClientCommands(ui)
  cmd._setup(client, "ADB> ")
  parser = CLI.CommandParser(cmd, 
      historyfile=os.path.expandvars("$HOME/.hist_androidsh"))
  parser.interact()


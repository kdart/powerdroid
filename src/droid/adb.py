#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Python client for using android adb.

Provides primitive methods for interacting with or controlling an Android
device over adb (the Android debug interface). This module uses the adb
server's socket protocol directly, and can be used in place of the adb
commandline client.
"""

import os
import zipfile
import struct
import stat
from cStringIO import StringIO

from pycopia import proctools
from pycopia import scheduler
from pycopia import socket
from pycopia import dictlib
from pycopia import timelib
from pycopia import aid

# Will raise an exception if not found.
try:
  ADB = proctools.which("adb")
except proctools.NotFoundError, err:
  raise ImportError, err


class Error(Exception):
  pass

class AdbError(Error):
  pass

class AdbQuit(Error):
  """Signals that the device connection must quit."""


ADB_PORT = 5037

# device states
OFFLINE, BOOTLOADER, DEVICE, HOST, RECOVERY, UNKNOWN = (
  "offline", "bootloader", "device", "host", "recovery", "unknown")

def _MKID(a, b, c, d):
  return ((a) | ((b) << 8) | ((c) << 16) | ((d) << 24))
# x86
ID_STAT = _MKID(ord('S'), ord('T'), ord('A'), ord('T'))
ID_LIST = _MKID(ord('L'), ord('I'), ord('S'), ord('T'))
ID_ULNK = _MKID(ord('U'), ord('L'), ord('N'), ord('K'))
ID_SEND = _MKID(ord('S'), ord('E'), ord('N'), ord('D'))
ID_RECV = _MKID(ord('R'), ord('E'), ord('C'), ord('V'))
ID_DENT = _MKID(ord('D'), ord('E'), ord('N'), ord('T'))
ID_DONE = _MKID(ord('D'), ord('O'), ord('N'), ord('E'))
ID_DATA = _MKID(ord('D'), ord('A'), ord('T'), ord('A'))
ID_OKAY = _MKID(ord('O'), ord('K'), ord('A'), ord('Y'))
ID_FAIL = _MKID(ord('F'), ord('A'), ord('I'), ord('L'))
ID_QUIT = _MKID(ord('Q'), ord('U'), ord('I'), ord('T'))

del _MKID

_SYNCMSG = {
  "id": ("I", struct.calcsize("I")),
  "req": ("II", struct.calcsize("II")),        # id, namelen
  "stat": ("IIII", struct.calcsize("IIII")),   # id, mode, size, time
  "dent": ("IIIII", struct.calcsize("IIIII")), # id, mode, size, time, namelen
  "data": ("II", struct.calcsize("II")),       # id, size
  "status": ("II", struct.calcsize("II")),     # id, msglen
}

SYNC_DATA_MAX = 64 * 1024


def StartServer(logfile=None):
  AdbCommand("start-server", logfile)

def KillServer(logfile=None):
  AdbCommand("kill-server", logfile)

def AdbCommand(cmd, logfile=None):
  """Run device agnostic adb command.

  Used to run commans that control the adb server.
  """
  pm = proctools.get_procmanager()
  proc = pm.spawnpipe("%s %s" % (ADB, cmd), logfile=logfile, merge=0)
  output = proc.read()
  errors = proc.readerr()
  proc.close()
  status = proc.wait()
  return status, output, errors


class AdbClient(object):
  """Python client for the adb server using socket interface."""

  def __init__(self):
    self._adb_version = int(self.HostQuery("host:version"), 16)

  def _Connect(self):
    retries = 3
    while retries:
      try:
        sock = socket.connect_tcp("localhost", ADB_PORT)
      except socket.SocketError:
        StartServer()
        retries -= 1
      else:
        return sock
    else:
      raise AdbError("Could not connect to server.")

  def DoCommand(self, sock, cmd):
    cmd = "%04x%s" % (len(cmd), cmd)
    sock.sendall(cmd)
    try:
      self._CheckStatus(sock)
    except AdbError:
      sock.close()
      raise

  def Connect(self, cmd):
    sock = self._Connect()
    self.DoCommand(sock, cmd)
    return sock

  def HostQuery(self, cmd):
    sock = self._Connect()
    self.DoCommand(sock, cmd)
    size = int(sock.recv(4), 16)
    resp = sock.recv(size)
    sock.close()
    return resp

  def _CheckStatus(self, sock):
    stat = sock.recv(4)
    if stat == "OKAY":
      return True
    elif stat == "FAIL":
      size = int(sock.recv(4), 16)
      val = sock.recv(size)
      raise AdbError(val)
    else:
      raise AdbError("Bad response: %r" % (stat,))

  def GetDevices(self):
    dm = DeviceManager()
    resp = self.HostQuery("host:devices")
    for n, line in enumerate(resp.splitlines()):
      parts = line.split("\t")
      if self._adb_version >= 19:
        device = AdbDeviceClient(n+1, parts[0], parts[1],
            self._adb_version)
      else:
        device = AdbDeviceClient(int(parts[0]), parts[1], parts[2], 
            self._adb_version)
      dm.Add(device)
    return dm

  def GetDevice(self, identifier=1):
    try:
      return self.GetDevices()[identifier]
    except (KeyError, IndexError):
      raise AdbError("Could not get device with identifier %r." % (identifier,))

  def Kill(self):
    sock = self.Connect("host:kill")
    sock.close()


class AdbDeviceClient(AdbClient):
  """ADB Client for a specific device.
  """

  def __init__(self, dev_id, serial_no, state, adb_version):
    self.device_id = dev_id
    self.serial = serial_no
    self.state = state
    self._adb_version = adb_version
    self._build = None

  def Connect(self, cmd):
    if self.state == DEVICE:
      if cmd.startswith("bootloader:"):
        raise AdbError("Sending bootloader command %r in DEVICE state." % (
            cmd,))
      if self._adb_version >= 19:
        transport = "host:transport:%s" % self.serial
      else:
        transport = "host:transport:%d" % self.device_id
    elif self.state == BOOTLOADER:
      transport = "host:transport-bl:%d" % self.device_id
    else:
      raise AdbError("bad device state: %r" % (self.state,))
    sock = self._Connect()
    self.DoCommand(sock, transport)
    self.DoCommand(sock, cmd)
    return sock

  def Command(self, cmd):
    sock = self.Connect(cmd)
    sock.close()

  def __str__(self):
    return "%s\t%s\t%s" % (
        self.device_id, self.serial, self.state)

  def __repr__(self):
    return "%s(%r, %r, %r, %r)" % (self.__class__.__name__,
        self.device_id, self.serial, self.state, self._adb_version)

  def GetBuild(self):
    """Return a dictionary of build information from phone.
    """
    if self._build is None:
      text = self.ShellCommandOutput("cat system/build.prop")
      rv = dictlib.AttrDict()
      for line in text.splitlines():
        if line.startswith("#"):
          continue
        try:
          l, r = line.split("=", 1)
        except ValueError:
          continue
        else:
          rv[l.strip()] = r.strip()
      self._build = rv
    return self._build

  build = property(GetBuild)

#  def GetShell(self, logfile=None):
#    s = self.Connect("shell:")
#    exp = ExpectAdb(s.makefile("w+", 1), prompt="# ", logfile=logfile)
#    exp.send("\n") # sync with prompt
#    exp.wait_for_prompt()
#    return exp

  def ShellCommand(self, cmd):
    sock = self.Connect("shell:%s" % (cmd,))
    sock.recv(4096) # eat any output
    sock.close()

  def ShellCommandOutput(self, cmd):
    io = StringIO()
    self.RunCommand(cmd, io)
    return io.getvalue()

  def RunCommand(self, cmd, stream):
    sock = self.Connect("shell:%s" % (cmd,))
    data = sock.recv(4096)
    while data:
      stream.write(data)
      data = sock.recv(4096)
    sock.close()

  def Remount(self):
    """Remounts the /system partition on the device read-write."""
    sock = self.Connect("remount:")
    sock.recv(4096)
    sock.close()

  def IsRunning(self):
    return self.state == DEVICE

  def IsOffline(self):
    return self.state == OFFLINE

  def IsBootloader(self):
    return self.state == BOOTLOADER

  def GetProduct(self):
    if self._adb_version >= 19:
      return self.HostQuery("host-serial:%s:get-product" % self.serial)
    else:
      return self.HostQuery("host:get-product")

  def GetState(self):
    if self._adb_version >= 19:
      st = self.HostQuery("host-serial:%s:get-state" % self.serial)
    else:
      st = self.HostQuery("host:get-state")
    self.state = st
    return st

  def WaitForBootloader(self):
    sock = self._Connect()
    self.DoCommand(sock, "host:wait-for-bootloader")
    try:
      sock.recv(4) # server blocks until bootloader available
      self.state = BOOTLOADER
    finally:
      sock.close()

  def WaitForDevice(self):
    sock = self._Connect()
    self.DoCommand(sock, "host:wait-for-device")
    try:
      sock.recv(4)
      self.state = DEVICE
    finally:
      sock.close()

  def Reboot(self, bootloader=False):
    if self.state == BOOTLOADER:
      sock = self.Connect("bootloader:reboot")
      sock.close()
    elif self.state == DEVICE:
      if bootloader:
        cmd = "reboot bootloader"
      else:
        cmd = "reboot"
      self.ShellCommand(cmd)

  def UploadData(self, name, data):
    cmd = "bootloader:flash:%s:%s" % (name, len(data))
    sock = self.Connect(cmd)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
    try:
      sock.sendall(data)
      self._CheckStatus(sock)
    finally:
      sock.close()

  def Update(self, filename, wipe=False, flash=False):
    """Perform an adb update."""
    zfile = zipfile.ZipFile(filename)
    try:
      zipproduct = zfile.read("android-product.txt").strip()
    except KeyError: # zipfile reports KeyError if name not in archive.
      zfile.close()
      raise AdbError("Not an android zip file.")
    # Verify product match if device reports it.
    devproduct = self.GetProduct()
    if devproduct:
      if zipproduct != devproduct:
        zfile.close()
        raise AdbError("product mismatch.")
      if devproduct == "sardine":
        self._SoonerUpdate(zfile, wipe, flash)
      elif devproduct == "trout":
        stat, out, errs = self._DreamUpdate(filename, wipe, flash)
        if not stat:
          raise AdbError("%s\n%s\n%s" % (stat, out, errs))
      else:
        raise AdbError("Unsupported product: %r" % (devproduct,))

  def _DreamUpdate(self, filename, wipe, flash):
    cmd = "fastboot %s update %s" % (aid.IF(wipe, "-w", ""), filename,)
    pm = proctools.get_procmanager()
    proc = pm.spawnpipe(cmd)
    output = proc.read()
    errors = proc.readerr()
    proc.close()
    status = proc.wait()
    return status, output, errors

  def _SoonerUpdate(self, zfile, wipe, flash):
    if self.GetState() != BOOTLOADER:
      self.Reboot(bootloader=True)
      retries = 3
      while retries:
        scheduler.sleep(2)
        try:
          self.WaitForBootloader()
        except AdbError: # may or may not get this error first time.
          retries -= 1
        else:
          break
      else:
        raise AdbError("Did not detect bootloader after reboot.")
    else:
      self.WaitForBootloader() # make sure we are truly in bootloader
    if self.GetState() != BOOTLOADER:
      raise AdbError("Did not enter bootloader from update.")
    try:
      for dname, fname in (
            ("recovery", "recovery.img"), 
            ("boot", "boot.img"), 
            ("systemfs", "system.img")):
        data = zfile.read(fname)
        self.UploadData(dname, data)
        scheduler.sleep(2)
      if flash:
        data = zfile.read("userdata.img")
        self.UploadData("userdata", data)
        scheduler.sleep(2)
      elif wipe:
        self.UploadData("eraseuserdata", " ")
        scheduler.sleep(2)
    finally:
      zfile.close()
    self.Reboot()
    retries = 5
    while retries:
      scheduler.sleep(10)
      try:
        self.WaitForDevice()
      except AdbError: # may or may not get this error first time.
        retries -= 1
      else:
        self.GetState()
        break
    else:
      raise AdbError("Did not detect device after update.")

  def RunEventScript(self, script):
    """Perform an event script using this adb instance.

    Args:
      script: an instance of devices.EventScript.
    """
    script.Perform(self)

  def GetLogcatIOHandler(self, stream, args=""):
    sock = self._ConnectLogcat(args)
    return LogcatIOHandler(sock, stream)

  def LogcatFile(self, fname, bufsize=-1, args=""):
    """Spool logcat output to file, in the background.

    Of course this requires USB to be connected.
    """
    sock = self._ConnectLogcat(args)
    proc = proctools.submethod(_LogcatFile, (fname, sock, bufsize))
    sock.close()
    return proc

  def _ConnectLogcat(self, args):
    tags = os.environ.get("ANDROID_LOG_TAGS", "")
    return self.Connect('shell:export ANDROID_LOG_TAGS="%s" ; logcat %s' % (
        tags, args))

  # The following methods are analogs of the adb tool commands.
  def Logcat(self, stream, args=""):
    sock = self._ConnectLogcat(args)
    data = sock.recv(4096)
    try:
      while data:
        stream.write(data)
        data = sock.recv(4096)
    finally:
      sock.close()

  def DumpState(self, stream):
    self.RunCommand("dumpstate -", stream)

  def Buildprop(self, stream):
    self.RunCommand("cat /system/build.prop", stream)

  def DumpSys(self, stream, section=None):
    if section:
      self.RunCommand("dumpsys %s" % section, stream)
    else:
      self.RunCommand("dumpsys", stream)

  def BugReport(self, stream):
    if self._adb_version >= 19:
      self.RunCommand("dumpstate -", stream)
    else:
      self._Separator(stream, "dumpstate")
      self.RunCommand("dumpstate", stream)
      self._Separator(stream, "build.prop")
      self.RunCommand("cat /system/build.prop", stream)
      self._Separator(stream, "dumpsys")
      self.RunCommand("dumpsys", stream)


  @staticmethod
  def _Separator(stream, name):
    stream.write("""
  ========================================================
  == %s
  ========================================================
  """ % name)

  def List(self, path, list_cb, cookie=0):
    """List directory on device.

    Calls list_cb for each directory entry:
      list_cb(mode, size, time, name, cookie)
    """
    sock = self.Connect("sync:")
    sock.write(struct.pack("II", ID_LIST, len(path)))
    sock.write(path)
    fmt, rsize = _SYNCMSG["dent"]
    while 1:
      data = sock.read(rsize)
      rid, mode, size, time, namelen = struct.unpack(fmt, data)
      if rid == ID_DONE:
        break
      if rid != ID_DENT:
        sock.close()
        raise AdbError("ID_DENT not returned for List")
      name = sock.read(namelen)
      list_cb(mode, size, time, name, cookie)
    _SyncQuit(sock)
    sock.close()

  def Push(self, loc, rem, verifyApk=0):
    """Push a file from local system to device."""
    st = os.stat(loc)
    if stat.S_ISREG(st.st_mode):
      sock = self.Connect("sync:")
      mode, fsize, ftime = _SyncReadmode(sock, rem)
      if mode != 0 and stat.S_ISDIR(mode):
        name = os.path.basename(loc)
        rem = "%s/%s" % (rem, name)
      try:
        _SyncSend(sock, loc, rem, st.st_mtime, st.st_mode, verifyApk)
        _SyncQuit(sock)
      finally:
        sock.close()
    else:
      raise AdbError("Push: source is not a regular file.")

  def Pull(self, loc, rem):
    sock = self.Connect("sync:")
    mode, fsize, ftime = _SyncReadmode(sock, rem)
    if mode == 0:
      sock.close()
      raise AdbError("Pull: remote file %r does not exist." % rem)
    if stat.S_ISREG(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
      # Given "loc" variable may be file or directory.
      try:
        lstat = os.stat(loc)
      except OSError:
        lpath, lname = os.path.split(loc)
        os.stat(lpath) # will raise OSError again if directory also does not
                       # exist.
      else: # some file or directory exists.
        # If directory, append remote name and use that as local name.
        # Otherwise use local name as-is.
        if stat.S_ISDIR(lstat.st_mode):
          rpath, rname = os.path.split(rem)
          loc = os.path.join(loc, rname)
      try:
        _SyncRecv(sock, loc, rem)
        _SyncQuit(sock)
      finally:
        sock.close()
    else: # TODO(dart) directory recursion
      raise AdbError("Pull: remote file %r is not a file." % rem)


def _SyncSend(sock, lpath, rpath, mtime, mode, verifyApk=0):
  fo = open(lpath)
  s = "%s,%d" % (rpath, mode)
  sock.write(struct.pack("II", ID_SEND, len(s)))
  sock.write(s)
  data = fo.read(SYNC_DATA_MAX)
  try:
    while data:
      sock.write(struct.pack("II", ID_DATA, len(data)))
      sock.write(data)
      data = fo.read(SYNC_DATA_MAX)
  finally:
    fo.close()
  fmt, sizeof = _SYNCMSG["data"]
  sock.write(struct.pack(fmt, ID_DONE, mtime))
  rid, msglen = _SyncReadMessage(sock, "status")
  if rid != ID_OKAY:
    if rid == ID_FAIL:
      reason = sock.read(msglen)
      raise AdbError("Send error: %s" % (reason,))
    else:
      raise AdbError("Send error: unknown reason")


def _SyncRecv(sock, lpath, rpath):
  datafmt, datasize = _SYNCMSG["data"]
  sock.write(struct.pack("II", ID_RECV, len(rpath)))
  sock.write(rpath)
  rid, size = struct.unpack(datafmt, sock.read(datasize))
  if rid == ID_DATA or rid == ID_DONE:
    try:
      os.unlink(lpath)
      os.makedirs(os.path.split(lpath)[0])
    except OSError: # most likely exists
      pass
    outf = open(lpath, "w")
    try:
      _Copy(sock, outf, size)
      while 1:
        rid, size = struct.unpack(datafmt, sock.read(datasize))
        if rid == ID_DONE:
          break
        if rid != ID_DATA:
          try:
            outf.close()
            os.unlink(lpath)
          except OSError:
            pass
          if rid == ID_FAIL:
            reason = sock.read(size)
          else:
            reason = "unknown reason (%ld)" % (rid,)
          raise AdbError("Recv error: %s" % (reason,))
        else:
          _Copy(sock, outf, size)
    finally:
      outf.close()


def _Copy(sock, outf, size):
  while size > 0:
    data = sock.read(size)
    outf.write(data)
    size -= len(data)


def _SyncQuit(sock):
  sock.write(struct.pack("II", ID_QUIT, 0))


def _SyncReadMessage(sock, msgtype):
  fmt, sizeof = _SYNCMSG[msgtype]
  return struct.unpack(fmt, sock.read(sizeof))


def _SyncReadmode(sock, remotepath):
  sock.write(struct.pack("II", ID_STAT, len(remotepath)))
  sock.write(remotepath)
  rid, mode, size, time = _SyncReadMessage(sock, "stat")
  if rid != ID_STAT:
    sock.close()
    raise AdbError("ID_STAT not returned.")
  return mode, size, time


def _LogcatFile(fname, sock, bufsize):
  fo = open(fname, "w", bufsize)
  try:
    while 1:
      data = sock.recv(4096)
      fo.write(data)
  finally:
    sock.close()
    fo.close()


class LogcatIOHandler(object):
  def __init__(self, sock, stream):
    self._sock = sock
    self._file = stream

  def fileno(self):
    return self._sock.fileno()

  def readable(self):
    return True

  def writable(self):
    return False

  def priority(self):
    return False

  def read_handler(self):
    data = self._sock.recv(4096)
    self._file.write(data)

  def write_handler(self):
    pass

  def pri_handler(self):
    pass

  def hangup_handler(self):
    pass

  def error_handler(self, ex, val, tb):
    print >>sys.stderr, "LogcatHandler error: %s (%s)" % (ex, val)


class EventReceiver(object):
  def __init__(self, sock):
    self._sock = sock

  def __call__(self):
    last_timestamp = timelib.now()
    data = sock.recv(20)
    try:
      while data:
        timestamp, evtype, evcode, evvalue = _ConvertEvent(data)
        if handler(timestamp - last_timestamp, evtype, evcode, evvalue) is None:
          last_timestamp = timestamp
        data = sock.recv(20)
    finally:
      sock.close()


def _ConvertEvent(evtext):
  # converts "0001 006a 00000001" to event type, code, and value. Also
  # supplies a local time stamp.
  evtypetext, evcodetext, evvaluetext = evtext.split()
  return (timelib.now(), int(evtypetext, 16), int(evcodetext, 16), 
      int(evvaluetext, 16))


class DeviceManager(object):
  """Manage and select from multiple devices."""
  def __init__(self):
    self.Clear()

  def Clear(self):
    self._device_map = {}
    self._serial_map = {}

  def Add(self, device):
    self._device_map[device.device_id] = device
    self._serial_map[device.serial] = device

  def Remove(self, device):
    del self._device_map[device.device_id]
    del self._serial_map[device.serial]

  def GetSerialNumbers(self):
    return self._serial_map.keys()

  def __str__(self):
    s = ["List of devices attached:"]
    s.append("seq\tserial  \tstate")
    for dev in self._device_map.values():
      s.append(str(dev))
    return "\n".join(s)

  def GetById(self, dev_id):
    return self._device_map[dev_id]

  def GetBySerial(self, serno):
    return self._serial_map[serno]

  def Get(self, dev_or_serial):
    if isinstance(dev_or_serial, int):
      return self._device_map[dev_or_serial]
    else: # serno is a string
      return self._serial_map[dev_or_serial]

  def __getitem__(self, dev_or_serial):
    return self.Get(dev_or_serial)



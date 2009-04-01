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



"""Base support for intsruments with RS-232 serial interfaces.

"""

__author__ = 'dart@google.com (Keith Dart)'



from pycopia import expect
from pycopia import tty

from droid.instruments import core


class Error(Exception):
  pass

class CommandError(Error):
  pass

class ExecutionError(Error):
  pass


class SerialInstrument(object):
  """Base class for instruments that interface with RS-232 ports.
  """
  _exp = None

  def __init__(self, devspec, logfile=None, **kwargs):
    fo = tty.SerialPort(devspec.port)
    fo.set_serial(devspec.serial)
    self._timeout = devspec.get("timeout", 30.0)
    self._exp = expect.Expect(fo, prompt=devspec.prompt,
        timeout=self._timeout,
        logfile=logfile)
    self.Initialize(devspec, **kwargs)

  def __del__(self):
    self.close()

  def close(self):
    if self._exp:
      self._exp.close()
      self._exp = None

  def _get_timeout(self):
    return self._timeout

  def _set_timeout(self,  value):
    self._timeout = float(value)

  timeout = property(_get_timeout, _set_timeout)

  def Initialize(self, devspec, **kwargs):
    pass

  def Prepare(self, measurecontext):
    return 0.20 # default for medium 

  def read(self, len=4096):
    return self._exp.read(len, timeout=self._timeout)
  readbin = read

  def writebin(self, string, length):
    self.write(string)

  def write(self, string):
    self._exp.write(string)
    self._exp.write("\n")
    return self._wait_for_prompt()

  def ask(self, string):
    self._exp.write(string)
    self._exp.write("\n")
    return self._wait_for_prompt()

  # gpib compatible methods
  def wait(self):
    pass

  def clear(self):
    self._exp.write(chr(3)) # ^C
    self._wait_for_prompt()

  def _wait_for_prompt(self):
    mo = self._exp.expect("([=?!])>\r\n", expect.REGEX)
    if mo:
      indicator = mo.group(1)
      if indicator == "=":
        return mo.string[:-6]
      if indicator == "?":
        raise CommandError("Command not understood")
      if indicator == "!":
        raise ExecutionError("Command could not be executed.")

  def poll(self):
    """Serial polls the device. The status byte is returned."""
    return 0

  def trigger(self):
    """Sends a GET (group execute trigger) command to the device."""
    pass

  def identify(self):
    return core.Identity(self.ask("*IDN?"))

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

  def GetVoltageHeadings(self):
    return ()

  def GetConfig(self, option):
    return None


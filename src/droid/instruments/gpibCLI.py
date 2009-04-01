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



"""Command tool for talking to GPIB instruments.

Useful for experimenting with and learning the devices command set.
"""

__author__ = 'dart@google.com (Keith Dart)'

import os

from pycopia import getopt
from pycopia import CLI

from droid.measure import core as measurecore
from droid.instruments import core
from droid.instruments import gpib


class TopLevel(CLI.BaseCommands):

  def _reset_scopes(self):
    eq = core.GENERICMAP.keys() + self._obj.keys()
    eq.sort()
    self.add_completion_scope("use", eq)
    self.add_completion_scope("clear", eq)
    self.add_completion_scope("reset", eq)

  def use(self, argv):
    """use [-v] <devicename>
  Select a device to interact with.

  -v = use verbose logging"""
    lf = None
    opts, longopts, args = self.getopt(argv, "v")
    for opt, arg in opts:
      if opt == "-v":
        lf = self._ui._io
    devname = args[0]
    cmd = self.clone(core.GetCommandClass(devname))
    inst = core.GetInstrument(devname, logfile=lf)
    errs = inst.Errors()
    if errs:
      self._print("Pre-existing errors:")
      for err in errs:
        self._print("  ", err)
    if inst.GetConfig(gpib.SC):
      cmd._setup(inst, "%%I%s%%N(CiC)> " % (devname, ))
    else:
      ident = inst.identify()
      cmd._setup(inst, "%%I%s%%N(%s)> " % (inst._configname, ident.model))
    raise CLI.NewCommand, cmd

  def ls(self, argv):
    """ls
  Show available devices."""
    self._print_list(self._obj.keys())

  def reset(self, argv):
    """reset <name>
  Reset the device."""
    name = argv[1]
    inst = core.GetInstrument(devname)
    try:
      inst.Reset()
    finally:
      inst.close()

  def clear(self, argv):
    """clear <name>
  Clear the GPIB bus for the named device."""
    inst = core.GetInstrument(argv[1])
    try:
      inst.clear()
    finally:
      inst.close()


class GpibCLI(CLI.GenericCLI):
  def save(self, argv):
    """save <filename>
  Save the value from the last operation into a file. """
    filename = argv[1]
    val = self._environ["_"]
    if val is not None:
      val = str(val)
      if self._ui.yes_no("Write %r... to %r?" % (val[:10], filename)):
        fo = open(filename, "w")
        try:
          fo.write(val)
        finally:
          fo.close()
    else:
      self._ui.error("Sorry, no value to write.")



class GenericController(GpibCLI):
  pass


class GenericInstrument(GpibCLI):

  def _reset_scopes(self):
    super(GenericInstrument, self)._reset_scopes()
    self.add_completion_scope("timeout", map(str, self._obj.TIMEOUTS))

  def reset(self, argv):
    """reset
  Resets the device to default values."""
    self._obj.Reset()

  def _ask(self, string):
    try:
      res = self._obj.ask(string)
    except gpib.GpibError, err:
      self._ui.error("Error: %s" %  (err,))
      res = None
    else:
      self._print(res)
    self._check_errors()
    return res

  def ask(self, argv):
    """ask <cmd>
  Send a qeury to the device, print the return value."""
    return self._ask(" ".join(argv[1:]))

  def identify(self, argv):
    """identify
  Return the identity string."""
    self._print(self._obj.identify())

  def write(self, argv):
    """write <data>
  Write the arguments to the device."""
    self._obj.write(" ".join(argv[1:]))
    self._check_errors()

  def read(self, argv):
    """read
  Read from the device. May block."""
    self._print(self._obj.read())

  def errors(self, argv):
    """errors
  Display error queue (also drains queue)."""
    resp = self._obj.Errors()
    if resp:
      self._print("Errors:")
      for err in resp:
        self._print("  ", err)
    else:
      self._print("No errors.")

  def clear(self, argv):
    """clear
  Clears the device."""
    self._obj.clear()
    self._check_errors()

  def poll(self, argv):
    """poll
  Polls the device."""
    self._print(self._obj.poll())
    self._check_errors()

  def trigger(self, argv):
    """trigger
  Triggers the device."""
    self._obj.trigger()
    self._check_errors()

  def wait(self, argv):
    """wait
  Waits for SRQ."""
    self._obj.wait()
    self._check_errors()

  def _check_errors(self):
    resp = self._obj.Errors()
    if resp:
      self._print(self._format("%RError:%N"))
      for err in resp:
        self._print("  ", err)

  def timeout(self, argv):
    """timeout [-l] [<Tval>]
  Set the device command timeout value to a pre-defined value.  
  If not supplied then print the current value.
  Option -l lists the available values."""
    opts, longopts, args = self.getopt(argv, "l")
    for opt, arg in opts:
      if opt == "-l":
        self._print_list(self._obj.TIMEOUTS)
        return
    if len(args) > 0:
      tstr = args[0]
      if tstr.startswith("T"):
        try:
          tval = getattr(self._obj, args[0])
        except AttributeError:
          self._ui.error("No such time value. Use one of the following:")
          self._print_list(self._obj.TIMEOUTS)
        else:
          self._obj.timeout = tval
      else:
        self._ui.error("Not a valid time value. Use one of the following.")
        self._print_list(self._obj.TIMEOUTS)
    else:
      self._print("Current timeout: %s" % self._obj.timeout)

  def options(self, argv):
    """options
  Print the list of device options."""
    self._print_list(self._obj.Options())

  def SRE(self, argv):
    """SRE [<newval>]
  Get, or set, the service request enable bit."""
    if len(argv) > 1:
      self._obj.SRE = argv[1]
    else:
      self._print(self._obj.SRE)

  def STB(self, argv):
    """STB
  Print the status byte."""
    self._print(self._obj.STB)

  def prepare(self, argv):
    """prepare [--longopts=x ...]
  Prepare the instrument for measuring using the global measurement
  context. Modify the context with long-style arguments."""
    opts, longopts, args = self.getopt(argv, "")
    # instrumentshell sets up environment with measurement context.
    env = self._environ.copy() 
    env.evalupdate(longopts)
    return self._obj.Prepare(env)


def instrumentshell(argv):
  """pdish [-?rg]

  Provides an interactive session to the GPIB bus.

  Options:
   -?    = This help text.
   -g    = used paged output (like 'more').
   -d    = Enable debugging.

"""
  paged = False

  try:
    optlist, longopts, args = getopt.getopt(argv[1:], "?gd")
  except GetoptError:
      print instrumentshell.__doc__
      return
  for opt, val in optlist:
    if opt == "-?":
      print instrumentshell.__doc__
      return
    elif opt == "-g":
      paged = True
    elif opt == "-d":
      from pycopia import autodebug

  if paged:
    from pycopia import tty
    io = tty.PagedIO()
  else:
    io = CLI.ConsoleIO()

  env = measurecore.MeasurementContext()
  env.evalupdate(longopts)
  ui = CLI.UserInterface(io, env)

  conf = core.INSTRUMENTS # TODO(dart) use real config
  cmd = TopLevel(ui)
  cmd._setup(conf, "pdish> ")

  parser = CLI.CommandParser(cmd, 
        historyfile=os.path.expandvars("$HOME/.hist_pdish"))

  parser.interact()


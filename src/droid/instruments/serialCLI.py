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



"""COmmand objects for serial instruments.

"""

__author__ = 'dart@google.com (Keith Dart)'




import os

from pycopia import CLI


class SerialInstrumentCLI(CLI.GenericCLI):

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

  def ask(self, argv):
    """ask <query>
  Send a qeury to the device, print the return value."""
    resp = self._obj.ask(" ".join(argv[1:]))
    self._print(resp)
    return resp

  def identify(self, argv):
    """identify
  Return the identity string."""
    self._print(self._obj.identify())

  def write(self, argv):
    """write <data>
  Write the arguments to the device."""
    self._obj.write(" ".join(argv[1:]))

  def read(self, argv):
    """read
  Read from the device. May block."""
    self._print(self._obj.read())

  def clear(self, argv):
    """clear
  Clears the device."""
    self._obj.clear()

  def trigger(self, argv):
    """trigger
  Triggers the device."""
    self._obj.trigger()




#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#

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


"""Defines the equipment and environment model and wrappers.

TODO(dart) abstract and editable lab model.
"""


from droid.instruments import core
from droid import devices
from droid.testcaselib import sync



class EnvironmentRuntime(object):
  """Runtime wrapper for a Environment data.

  This object will be created and returned by the
  storage.Storage.RootStorage object.
  """

  def __init__(self, config):
    # TODO(dart) Fix hard-coded environment and add better Device objects.
    self._instrumentcache = {}
    self._dutid = config.get("deviceid", 1)
    self.mailrate = config.get("mailrate", 1.0) # rate in msg/min, default 1/min
    self.account = config.account
    self.password = config.account_password
    self.APNINFO = devices.APNInfo(
      name="TestSIM",
      mcc=1,
      mnc=12, # correct value is 1, but this is needed to compensate for a bug
      accesspointname="internet",
      user="*",
      password="*",
      server="*",
      proxy="",
      port="",
      mmsc="",
      iscurrent=1)

  def _GetDUT(self):
    try:
      dut = self._instrumentcache["DUT"]
    except KeyError:
      dut = devices.GetDevice(self._dutid)
      if dut is None: # not available 
        return None
      if dut.account is None:
        dut.SetAccount(self.account, self.password)
      self._instrumentcache["DUT"] = dut
    return dut

  def _GetInstrument(self, name):
    try:
      return self._instrumentcache[name]
    except KeyError:
      inst = core.GetInstrument(name)
      self._instrumentcache[name] = inst
      return inst

  def _GetMailer(self):
    try:
      return self._instrumentcache["mailer"]
    except KeyError:
      inst = sync.MessageMailer(self.account, 10, self.mailrate)
      self._instrumentcache["mailer"] = inst
      return inst

  def GetInstrument(self, name):
    return core.GetInstrument(name)

  DUT = property(lambda self: self._GetDUT())
  powersupply = property(lambda self: self._GetInstrument("ps1"))
  testset = property(lambda self: self._GetInstrument("ag8960"))
  afgenerator = property(lambda self: self._GetInstrument("ag8960_afgen"))
  afanalyzer = property(lambda self: self._GetInstrument("ag8960_afana"))
  multitonegen = property(lambda self: self._GetInstrument("ag8960_mtgen"))
  multitoneana = property(lambda self: self._GetInstrument("ag8960_mtana"))
  bttestset = property(lambda self: self._GetInstrument("n4010a"))
  btafgenerator = property(lambda self: self._GetInstrument("n4010a_afgen"))
  btafanalyzer = property(lambda self: self._GetInstrument("n4010a_afana"))
  multimeter = property(lambda self: self._GetInstrument("fluke45"))
  voltmeter = property(lambda self: self._GetInstrument("fluke45"))
  psdvm = property(lambda self: self._GetInstrument("ps1dvm"))
  mailer = property(lambda self: self._GetMailer())


#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Defines the equipment and environment model and wrappers.

TODO(dart) abstract and editable lab model.
"""


from droid.instruments import core
from droid import devices
from droid.testcaselib import sync



class EnvironmentRuntime(object):
  """Runtime wrapper for a Environment data.

  This object will be created and returned by the
  storage.Storage.RootStorage object. It is the "environment" attribute.
  It may contain information or mappings for the partiular environment
  that is in use. Currently, it is always the same, but may in the future
  change according the the "environmentname" config variable.
  """

  def __init__(self, config):
    # TODO(dart) Fix hard-coded environment and add better Device objects.
    self._dutid = config.get("deviceid", 1)
    self._DUT = None
    self._mailer = None
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
    if self._DUT is not None:
      return self._DUT
    dut = devices.GetDevice(self._dutid)
    if dut is None: # not available 
      return None
    if dut.account is None:
      dut.SetAccount(self.account, self.password)
    self._DUT = dut
    return dut

  def _DelDUT(self):
    self._DUT = None

  def _GetMailer(self):
    if self._mailer is not None:
      return self._mailer
    inst = sync.MessageMailer(self.account, 10, self.mailrate)
    self._mailer = inst
    return inst

  def GetInstrument(self, name):
    return core.GetInstrument(name)

  def Clear(self):
    core.ClearInstruments()

  def __getattr__(self, name):
    try:
      return self.GetInstrument(name)
    except core.NoSuchDevice, name:
      raise AttributeError("No device: %r" % (name,))

  # special attributes
  DUT = property(_GetDUT, None, _DelDUT)
  mailer = property(_GetMailer)

#  def _GetInstrument(self, name):
#    try:
#      return self._instrumentcache[name]
#    except KeyError:
#      inst = core.GetInstrument(name)
#      self._instrumentcache[name] = inst
#      return inst


#  powersupply = property(lambda self: self._GetInstrument("powersupply"))
#  testset = property(lambda self: self._GetInstrument("ag8960"))
#  cdmatestset = property(lambda self: self._GetInstrument("ag8960_cdma"))
#  afgenerator = property(lambda self: self._GetInstrument("ag8960_afgen"))
#  afanalyzer = property(lambda self: self._GetInstrument("ag8960_afana"))
#  multitonegen = property(lambda self: self._GetInstrument("ag8960_mtgen"))
#  multitoneana = property(lambda self: self._GetInstrument("ag8960_mtana"))
#  bttestset = property(lambda self: self._GetInstrument("n4010a"))
#  btafgenerator = property(lambda self: self._GetInstrument("n4010a_afgen"))
#  btafanalyzer = property(lambda self: self._GetInstrument("n4010a_afana"))
#  multimeter = property(lambda self: self._GetInstrument("fluke45"))
#  voltmeter = property(lambda self: self._GetInstrument("fluke45"))
#  currentmeter = property(lambda self: self._GetInstrument("fluke45"))
#  psdvm = property(lambda self: self._GetInstrument("ps1dvm"))
#  mstxpower = property(lambda self: self._GetInstrument("ag8960_mstxpower"))
#  modem = property(lambda self: self._GetInstrument("modem"))


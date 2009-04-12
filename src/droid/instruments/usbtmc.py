#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright 2006 Google Inc. All Rights Reserved.

"""Interface to USBTMC devices.

http://www.home.agilent.com/upload/cmc_upload/All/usbtmc.html

"""

import os
import fcntl
import struct


DEVBASEPATH = "/dev/usbtmc%d"

class UsbtmcAttribute(object):
  STRUCT = "ii"

  def __init__(self):
    self.attribute = None
    self.value = None


class UsbtmcDevCapabilities(object):
  STRUCT  = "cccc"

  def __init__(self):
    self.interface_capabilities = None
    self.device_capabilities = None
    self.usb488_interface_capabilities = None
    self.usb488_device_capabilities = None



class USBTMCDevice(object):
  def __init__(self, devspec, **kwargs):
    if devspec is not None:
      self._fd = None  # XXX
      #self._set_timeout(T3s)
      self.Initialize(devspec, **kwargs)
    else:
      self._id = None


  def Initialize(self, devspec, **kwargs):
    pass


def GetInstrument(name, devspec):
  pass


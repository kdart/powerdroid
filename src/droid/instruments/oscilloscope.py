#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright Google Inc. All Rights Reserved.

"""Oscilloscope objects.

"""

from droid.instruments import core
from droid.instruments import usbtmc



class TekDPO4104Oscilloscope(usbtmc.USBTMCDevice, core.Oscilloscope):
  pass

#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright 2007 The Android Open Source Project

"""Plotting handlers.

"""

__author__ = 'dart@google.com (Keith Dart)'


import os
import glob

from pycopia.WWW import json


HOSTNAME = os.uname()[1]

def testing(*args, **kwargs):
  return args, kwargs

def listing():
  return glob.glob("/var/www/%s/media/images/charts/*.png" % HOSTNAME)

def powerprofile():
  pass


_EXPORTED = [testing, listing]

handler = json.JSONDispatcher(_EXPORTED)

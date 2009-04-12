#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Interfaces to router devices.

"""

__author__ = 'dart@google.com (Keith Dart)'


from droid.instruments import core

from pycopia import sshlib

class Router(object):
  pass


class WifiRouter(Router):
  pass


class WRTSL54GS(WifiRouter):
  """Linksys router with openwrt."""
  def __init__(self, context):
    pass



if __name__ == "__main__":
  pass


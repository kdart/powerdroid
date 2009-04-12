#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Various kinds of alarms and alerts to get a user's attention are here.
"""

__author__ = 'dart@google.com (Keith Dart)'


class Alarm(object):

  def On(self):
    raise NotImplementedError

  def Off(self):
    raise NotImplementedError


class EmailAlarm(Alarm):
  pass


class ConsoleAlarm(Alarm):
  pass



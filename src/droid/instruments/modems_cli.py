#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Command line interface to oscilloscopes.

"""



from droid.instruments import gpibCLI


class ModemsCLI(gpibCLI.GenericInstrument):

  def _reset_scopes(self):
    pass

  def dial(self, argv):
    """dial <number>
  Dial the number in voice mode."""
    resp = self._obj.Dial(argv[1])
    self._print(resp)

  def hangup(self, argv):
    """hangup
  Hangup a call."""
    resp = self._obj.Hangup()
    self._print(resp)

  def answer(self, argv):
    """answer
  Answer a call."""
    resp = self._obj.Answer()
    self._print(resp)

  def readq(self, argv):
    """readq
  Read only what is in the input queue."""
    resp = self._obj.readq()
    self._print(resp)

  def calltime(self, argv):
    """calltime
  Show the time of last call, in seconds."""
    resp = self._obj.GetLastCallTime()
    self._print(resp)


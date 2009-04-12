#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Measurement controllers for Radio test sets, such as the Agilent 8960.
"""


from droid.measure import core
from droid.instruments import gpib
from droid.reports import core as reportcore


class ToggleRFOutput(core.BaseMeasurer):
  """Toggle the RF output state of the testset. 

  This controls what the DUT sees as "next to a cell" and "can't see a
  cell".
  """
  def __init__(self, ctx):
    super(ToggleRFOutput, self).__init__(ctx)
    self._testset = ctx.environment.testset
    self.datafile = reportcore.GetDatafile(ctx)

  def Initialize(self):
    self.datafile.Initialize()
    self.datafile.SetColumns("timestamp (s)", "RFOutputState (b)")
    self._testset.ClearErrors()
    self._outputstate = self._testset.GetOutputState()

  def Finalize(self):
    self.datafile.Finalize()
    self._testset.ClearErrors()
    self._testset.SetOutputState(True)

  def __call__(self, timestamp, lastvalue):
    self._outputstate = not self._outputstate
    # The testset will also complain about the DUT not responding to
    # immediate assignments (protocol layer is independent of output state)
    # That is expected, so just ignore those errors.
    try:
      self._testset.SetOutputState(self._outputstate)
    except gpib.GpibError:
      pass
    self.datafile.WriteRecord(timestamp, int(self._outputstate))
    return lastvalue


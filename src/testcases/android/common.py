#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#
# Copyright The Android Open Source Project
#
# Note that docstrings are in RST format:
# <http://docutils.sourceforge.net/rst.html>.


"""
Common tests
------------

Common tests of a utility nature.
"""

__version__ = "$Revision$"

import os

from droid.qa import core
from droid.storage import datafile

from testcases.android import interactive
from testcases.android import measurements


class DroidBaseTest(interactive.AndroidInteractiveMixin, 
        measurements.MeasurementsMixin, 
        core.Test):

  def Initialize(self):
    self.config.datafilename = "/var/tmp/droid_measure.dat"

  # Always get a bug report when not in debug mode.
  def Finalize(self, result):
    cf = self.config
    if not cf.flags.DEBUG:
      cf.logfile.note(self.test_name)
      cf.logfile.note(str(cf.environment.DUT))
      self.Info("Collecting bug report.")
      cf.environment.DUT.BugReport(cf.logfile)


class DroidBaseSuite(core.TestSuite):

  def Initialize(self):
    cf = self.config
    cf.environment.testset.ResetCounters()
    cf.startipcounters = cf.environment.testset.GetIPCounters()
    if not cf.flags.DEBUG:
      fpdir = datafile.GetDirectoryName(cf)
      datafile.MakeDataDir(fpdir)

  def Finalize(self):
    cf = self.config
    if cf.environment.DUT.build:
      datadir = datafile.GetDirectoryName(self.config)
      os.symlink(
          cf.resultsdir, os.path.join(datadir, os.path.basename(cf.resultsdir)))


### utility test cases. ###

class DeviceSetup(DroidBaseTest):
  """
Purpose
+++++++

This is a utility test case that does the initial setup of an Android
deviced connected to a power supply.

Pass criteria
+++++++++++++

Device and environment setup completes without throwing an exception.

Start Condition
+++++++++++++++

None.

End Condition
+++++++++++++

Device is powered on. It also has sync featured turned on, phone is
inactive (hung up), no audio signal is being applies. 

Reference
+++++++++

None

Prerequisites
+++++++++++++

None

Procedure
+++++++++

- Power cycle the DUT.
- Connect DUT to USB controller.
- Reset and prepare test equipment.
- Power on the device, or optionally reboot it.
- Check that USB host can see device, and get build information.
- Optionally enabled bluetooth and prepare test equipment.
- Update the local DUT object settngs and condition state from data
  available on the DUT.

"""

  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT is None:
      raise core.TestSuiteAbort("Could not get DUT")
    if cf.get("skipsetup", False):
      DUT.UpdateAllStates()
      return self.Passed("Environment set up skipped.")

    cf.environment.powersupply.Prepare(cf)
    self.Sleep(2)
    cf.environment.testset.Prepare(cf)
    self.Info("Radio profile: %s" % (cf.testsets.profile,))
    self.Info("Network: %s (simulated)" % (cf.SIM,))

    # Disables checkin, or not. Default to what user experiences.
    if cf.get("blockcheckin", False):
      self.Info("Not allowing checkin.")
      DUT.OverrideGserviceSetting("url:block_checkin", 
          "https://android.clients.google.com/checkin block")
      self.Sleep(5) # give DUT time to store above

    if cf.get("doreboot", False):
      self.RebootDevice()
    else:
      self.PowerCycle()
      self.PowerOnDevice()

    self.Info("\nProduct: %s\nType: %s\nBranch: %s\nBuild id: %s\n" % (
        DUT.build.product, 
        DUT.build.type, 
        DUT.build.branch, 
        DUT.build.id))

    if cf.bttestsets.use:
      cf.bttestsets.btaddress = DUT.btaddress
      self.Info("Using bluetooth with address %s." % (DUT.btaddress,))
      cf.environment.bttestset.Prepare(cf)
      self.EnableBluetooth()
    else:
      self.UplinkAudioOff()
    self.DownlinkAudioOff()
    DUT.UpdateAllStates()
    DUT.CallInactive()
    if cf.get("needpdp", True):
      self.WaitForPDP()
    return self.Passed("Environment set up.")


class DeviceUpdate(DroidBaseTest):
  """
Purpose
+++++++

Utility test to update the DUT software image.

Pass criteria
+++++++++++++

Software is updated to requested image.

Start Condition
+++++++++++++++

An active ADB connection.

End Condition
+++++++++++++

DUT has image specifed by filename parameter.

Reference
+++++++++

None

Prerequisites
+++++++++++++

None

Parameters
++++++++++

None

Configurables
+++++++++++++

zipfilename: Full path to zip file with new Android build.
wipe: Boolean flag that indicates whether or not to wipe the data
    partition.
flash: Boolean flag that indicates whether or not to flash the data
    partition.

Procedure
+++++++++

- Perform device update, report results.

"""

  def Execute(self):
    cf = self.config
    env = cf.environment
    zipfilename = cf.get("zipfilename", None)
    if not zipfilename:
      return self.Incomplete("No zipfilename configuration supplied.")
    self.Info("Connecting to device.")
    self.ConnectDevice()
    img_pos = zipfilename.find("img")
    if img_pos < 0 or not zipfilename.endswith(".zip"):
      return self.Incomplete("Not an image zip file?")
    zipbuildname = zipfilename[img_pos + 4: -4]
    self.Info("Starting update with %r." % (zipfilename,))
    if env.DUT.IsRunning():
      self.Info("Rebooting to bootloader.")
      env.DUT.Reboot(bootloader=True)
      self.Sleep(60)
    self.Info("Updating...")
    status, output, errors = env.DUT.UpdateSoftware(zipfilename, 
        cf.get("wipe", True), cf.get("flash", False))
    if status:
      del env.DUT.build # remove old build information from DUT.
      self.Info(output)
      self.Sleep(20)
      env.DUT.ActivateUSB()
      self.Sleep(10)
      self.WaitForRuntime()
      self.assertEqual(env.DUT.build.id.rsplit("-", 1)[0], # may have "-INSECURE"
          zipbuildname, "Not updated.")
      self.Info("Adding testset APN info: %r." % (env.APNINFO.name,))
      env.DUT.UpdateAPN(env.APNINFO)
      self.Info("Setting bluetooth name to: %r." % (env.DUT.BLUETOOTHNAME,))
      env.DUT.SetProp("net.bt.name", env.DUT.BLUETOOTHNAME)
      fpdir = datafile.GetDirectoryName(self.config)
      self.Info("Making data directory: %r" % fpdir)
      datafile.MakeDataDir(fpdir)
      return self.Passed("Software updated to %r." % (env.DUT.build.id,))
    else:
      self.Diagnostic(output)
      self.Diagnostic(errors)
      return self.Failed("fastboot error: %s" % (status,))


class SetupSuite(DroidBaseSuite):
  pass


# This suite is mostly just for self-testing.
def GetSuite(conf):
  suite = SetupSuite(conf)
  suite.AddTest(DeviceSetup)
  return suite

def Run(conf):
  suite = GetSuite(conf)
  suite()


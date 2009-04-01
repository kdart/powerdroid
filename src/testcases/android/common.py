#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab

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


#
# Note that docstrings are in RST format:
# <http://docutils.sourceforge.net/rst.html>.


"""
Common tests
------------

Common tests of a utility nature.
"""

__version__ = "$Revision$"


from droid.qa import core
from droid.storage import datafile

from testcases.android import interactive


class DeviceSetup(core.Test, interactive.AndroidInteractiveMixin):
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

Device is powered on. It also has sync featured turned off, phone is
inactive (hung up), no audio signal is being applies.

Reference
+++++++++

None

Prerequisites
+++++++++++++

None

Procedure
+++++++++

- Connect DUT to USB controller.
- Reset and set up test equipment.
- Power on the device, or optionally reboot it.
- Check that USB host can see device, and get build information.
- Optionally fetch bluetooth address.

"""

  def Execute(self):
    cf = self.config
    cf.environment.testset.Prepare(cf)
    self.Info("Radio profile: %s" % (cf.testsets.profile,))
    if cf.get("doreboot", False):
      self.RebootDevice()
    else:
      self.PowerCycle()
      self.PowerOnDevice()
    DUT = cf.environment.DUT
    self.Info("\nProduct: %s\nType: %s\nBuild id: %s\n" % (
        DUT.build.product, 
        DUT.build.type, 
        DUT.build.id))
    if cf.bttestsets.use:
      cf.bttestsets.btaddress = DUT.btaddress
      self.Info("Using bluetooth with address %s." % (DUT.btaddress,))
      cf.environment.bttestset.Prepare(cf)
      self.EnableBluetooth()
    self.ExternalAudioOff()
    DUT.CallInactive()
    DUT.XMPPOn()
    DUT.SyncingOn()
    return self.Passed("Environment set up.")


class DeviceReport(core.Test, interactive.AndroidInteractiveMixin):
  """
Purpose
+++++++

Utility test to fetch a debug report from DUT.

Pass criteria
+++++++++++++

None

Start Condition
+++++++++++++++

None.

End Condition
+++++++++++++

No change.

Reference
+++++++++

None

Prerequisites
+++++++++++++

DeviceSetup

Procedure
+++++++++

- Fetch debug report from DUT and write it to the log file.

"""

  def Execute(self):
    cf = self.config
    self.Info("Collecting bug report.")
    self.ConnectDevice()
    cf.environment.DUT.ActivateUSB()
    cf.environment.DUT.BugReport(cf.logfile)
    return self.Passed("Bug report written to log file.")


# TODO(dart) remove this once auto-insertion of prereqs is added
core.InsertOptions(DeviceReport)
DeviceReport.OPTIONS.prerequisites = [
    core.PreReq("testcases.android.common.DeviceSetup"),
  ]


class DeviceUpdate(core.Test, interactive.AndroidInteractiveMixin):
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
      self.Info("Waiting for bootup...")
      self.Sleep(120)
      self.ConnectDevice()
      env.DUT.ActivateUSB()
      self.assertEqual(env.DUT.build.id.rsplit("-", 1)[0], # may have "-INSECURE"
          zipbuildname, "Not updated.")
      self.Info("Adding testset APN info: %r." % (env.APNINFO.name,))
      env.DUT.UpdateAPN(env.APNINFO)
      fpdir = datafile.GetDirectoryName(self.config)
      self.Info("Making data directory: %r" % fpdir)
      datafile.MakeDataDir(fpdir)
      return self.Passed("Software updated to %r." % (env.DUT.build.id,))
    else:
      self.Diagnostic(output)
      self.Diagnostic(errors)
      return self.Failed("fastboot error: %s" % (status,))



class SetupSuite(core.TestSuite):
  pass


# This suite is mostly just for self-testing.
def GetSuite(conf):
  suite = SetupSuite(conf)
  suite.AddTest(DeviceSetup)
  suite.AddTest(DeviceReport)
  return suite

def Run(conf):
  suite = GetSuite(conf)
  suite()


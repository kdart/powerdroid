#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab
#
# Copyright The Android Open Source Project
#
# Note that docstrings are in RST format:
# <http://docutils.sourceforge.net/rst.html>.
#
# The docstring headings map to testcase fields, so the names should not
# be changed.


"""
Bluetooth tests.
----------------

Test Bluetooth functionality.

These tests may be fully automated, or may require some user interaction.
In either case, these tests must be run in the Android test lab with the
device connected to the PowerDroid test system.

"""

__version__ = "$Revision$"


from droid.qa import core
from testcases.android import interactive



class BluetoothBaseTest(interactive.AndroidInteractiveMixin, core.Test):
  pass


class EnableBluetooth(core.Test, interactive.AndroidInteractiveMixin):
  """
Purpose
+++++++

Enable the bluetooth feature on the DUT.

Pass criteria
+++++++++++++

The Bluetooth feature becomes active.

Start Condition
+++++++++++++++

Bluetooth is not enabled on DUT.

End Condition
+++++++++++++

Bluetooth is enabled in DUT configuration, and activated.

Reference
+++++++++



Prerequisites
+++++++++++++

testcases.android.common.DeviceSetup

Procedure
+++++++++

1. Use UI to set bluetooth feature on.
2. Set DUT object's bluetooth address.

"""
  def Execute(self):
    self.EnableBluetooth()
    return self.Passed("Bluetooth enabled.") 



class BluetoothStartTest(BluetoothBaseTest):
  """
Purpose
+++++++

Verify Bluetooth may be started from UI.

Pass criteria
+++++++++++++

The Bluetooth feature becomes active.

Start Condition
+++++++++++++++

Bluetooth is not enabled on DUT.

End Condition
+++++++++++++

Bluetooth is enabled in DUT configuration, and activated.

Reference
+++++++++



Prerequisites
+++++++++++++

testcases.android.common.DeviceSetup

Procedure
+++++++++

1. launch Bluetooth and set the radio to be "ON". 
   Ensure that the Bluetooth application can be launched. 

2. Verify Bluetooth application is launched, and toggle indicates "ON".

"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    self.EnableBluetooth()
    return self.Passed("Bluetooth enabled.") 



class BluetoothReStartTest(BluetoothBaseTest):
  """
Purpose
+++++++

Verify that the Bluetooth radio is still "ON" after power cycle
Equipment.

Pass criteria
+++++++++++++


Start Condition
+++++++++++++++

Bluetooth is enabled in the configuration.

End Condition
+++++++++++++

No change.

Reference
+++++++++



Prerequisites
+++++++++++++

BluetoothStartTest

Procedure
+++++++++


1. Power cycle the DUT.
2. Verify Bluetooth radio is still "ON" after the power cycle.

"""

  PREREQUISITES = ["testcases.android.common.DeviceSetup"]

  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    return self.Incomplete("Not implemented.") 



class BluetoothNameTest(BluetoothBaseTest):
  """
Purpose
+++++++

Verify that the DUT can be configured to broadcast a unique name.

Pass criteria
+++++++++++++


Start Condition
+++++++++++++++

Bluetooth has been turned on, no name is configured.

End Condition
+++++++++++++

Bluetooth is on, and a unique name is configured.

Reference
+++++++++



Prerequisites
+++++++++++++

BluetoothReStartTest

Procedure
+++++++++


1. Go to Settings/Bluetooth/setup and change the name of the DUT form
   default to a unique name. For example, name your DUT "powerandroid".

2. Verify Bluetooth HCI is active by "scanning" for it on another device.

"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    return self.Incomplete("Not implemented.") 


class BluetoothNameSaveTest(BluetoothBaseTest):
  """
Purpose
+++++++

Verify that the DUT Bluetooth name change is saved across reboots.

Pass criteria
+++++++++++++


Start Condition
+++++++++++++++

Bluetooth has been turned on and given a unique name.

End Condition
+++++++++++++

No change.

Reference
+++++++++



Prerequisites
+++++++++++++

BluetoothNameTest

Procedure
+++++++++

1. Reverify that Bluetooth configuration UI shows the unique name
   previously entered.
2. Power cycle the DUT.
3. Verify again that the configuration UI shows the same name.
4. Verify by scanning with another device that the DUT is discoverable
   and advertises that name.

"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    return self.Incomplete("Not implemented.") 


class BluetoothPairingTest(BluetoothBaseTest):
  """
Purpose
+++++++

Verify that the Bluetooth headset and DUT may be paired.

Pass criteria
+++++++++++++

The bluetooth headset enters "ACLS" mode, meaning it has paired in slave
mode.

Start Condition
+++++++++++++++

Bluetooth is enabled and named.

End Condition
+++++++++++++

DUT is paired with a headset (testset).

Reference
+++++++++


Prerequisites
+++++++++++++

BluetoothNameTest

Procedure
+++++++++

1. Turn on Bluetooth headset (or test set) and make discoverable by
   following the manufacturer's instructions for connecting headsets
   Bluetooth headset is made visible/searchable to other devices 

2. Open Bluetooth Manager on DUT. Ensure the Bluetooth Headset is
   discovered and paired. Verify PIN popup occurs. PIM popup should stay
   open if the screen is slid open.

"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    return self.Incomplete("Not implemented.") 




class BluetoothQualityTest(BluetoothBaseTest):
  """
Purpose
+++++++

Verify that the conversation is clear when paired with headset.


Pass criteria
+++++++++++++

Audio quality in headset is acceptable in both mobile originated and
mobile terminated calls.

Start Condition
+++++++++++++++

Headset is paired and ready for use.

End Condition
+++++++++++++

No change.

Reference
+++++++++



Prerequisites
+++++++++++++

BluetoothPairingTest

Procedure
+++++++++

1. Make a MO phone call and ensure that you are able to speak via Bluetooth
headset. If using a test set, use the audio analyzer to detect signal and
measure noise and distortion.

2. Make a MT call to the DUT and ensure that the BT headset is able to
notify the user BT headset.

3. Accept the MT call using the headset. Verify call is activated. 
Check voice quality.

"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    return self.Incomplete("Not implemented.") 


class BluetoothNameVulnerabilityTest(BluetoothBaseTest):
  """
Purpose
+++++++

Verify that the DUT is not susceptible to:
http://cve.mitre.org/cgi-bin/cvename.cgi?name=CAN-2005-2547


Pass criteria
+++++++++++++

Name meta-characters have no effect.

Start Condition
+++++++++++++++

Bluetooth is active.

End Condition
+++++++++++++

No change.

Reference
+++++++++

http://cve.mitre.org/cgi-bin/cvename.cgi?name=CAN-2005-2547

Prerequisites
+++++++++++++


Procedure
+++++++++

1. Set up headset device with carefully crafted name that might expose this
   exploit. 

2. Pair with the device.

3. Verify that name with shell meta-characters cannot execute arbitrary
   code.


"""
  def Execute(self):
    cf = self.config
    DUT = cf.environment.DUT
    return self.incomplete("Not implemented.") 



class BluetoothSuite(core.TestSuite):
  pass

def GetSuite(conf):
  suite = BluetoothSuite(conf)
  suite.addTest(BluetoothStartTest)
  return suite


def run(conf):
  suite = GetSuite(conf)
  suite()


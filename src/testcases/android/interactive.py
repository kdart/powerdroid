#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Utility test for user-interactive Android tests.

"""


from droid.qa import core


class AndroidInteractiveMixin(object):
  """A mixin class for core.Test classes that provides user interactive
  methods for running tests. *Must* be mixed in with a core.Test subclass.

  The methods here are called to change the state of the DUT. The state
  may be changed without any user interaction, if possible, or by querying
  the user via the test framework's UI object.
  """

  def ConnectDevice(self):
    cf = self.config
    # Turning on charger turns on USB switch also.
    cf.environment.powersupply.ChargerOn() 
    self.Sleep(5) # give USB time to sync and settle.
    self.Info("Device connected to USB.")
    return False

  def DisconnectDevice(self):
    cf = self.config
    DUT = cf.environment.DUT
    # Turning off charger supply disconnects USB switch.
    cf.environment.powersupply.ChargerOff()
    DUT.DisconnectUSB()
    self.Info("Device disconnected from USB.")

  def PowerOnDevice(self):
    cf = self.config
    testset = cf.environment.testset
    retry = 0
    while retry < 3:
      cf.UI.printf("%IPlease power on device.%N Answer yes when done.")
      if cf.UI.yes_no("Powered and running?", default=False):
        break
      retry += 1
    else:
      raise core.TestSuiteAbort, "Device didn't power on."
    self.Info("Device powered ON.")
    DUT = cf.environment.DUT
    DUT.PowerOn()
    if DUT.IsUSBConnected():
      DUT.ActivateUSB()
      self.WaitForRuntime()

  def WaitForRuntime(self):
    cf = self.config
    DUT = cf.environment.DUT
    self.Info("Waiting for runtime activation.")
    while not DUT.IsBootComplete():
      self.Sleep(2)
    self.Sleep(10) # It's not really ready when it says it is.

  def WaitForPDP(self):
    cf = self.config
    testset = cf.environment.testset
    self.Info("Waiting for PDP activation.")
    retry = 0
    while retry < 20:
      if testset.IsPDPAttached():
        break
      else:
        self.Sleep(6)
      retry += 1
    else:
      raise core.TestSuiteAbort, "Device did not become PDP active."

  def RebootDevice(self):
    cf = self.config
    DUT = cf.environment.DUT
    DUT.Reboot()
    self.DisconnectDevice() # work around USB connection bug
    self.Sleep(60)
    self.ConnectDevice()
    DUT.ActivateUSB()
    self.Info("Device rebooted.")

  def PowerOffDevice(self):
    cf = self.config
    # Turning power off may generate spurious errors on test set, so turn
    # it off too, then set it back.
    oldmode = cf.environment.testset.SetOperatingMode("OFF")
    try:
      retry = 0
      while retry < 3:
        cf.UI.printf("%IPlease power off the DUT.%N")
        if cf.UI.yes_no("Is it off?", default=False):
          break
        retry += 1
      else:
        raise core.TestSuiteAbort, "Device didn't power off."
      self.Info("Device power OFF.")
      cf.environment.DUT.PowerOff()
    finally:
      cf.environment.testset.ClearErrors()
      cf.environment.testset.SetOperatingMode(oldmode)

  def DeviceRadioOff(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.IsCallActive():
      self.HangupCall()
    # Turning radio off may generate spurious errors on test set, so turn
    # it off too, then set it back.
    oldmode = cf.environment.testset.SetOperatingMode("OFF")
    self.Sleep(1)
    try:
      DUT.RadioOff(cf.get("use_ui", False))
      self.Sleep(4)
      self.Info("Radio OFF.")
    finally:
      cf.environment.testset.SetOperatingMode(oldmode)

  def DeviceRadioOn(self):
    cf = self.config
    cf.environment.DUT.RadioOn(cf.get("use_ui", False))
    self.Sleep(4)
    self.Info("Radio ON.")

  def DeviceSyncOn(self):
    cf = self.config
    DUT = cf.environment.DUT
    if not DUT.HasAccount():
      self.AddAccount()
    if not DUT.IsSyncingOn():
      DUT.ToggleSyncState()
    self.Info("Syncing ON.")

  def DeviceSyncOff(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.IsSyncingOn():
      DUT.ToggleSyncState()
    self.Info("Syncing OFF.")

  def MakeACall(self, user=False):
    cf = self.config
    DUT = cf.environment.DUT
    testset = cf.environment.testset
    if user:
      self.Info("Making a call from mobile (mobile originated).")
      if DUT.IsUSBConnected():
        retry = 0
        while retry < 3:
          DUT.Call(cf.testsets.dialednumber)
          # test set automatically answers.
          self.Sleep(10) # DUT can take some time to actually call!
          if not testset.callcondition.connected:
            retry += 1
          else:
            break
        else:
          raise core.TestIncompleteError, "Mobile/DUT did not make the call."
      else:
        retry = 0
        while retry < 3:
          cf.UI.printf(
              "%IPlease use the DUT UI to make a phone call.%N "
              "Answer yes when done.")
          if cf.UI.yes_no("Active call?", default=False):
            break
          retry += 1
        else:
          raise core.TestIncompleteError, "User did not make a call."
    else: # remote
      self.Info("Making a call from network/testset.")
      testset.ClearErrors()
      testset.Call()
      if cf.bttestsets.use:
        if not cf.environment.bttestset.autoanswer:
          cf.environment.bttestset.Answer()
      elif DUT.IsUSBConnected():
        retry = 0
        while retry < 6:
          if not testset.callcondition.connected:
            self.Sleep(5)
            DUT.AnswerCall()
            retry += 1
          else:
            break
        else:
          raise core.TestIncompleteError, "DUT did not pick up call."
      else:
        retry = 0
        while retry < 3:
          cf.UI.printf(
              "%IPlease use the DUT UI to answer the call.%N "
              "Answer yes when done.")
          if cf.UI.yes_no("Answered and active?", default=False):
            break
          retry += 1
        else:
          raise core.TestIncompleteError, "User did not answer call."
    # verify with test set
    testset.ClearErrors()
    if not testset.IsCallActive():
      raise core.TestIncompleteError, "Did not establish voice call."
    DUT.CallActive()

  def HangupCall(self, user=False):
    cf = self.config
    DUT = cf.environment.DUT
    testset = cf.environment.testset
    if user:
      self.Info("Hanging up call from MS/UI.")
      if cf.bttestsets.use:
        cf.environment.bttestset.Hangup()
        self.Sleep(3)
      elif DUT.IsUSBConnected():
        DUT.Hangup()
      else: 
        retry = 0
        while retry < 3:
          cf.UI.printf(
              "%IPlease use the DUT UI hang up voice call.%N "
              "Answer yes when done.")
          if cf.UI.yes_no("Voice call hung up?", default=False):
            break
          retry += 1
        else:
          raise core.TestIncompleteError, "User did not hang up."
    else:
      self.Info("Hanging up call from network/testset.")
      testset.ClearErrors()
      testset.Hangup()
      self.Sleep(3)
      if DUT.IsUSBConnected():
        DUT.Hangup()
    testset.ClearErrors()
    if testset.IsCallActive():
      raise core.TestIncompleteError, "Call did not hang up."
    DUT.CallInactive()

  def DownlinkAudioOn(self):
    cf = self.config
    cf.environment.testset.ClearErrors()
    cf.environment.testset.SetDownlinkAudio("SIN1000")
    cf.environment.DUT.AudioOn()
    self.Info("Turned downlink audio ON.")

  def DownlinkAudioOff(self):
    cf = self.config
    cf.environment.testset.ClearErrors()
    cf.environment.testset.SetDownlinkAudio("NONE")
    cf.environment.DUT.AudioOff()
    self.Info("Turned downlink audio OFF.")

  def UplinkAudioOn(self):
    cf = self.config
    #cf.environment.testset.SetUplinkAudio("MULTITONE")
    cf.environment.DUT.UplinkAudioOn()
    self.Info("Turned uplink audio ON.")

  def UplinkAudioOff(self):
    cf = self.config
    #cf.environment.testset.SetUplinkAudio()
    cf.environment.DUT.UplinkAudioOff()
    self.Info("Turned uplink audio OFF.")

  def PowerSupplyOn(self):
    self.Info("Turning power supply on.")
    cf = self.config
    cf.environment.powersupply.SetVoltage(cf.get("voltage", 3.8))
    cf.environment.powersupply.On()
    self.Sleep(2) # sleep to let PS and DUT settle

  def PowerSupplyOff(self):
    self.Info("Turning power supply off.")
    self.config.environment.powersupply.Off()
    self.Sleep(1) # sleep to let PS and DUT settle

  def PowerSupplyVoltage(self):
    return self.config.environment.powersupply.MeasureDCVoltage()

  def PowerCycle(self, delay=5):
    self.Info("Power cycling DUT.")
    self.config.environment.powersupply.Reset()
    self.Sleep(delay)
    self.PowerSupplyOn()
    self.ConnectDevice()
    # Take advantage of off state to verify charger voltage here.
    self.PowerSupplyOff()
    self.CheckChargeVoltage() 
    self.PowerSupplyOn()

  def CheckChargeVoltage(self):
    voltage = self.config.environment.powersupply.MeasureDCVoltage()
    self.Info("Checking charge voltage.")
    self.assertApproximatelyEqual(
        float(voltage), 
        self.config.get("chargevoltage", 4.2), 
        0.1,
        "Not correct charge voltage. Got: %s" % voltage)
    self.Info("OK, charge voltage is %s." % voltage)

  def GetBuildInfoFromUser(self):
    build = {}
    build["product"] = "sooner"
    build["type"] = "release"
    build["id"] = None
    cf = self.config
    UI = cf.UI
    UI.printf("Manual build information entry.")
    while True:
      UI.printf("%IEnter build information%N.")
      build["product"] = UI.get_value("Product?", default=build["product"])
      build["type"] = UI.get_value("Build type?", default=build["type"])
      build["id"] = UI.get_value("Build ID?", default=build["id"])
      UI.write("\nEntered values:\nProduct: %s\nType: %s\nBuild id: %s\n" % (
        build["product"], 
        build["type"], 
        build["id"]))
      if UI.yes_no("OK?", default=True):
        break
    cf.environment.DUT.SetBuild(build)

  def UpdateDevice(self):
    """Installs new build and does any required one-time setup."""
    cf = self.config
    buildfile = cf.get("buildfile")
    if buildfile:
      self.Info("Updating device build to %r." % (buildfile,))
      cf.environment.DUT.UpdateSoftware(buildfile, wipe=True)
      return True
    return False

  def UpdateAPN(self):
    """Add an APN entry for the lab configuration."""
    env = self.config.environment
    env.DUT.UpdateAPN(env.APNINFO)

  def AddAccount(self):
    cf = self.config
    if cf.environment.DUT.HasAccount():
      return
    retry = 0
    while retry < 3:
      cf.UI.printf(
          "%IPlease use the DUT UI to add Gmail/XMPP account.%N "
          "Answer yes when done.")
      if cf.UI.yes_no("account %r added?" % cf.account, default=False):
        cf.UI.printf("OK, I %gtrust%N you, %u!")
        break
      retry += 1
    else:
      raise core.TestIncompleteError, "XMPP/Gmail account not added."
    cf.environment.DUT.SetAccount(cf.account)
    self.Info("Gmail/XMPP account for %r added." % cf.account)

  def RemoveAccount(self):
    cf = self.config
    retry = 0
    while retry < 3:
      cf.UI.printf(
          "%IPlease use the DUT UI to remove Gmail/XMPP account.%N "
          "Answer yes when done.")
      if cf.UI.yes_no("Account removed?", default=False):
        cf.UI.printf("OK, I %gtrust%N you, %u!")
        break
      retry += 1
    else:
      raise core.TestIncompleteError, "XMPP/Gmail account not removed."
    cf.environment.DUT.SetAccount(None)
    self.Info("Gmail/XMPP account remove.")

  def SetXMPPOn(self):
    cf = self.config
    DUT = cf.environment.DUT
    if not DUT.HasAccount():
      self.AddAccount()
    if not DUT.IsXMPPPersistent():
      DUT.ToggleXMPP()
      DUT.XMPPOn()
    self.Info("Persistent XMPP/Gtalk ON.")

  def SetXMPPOff(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.IsXMPPPersistent():
      DUT.ToggleXMPP()
      DUT.XMPPOff()
    self.Info("Persistent XMPP/Gtalk OFF.")

  def TurnUpdatesOn(self):
    cf = self.config
    cf.environment.mailer.Start()
    cf.environment.DUT.UpdatesOn()
    self.Info("Mail updates ON.")

  def TurnUpdatesOff(self):
    cf = self.config
    cf.environment.mailer.Stop()
    cf.environment.DUT.UpdatesOff()
    self.Info("Mail updates OFF.")

  def ChangeConfig(self, statename, newstate, prompt):
# FIXME incomplete, work in progress, don't use yet.
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.GetState(statename) != newstate:
      self._ChangeState(statename, newstate)
    retry = 0
    while retry < 3:
      cf.UI.printf("%%I%s%%N. %%nAnswer yes when done." % (prompt,))
      if cf.UI.yes_no("Changed?", default=False):
        cf.UI.printf("OK, I %gtrust%N you, %u!")
        break
      retry += 1
    else:
      raise core.TestIncompleteError("%s not changed." % (statename,))

    DUT.ChangeState(statename, newstate)
    self.Info("State %r set to %s." % (statename, newstate))

  def EnableBluetooth(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.IsUSBConnected():
      DUT.SetBluetoothON()
    else:
      retry = 0
      while retry < 3:
        cf.UI.printf(
            "%IVerify Bluetooth is ON and connected to Bluetooth testset.%N "
            "Answer yes when done.")
        if cf.UI.yes_no("Bluetooth ON?", default=False):
          break
        retry += 1
      else:
        raise core.TestIncompleteError, "User did not verify bluetooth state."
      DUT.StateON("bluetooth")
    self.Info("Bluetooth is ON.")

  def DisableBluetooth(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.IsUSBConnected():
      DUT.SetBluetoothOFF()
    else:
      retry = 0
      while retry < 3:
        cf.UI.printf(
            "%ITurn OFF and verify Bluetooth is OFF.%N "
            "Answer yes when done.")
        if cf.UI.yes_no("Bluetooth OFF?", default=False):
          break
        retry += 1
      else:
        raise core.TestIncompleteError, "User did not verify bluetooth state."
      DUT.StateOFF("bluetooth")
    self.Info("Bluetooth is OFF.")

  def EnableWifi(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.IsUSBConnected():
      DUT.SetWifiON()
    else:
      retry = 0
      while retry < 3:
        cf.UI.printf(
            "%IVerify Wifi is ON and connected to access point.%N "
            "Answer yes when done.")
        if cf.UI.yes_no("Wifi ON?", default=False):
          cf.UI.printf("OK, I %gtrust%N you, %u!")
          break
        retry += 1
      else:
        raise core.TestIncompleteError, "User did not verify wifi state."
      DUT.StateON("wifi")
    self.Info("Wifi is ON.")

  def DisableWifi(self):
    cf = self.config
    DUT = cf.environment.DUT
    if DUT.IsUSBConnected():
      DUT.SetWifiOFF()
    else:
      retry = 0
      while retry < 3:
        cf.UI.printf(
            "%IVerify Wifi is oFF and not connected to access point.%N "
            "Answer yes when done.")
        if cf.UI.yes_no("Wifi OFF?", default=False):
          cf.UI.printf("OK, I %gtrust%N you, %u!")
          break
        retry += 1
      else:
        raise core.TestIncompleteError, "User did not verify wifi state."
      DUT.StateOFF("wifi")
    self.Info("Wifi is OFF.")



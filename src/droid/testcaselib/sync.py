#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab

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



"""Support for syncing tests.

"""

__author__ = 'dart@google.com (Keith Dart)'


from pycopia import proctools


class MessageMailer(object):
  """An emailing instrument. 

  Args:
    recipient (string): the primary recipient of emails.
    messages (int): number of messages per thread.
    rate (float): the rate, in messages per minute, to send emails.
  """
  def __init__(self, recipient, messages, rate):
    self._delay = 1.0 / (rate / 60.0) # time delay is in seconds
    # 5 days worth or threads, to be sure to cover any test.
    self._messagethreads = int(720 * rate)
    self._messages = messages
    self._recipient = recipient
    self._proc = None
    self._exitstatus = None

  def Start(self):
    if self._proc is None:
      self._exitstatus = None
      self._proc = proctools.submethod(_SubMailer, 
          (self._messagethreads, self._messages, self._delay,
          self._recipient))
      self._proc.set_callback(self._End_cb)

  def __str__(self):
    if self._exitstatus is None:
      return str(self._proc)
    else:
      return str(self._exitstatus)

  def Stop(self):
    proc = self._proc
    self._proc = None
    if self._exitstatus is None:
      proc.kill()
      proc.close()
      self._exitstatus = proc.wait()
    return self._exitstatus

  def IsRunning(self):
    return self._exitstatus is None

  def _End_cb(self, proc):
    self._proc = None
    self._exitstatus = proc.exitstatus


def _SubMailer(topics, messages, delay, recipient):
  """Runs the mailer, from a subprocess."""
  # import here since this is run from a subprocess.
  from droid import mailer
  mlr = mailer.Mailer(topics, messages, delay, recipient)
  mlr.Run()



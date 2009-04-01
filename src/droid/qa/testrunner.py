#!/usr/bin/python2.4
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


This module provides the primary test runner for the automation framework.

"""
__author__ = 'dart@google.com (Keith Dart)'

import sys
import os
import shutil
from errno import EEXIST

from pycopia import timelib
from pycopia import debugger

from  droid.qa import core
from  droid.qa import constants
from droid.storage.Storage import NoSuchReport

# for object type checking
ModuleType = type(sys)
ObjectType = object
TypeType = type


class Error(Exception):
  """Testrunner errors."""
  pass

class TestRunnerError(Error):
  """Raised for a runtime error of the test runner."""


class TestRunner(object):
  """Runs test objects.

  Handled running objects, generating the report, and other overhead of
  running tests and cleaning up afterwards.
  """
  def __init__(self, config):
    self.config = config
    self.config.options_override = {}
    self.config.arguments = []

  def SetOptions(self, opts):
    if isinstance(opts, dict):
      self.config.options_override = opts
    else:
      raise ValueError, "Options must be dictionary type."

  def RunObject(self, obj):
    """Run a test object (object with run() function or method).

    Arguments: 
      obj: 
        A Python test object.  This object must have a `run()` function
        or method that takes a configuration object as it's single
        parameter. It should also have a `test_name` attribute.

    Messages:
      May send any of the following messages to the report object:
        RUNNERARGUMENTS: 
          command-line arguments given to test runner.
        logfile: 
          name of the log file from the configuration.
        COMMENT:
          User supplied comment given when test object was invoked.
        RUNNERSTART:
          Timestamp when test runner started.
        RUNNEREND:
          Timestamp when test runner ends.
        add_url:
          Location where any generated data files, logs, and reports can
          be found.

    """
    cf = self.config
    basename = "_".join(obj.test_name.split("."))
    cf.reportfilename = basename
    cf.logbasename = "%s.log" % (basename,)
    # resultsdir is where you would place any resulting data files. This
    # is also where any report object or log files are placed.
    cf.resultsdir = os.path.join(
      os.path.expandvars(cf.get("resultsdirbase", "/var/tmp")),
      "%s-%s-%s" % (cf.reportfilename, cf.username, timelib.strftime("%Y%m%d%H%M", 
      timelib.localtime(cf.runnerstarttime))))
    self._CreateResultsDir()
    self._ReportUrl()
    cf.report.logfile(cf.logfilename)
    # run the test object!
    return obj.Run(cf) 

  def RunObjects(self, objects):
    """Invoke the `run` method on a list of mixed runnable objects.

    Arguments:
      objects:
        A list of runnable object instances.

    May raise TestRunnerError if an object is not runnable by this test
    runner.
    """
    for obj in objects:
      objecttype = type(obj)
      if objecttype is ModuleType and hasattr(obj, "Run"):
        self.RunModule(obj)
      elif objecttype is TypeType and issubclass(obj, core.Test):
          self.RunTest(obj)
      elif isinstance(obj, core.TestSuite):
          self.RunSuite(obj)
      else:
        raise TestRunnerError("%r is not a runnable object." % (obj,))

  def RunModule(self, mod):
    """Run a test module.

    Prepares the configuration with module configuration, sends report
    messages appropriate for modules, and reports pass or fail.

    Arguments:
      mod:
        A module object with a run() function that takes a configuration
        object as it's single parameter.

    Returns:
      The return value of the module's Run() function, or FAILED if the
      module raised an exception.
    """
    cf = self.config
    # merge any test-module specific config files. The config file name is
    # the same as the module name, with ".conf" appended. Located in the
    # same directory as the module itself.
    testconf = os.path.join(os.path.dirname(mod.__file__), 
          "%s.conf" % (mod.__name__.split(".")[-1],))
    cf.mergefile(testconf)
    cf.evalupdate(cf.options_override)
    # make the module look like a test.
    mod.test_name = mod.__name__
    try:
      ID = mod.__version__[1:-1]
    except AttributeError: # should be there, but don't worry if its not.
      ID = "undefined"
    cf.report.add_message("MODULEVERSION", ID)
    cf.report.add_message("MODULESTARTTIME", timelib.now())
    try:
      rv = self.RunObject(mod)
    except KeyboardInterrupt:
      cf.report.add_message("MODULEENDTIME", timelib.now())
      cf.report.incomplete("Module aborted by user.")
      raise
    except:
      ex, val, tb = sys.exc_info()
      if cf.flags.DEBUG:
        debugger.post_mortem(tb, ex, val)
      rv = constants.FAILED
      cf.report.add_message("MODULEENDTIME", timelib.now())
      cf.report.failed("Module exception: %s (%s)" % (ex, val))
    else:
      cf.report.add_message("MODULEENDTIME", timelib.now())
      if rv is None:
        # If module run() function returns None we take that to mean that
        # it runs a TestSuite itself. Report nothing.
        pass
      # But if the module returns something else we take that to mean that
      # it is reporting some true/false value to report as pass/fail.
      elif rv:
        return cf.report.passed("Return evaluates True.")
      else:
        return cf.report.failed("Return evaluates False.")
      return rv

  def RunSuite(self, suite):
    """Run a TestSuite object.

    Given a pre-populated TestSuite object, run it after initializing
    configuration and report objects.

    Arguments:
      suite:
        An instance of a core.TestSuite class or subclass. This should
        already have Test objects added to it.

    Returns:
      The return value of the suite. Should be PASSED or FAILED.

    """
    assert isinstance(suite, core.TestSuite), "Must supply TestSuite object."
    return self.RunObject(suite)

  def RunTest(self, testclass, *args, **kwargs):
    """Run a test class with arguments.

    Runs a single test class with the provided arguments.

    Arguments:
      testclass:
        A class that is a subclass of core.Test. Any extra arguments given
        are passed to the `execute()` method when it is invoked.

    Returns:
      The return value of the Test instance. Should be PASSED, FAILED, 
      INCOMPLETE, or ABORT.
    """
    cf = self.config
    testinstance = testclass(cf)
    entry = core.TestEntry(testinstance, args, kwargs)
    try:
      return self.RunObject(entry)
    except core.TestSuiteAbort, err:
      cf.report.info("%r aborted (%s)." % (entry.test_name, err))
      entry.result = constants.INCOMPLETE
      return constants.ABORT

  def _CreateResultsDir(self):
    """Make results dir, don't worry if it already exists."""
    try:
      os.mkdir(self.config.resultsdir)
    except OSError, error:
      if error[0] == EEXIST:
        pass
      else:
        raise # raise original execption since we don't know what else it
              # could be. This will be an OSError, which is not specific
              # to the domain of this module.

  def _ReportUrl(self):
    """Construct a URL for finding the report and test produced data.

    If the configuration has a `baseurl` and `documentroot` defined then
    the results location is available by web server and a URL is sent to
    the report. If not, the a directory location is sent to the report.
    """
    cf = self.config
    baseurl = cf.get("baseurl")
    documentroot = cf.get("documentroot")
    resultsdir = cf.resultsdir
    if baseurl and documentroot:
      cf.report.add_url("Results location.", baseurl + resultsdir[len(documentroot):])
    else:
      cf.report.add_url("Results location.", "file://" + resultsdir)

  def Initialize(self):
    """Perform any initialization needed by the test runner.

    Initializes report. Sends runner and header messages to the report.
    """
    cf = self.config
    cf.username = os.environ["USER"]
    os.chdir(cf.logfiledir) # Make sure runner CWD is a writable place.
    cf.runnerstarttime = starttime = timelib.now()
    try:
      rpt = cf.report
    except NoSuchReport, err:
      cf.UI.error("No report with the name %r. Use of of the following." % (cf.reportname,))
      cf.UI.print_list(err.args[0])
      raise TestRunnerError, "No such report name: %r" % (cf.reportname,)
    # Report file's names. save for future use.
    cf.reportfilenames = rpt.filenames 
    rpt.initialize(cf)
    rpt.add_title("Test Results for %r." % " ".join(cf.get("argv", [])))
    arguments = cf.get("arguments")
    # Report command line arguments, if any.
    if arguments:
      rpt.add_message("RUNNERARGUMENTS", " ".join(arguments))
    # Report comment, if any.
    comment = cf.get("comment")
    if comment:
      rpt.add_message("COMMENT", comment)
    rpt.add_message("RUNNERSTARTTIME", starttime, 0)

  def Finalize(self):
    """Perform any finalization needed by the test runner.

    Sends runner end messages to report. Finalizes report.
    """
    cf = self.config
    rpt = cf.report
    rpt.add_message("RUNNERENDTIME", timelib.now(), 0)
    rpt.finalize()
    # force close of report and logfile between objects. these are
    # `property` objects and deleting them makes them close and clears the
    # cache.
    del rpt
    del cf.report
    del cf.logfile 
    del cf.UI 
    if cf.has_key("resultsdir"):
      for fname in cf.reportfilenames:
        if not fname.startswith("<"): # a real file, not builtin stdio
          if os.path.isfile(fname):
            shutil.move(fname, cf.resultsdir)
      if os.path.isfile(cf.logfilename):
        if os.path.getsize(cf.logfilename) > 0:
          shutil.move(cf.logfilename, cf.resultsdir)
      # If resultsdir ends up empty, remove it.
      if not os.listdir(cf.resultsdir): # TODO(dart), stat this instead
        os.rmdir(cf.resultsdir)


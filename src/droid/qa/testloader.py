#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright 2006 The Android Open Source Project

"""Module that defines test loaders.

The objects here are responsible for taking a desired test, or set of
tests, looking in the database for implementations and dependencies, and
constructing a runnable test objects. It also provides utility functions
for listing and instantiating runnable test objects.
"""


__author__ = 'dart@google.com (Keith Dart)'


import sys
import os

from pycopia.aid import newclass
from pycopia.textutils import identifier

from droid.qa import core
from droid.util import module


class Error(Exception):
  """Base class for test loader errors."""

class NoImplementationError(Error):
  """Raised when a test object has no automated implementation defined."""

class InvalidObjectError(Error):
  """Raised when an attempt is made to instantiate a test object from the
  database, but the object in the database is marked invalid.
  """

class InvalidTestError(Error):
  """Raised when a test is requested that cannot be run for some
  reason.
  """

def GetTestClass(dbcase):
  """Return the implementation of a TestCase.
  Return None if testcase is not fully automated.
  """
  if dbcase.automated and dbcase.valid:
    impl = dbcase.testimplementation
    if impl:
      obj = module.GetObject(impl)
      if type(obj) is type and issubclass(obj, core.Test):
        return obj
      else:
        raise InvalidTestError("%r is not a Test class object." % (obj,))
    else:
      raise NoImplementationError(
                    "No implementation defined for test %r." % (dbcase.name,))
  else:
    return None


def NewTestSuite(dbsuite):
  """Return a runnable Suite converted from a database TestSuite."""
  if dbsuite.valid:
    return newclass(identifier(dbsuite.name), core.TestSuite)
  else:
    raise InvalidObjectError("%s is not runnable (not valid)." % (dbsuite,))



def GetModuleFile(mod):
  """Find the source file for a module. Give the module, or a name of one.

  Returns:
    Full path name of Python source file. Returns None if not found."""
  if type(mod) is str:
    mod = module.GetModule(mod)
  try:
    basename, ext = os.path.splitext(mod.__file__)
  except AttributeError: # C modules don't have a __file__ attribute
    return None
  testfile = basename + ".py"
  if os.path.isfile(testfile):
    return testfile
  return None



def GetModuleList():
  """Get list of test modules.

  Used by user interfaces to select a module to run. All automated test
  implementations are located in a base package called "testcases".

  Returns:
    A complete list of module names found in the "testcases" package, as
    strings. This includes sub-packages.
  """
  import testcases
  # callback for testdir walker
  def filternames(flist, dirname, names):
    for name in names:
      if name.endswith(".py") and not name.startswith("_"):
        flist.append(os.path.join(dirname, name[:-3]))
  testhome = os.path.dirname(testcases.__file__)
  modnames = []
  os.path.walk(testhome, filternames, modnames)
  testhome_index = len(os.path.dirname(testhome)) + 1
  names = map(lambda n: n[testhome_index:].replace("/", "."), modnames)
  names.sort()
  return names

# store type objects here for speed
ModuleType = type(core)
FunctionType = type(GetModuleList)


#### The command-line interface object. ####


# not in a docstring since docstrings don't exist in optimize mode.
TestRunnerInterfaceDoc = r"""
Invoke a test or test suite from a shell.

Usage:

  %s [-hdviIcf] [-n <string>] arg...

  Where the arguments are test suite or test case names. If none are
  supplied a menu is presented.

  Options:
    Tells the runner what test modules to run, and sets the flags in the
    configuration. Options are:

      -h -- Print help text and return.
      -d -- Turn on debugging.
      -v -- Increase verbosity.
      -i -- Set flag to run interactive tests.
      -I -- Set flag to skip interactive tests.
      -c or -f <file> -- Merge in extra configuration file.
      -n <string> -- Add a comment to the test report.
"""

class TestRunnerInterface(object):
  """A Basic CLI interface to a TestRunner object.

  Instantiate with an instance of a TestRunner.

  Call the instance of this with an argv list to instantiate and run the
  given tests.
  """
  def __init__(self, testrunner):
    self.runner = testrunner

  def __call__(self, argv):
    """Run the test runner.

    Invoke the test runner by calling it.
    """
    cf = self.runner.config
    # this getopt() is a lightweight getopt that only considers
    # traditional options as options (e.g. -x). Any long-option form (e.g.
    # --reportname=default) is converted into a dictionary and is used to
    # update the configuration. This allows the user or test runner to
    # provide or alter configuration parameters at run time without
    # needing a pre-defined list to getopt().
    from pycopia import getopt
    optlist, extraopts, args = getopt.getopt(argv[1:], "h?dviIc:f:n:")
    for opt, optarg in optlist:
      if opt in ("-h", "-?"):
        print TestRunnerInterfaceDoc % (os.path.basename(argv[0]),)
        return
      if opt == "-d":
        cf.flags.DEBUG += 1
      if opt == "-v":
        cf.flags.VERBOSE += 1
      if opt == "-i":
        cf.flags.INTERACTIVE = True
      if opt == "-I":
        cf.flags.INTERACTIVE = False
      if opt == "-c" or opt == "-f":
        cf.mergefile(optarg)
      if opt == "-n":
        cf.comment = optarg
    cf.update(extraopts)
    cf.argv = args # test args
    # original command line arguments saved for the report
    cf.arguments = [os.path.basename(argv[0])] + argv[1:]
    # Save extra options for overriding configuration after a mergefile
    # because command line options should have highest precedence.
    self.runner.SetOptions(extraopts)

    if not args:
      from pycopia import cliutils
      l = GetModuleList()
      l.insert(0, None)
      arg = cliutils.choose(l, prompt="Select test")
      if arg is None:
        return
      args = [arg]
    objects, errors = module.GetObjects(args)
    if errors:
      print >>sys.stderr, "Errors found while loading test object:"
      for error in errors:
        print >>sys.stderr, error
    if objects:
      self.runner.Initialize()
      self.runner.RunObjects(objects)
      self.runner.Finalize()




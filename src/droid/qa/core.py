#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copied from Pycopia test automation framework, and modified.
# Copied from Gtest test automation framework, and modified.


"""Provides base classes for test cases and suites.

This module defines a Test class, which is the base class for all test case
implementations. This class is not substantiated itself, but a subclass is
defined that overrides the `execute` method. 

Your `execute` should return the value that the `Passed` or
`Failed` methods return, as appropriate. 

All test related errors are based on the `TestError` exception. You may
also use the built-in `assert` statement. There are also various assertion
methods you may use. If a test cannot be completed for some reason you may
also raise a 'TestIncompleteError' exception.

Usually, a set of test cases is collected in a TestSuite object, and run
sequentially by calling the suite instance. 

"""

__author__ = 'keith@dartworks.biz (Keith Dart)'


import sys
import os

from pycopia import combinatorics
from pycopia import scheduler
from pycopia import timelib
from pycopia import debugger
from pycopia import UserFile
from pycopia import dictlib
from pycopia import aid

from droid.qa import constants
from droid.util import module
from droid.util import methods


__all__ = ['Test', 'TestSuite']

# exception classes that may be raised by test methods.
class TestError(AssertionError):
    """TestError() Base class of testing errors. 

    This is based on AssertionError so the same assertion catcher can be
    used for catching assertions and these kind of exceptions.
    """
Error = TestError # alias for google conformance.

class TestIncompleteError(TestError):
    """Test case disposition could not be determined."""

class TestFailError(TestError):
    """Test case failed to meet the pass criteria."""

class TestSuiteAbort(Exception):
    """Entire test suite must be aborted."""


class TestPrerequisiteError(Exception):
    """Error in prerequisite calculation."""


class TestOptions(object):
    """A descriptor that forces OPTIONS to be class attributes that are not
    overridable by instances.
    """
    def __init__(self, initdict):
        # Default option value is empty iterable (evaluates false).
        self.OPTIONS = dictlib.AttrDictDefault(initdict, default=())

    def __get__(self, instance, owner):
        return self.OPTIONS

    # This is here to make instances not able to override options, but does
    # nothing else. Attempts to set testinstance.OPTIONS are simply ignored.
    def __set__(self, instance, value):
        pass


def InsertOptions(klass, **kwargs):
    if type(klass) is type and issubclass(klass, Test):
        if not klass.__dict__.has_key("OPTIONS"):
            klass.OPTIONS = TestOptions(kwargs)
    else:
        raise ValueError("Need Test class.")


class Test(object):
    """Base class for all test cases.

    Subclass this to define a new test. The test should be as atomic as
    possible. A Test may be combined with other tests and may have
    dependencies (defined by the database).

    May send any of the following messages to the report object:
        TESTARGUMENTS : string representation of supplied arguments.
        STARTTIME         : timestamp indicating when test was started.
        ENDTIME             : timestamp indicating when test ended.
        add_heading     : Section heading.
        passed                : When test passed.
        failed                : When test failed.
        Incomplete        : When test was not able to complete.
        diagnostic        : Add useful diagnostic information when a test fails.
        abort                 : Abort suite, provides the reason.
        Info                    : Informational and progress messages.
    """
    # class level attributes that may be overridden in subclasses, or reset by test
    # runner from external information (database).

    OPTIONS = TestOptions({})
    PREREQUISITES = []

    def __init__(self, config):
        cl = self.__class__
        self.test_name = "%s.%s" % (cl.__module__, cl.__name__)
        self.config = config 
        self._report = config.report 
        self._debug = config.flags.DEBUG 
        self._verbose = config.flags.VERBOSE 
        self.__datapoints = []
        self._merge_config()

    def _merge_config(self):
        """Merge Test specific config file."""
        cl = self.__class__
        cf = self.config
        mod = sys.modules[cl.__module__]
        testcnf = os.path.join(os.path.dirname(mod.__file__), 
                    "%s.conf" % (cl.__name__,))
        if cf.mergefile(testcnf):
            cf.evalupdate(cf.options_override)

    @classmethod
    def set_test_options(cls):
        InsertOptions(cls)
        opts = cls.OPTIONS
        pl = []
        for prereq in cls.PREREQUISITES:
            if type(prereq) is str:
                pl.append(PreReq(prereq))
            elif type(prereq) is tuple:
                pl.append(PreReq(*prereq))
            else:
                raise ValueError("Bad prerequisite value.")
        opts.prerequisites = pl
        opts.bugid = None

    def __call__(self, *args, **kwargs):
        """Invoke the test.

        The test is "kicked-off" by calling this. Any arguments are passed to
        the test implementation (`execute` method).
        """
        self._report.add_heading(self.test_name, 2)
        if args or kwargs:
            self._report.add_message("TESTARGUMENTS", ReprArgs(args, kwargs), 2)
        self.starttime = timelib.now() # saved starttime in case initializer
                                                                     # needs to create the log file.
        rv = None # in case of exception
        rv = self._initialize(rv)
        if rv is not None: # an exception happened
            return rv
        # test elapsed time does not include initializer time.
        teststarttime = timelib.now()
        # run the execute() method and check for exceptions.
        try:
            rv = self.execute(*args, **kwargs)
        except KeyboardInterrupt:
            if self._debug:
                ex, val, tb = sys.exc_info()
                debugger.post_mortem(tb, ex, val)
            rv = self.Incomplete("%s: aborted by user." % self.test_name)
            self._finalize(rv)
            raise
        except TestFailError, errval:
            rv = self.Failed("Caught Fail exception: %s" % (errval,))
        except TestIncompleteError, errval:
            rv = self.Incomplete("Caught Incomplete exception: %s" % (errval,))
        # Test asserts and validation errors are based on this.
        except AssertionError, errval:
            rv = self.Failed("failed assertion: %s" % (errval,))
        except TestSuiteAbort:
            raise # pass this one up to suite
        except debugger.DebuggerQuit: # set_trace "leaks" BdbQuit
            rv = self.Incomplete("%s: Debugger exit." % (self.test_name, ))
        except:
            ex, val, tb = sys.exc_info()
            if self._debug:
                debugger.post_mortem(tb, ex, val)
                tb = None
            rv = self.Incomplete("%s: Exception occured! (%s: %s)" % \
                    (self.test_name, ex, val))
        endtime = timelib.now()

        self._report.add_message("STARTTIME", teststarttime, 2)
        self._report.add_message("ENDTIME", endtime, 2)
        minutes, seconds = divmod(endtime - teststarttime, 60.0)
        hours, minutes = divmod(minutes, 60.0)
        self.Info("Time elapsed: %02.0f:%02.0f:%02.2f" % (hours, minutes, seconds))
        return self._finalize(rv)

    def _initialize(self, rv):
        """initialize phase handler.

        Run user-defined `initialize()` and catch exceptions. If an exception
        occurs in the `initialize()` method (which establishes the
        pre-conditions for a test) then alter the return value to abort()
        which will abort the suite. Invokes the debugger if the debug flag is
        set. If debug flag is not set then emit a diagnostic message to the
        report.
        """
        try:
            self.initialize()
        except:
            ex, val, tb = sys.exc_info()
            self.Diagnostic("%s (%s)" % (ex, val))
            if self._debug:
                debugger.post_mortem(tb, ex, val)
            rv = self.Abort("Test initialization failed!")
        return rv

    def _finalize(self, rv):
        """
        Run user-defined `finalize()` and catch exceptions. If an exception
        occurs in the finalize() method (which is supposed to clean up from
        the test and leave the UUT in the same condition as when it was
        entered) then alter the return value to abort() which will abort the
        suite. Invokes the debugger if the debug flag is set.
        """
        try:
            self.finalize(rv)
        except:
            ex, val, tb = sys.exc_info()
            self.Diagnostic("%s (%s)" % (ex, val))
            if self._debug:
                debugger.post_mortem(tb, ex, val)
            rv = self.Abort("Test finalize failed!")
        if self.__datapoints and rv == constants.PASSED:
            self.SaveData(self.__datapoints, DT_PICKLE, 
                         note="datapoints: %d" % (len(self.__datapoints),))
                            # the above note has special meaning to other parts of the
                            # framework (reporting)
        return rv

    # utility methods - methods that are common to nearly all tests.

    def GetStartTimestamp(self):
        return timelib.strftime("%m%d%H%M%S", timelib.localtime(self.starttime))

    def GetFilename(self, basename=None, ext="log"):
        """Create a log file name.

        Return a standardized log file name with a timestamp that should be
        unique enough to not clash with other tests, and also able to correlate
        it later to the test report via the time stamp. The path points to the
        resultsdir location.
        """
        filename = "%s-%s.%s" % (basename or self.test_name.replace(".", "_"),
                self.GetStartTimestamp(), ext)
        return os.path.join(self.config.resultsdir, filename)

    def GetFile(self, basename=None, ext="log", mode="a+"):
        """Return a file object for a log file in the results location."""
        fname = self.GetFilename(basename, ext)
        return UserFile.UserFile(fname, mode)

    def Sleep(self, Nsecs):
        """Sleep for N seconds.

        Sleep method simply sleeps for specified number of seconds.
        """
        return scheduler.sleep(Nsecs)

    def Schedule(self, delay, cb):
        """Callback scheduler.

        Schedule a function to run 'delay' seconds in the future.
        """
        return scheduler.add(delay, callback=cb)

    def Timed(self, function, args=(), kwargs={}, timeout=30):
        """Run a function with a failsafe timer.

        Call the provided function with a failsafe timeout value. The function
        will be interrupted if it takes longer than `timeout` seconds.
        """
        sched = scheduler.get_scheduler()
        return sched.timeout(function, args, kwargs, timeout)

    def Timedio(self, function, args=(), kwargs={}, timeout=30):
        """Run a function that may block on I/O with a failsafe timer.

        Call the provided function with a failsafe timeout value. The function
        will be interrupted if it takes longer than `timeout` seconds. The
        method should be one that blocks on I/O.
        """
        sched = scheduler.get_scheduler()
        return sched.iotimeout(function, args, kwargs, timeout)

    def RunSubtest(self, _testclass, *args, **kwargs):
        """Invoke another Test class in the same environment as this one.

        Runs another Test subclass with the given arguments passed to the
        `execute()`.
        """
        orig = self.config.report
        if not self._verbose: # don't let the subtest write to the report.
            # if verbose mode then use original report (bug 708716)
            from pycopia import reports
            nr = reports.get_report(("NullReport",))
            self.config.report = nr
        inst = _testclass(self.config)
        try:
            return apply(inst, args, kwargs)
        finally:
            self.config.report = orig

    def RunCommand(self, cmdline, env=None, timeout=None, logfile=None):
        """Run an external command. 

        This method will block until the command returns. An optional timeout
        may be supplied to prevent hanging forever.

        Arguments:
            A string that is the command line to be run. 
            A (optional) dictionary containing the environment variables.
            An (optional) timeout value that will forcibly return if the call
                takes longer than the timeout value.

        Returns:
         A tuple of ExitStatus object and stdout/stderr (string) of the program.
        """
        from pycopia import proctools
        p = proctools.spawnpipe(cmdline, logfile=logfile, env=env)
        try:
            if timeout:
                sched = scheduler.get_scheduler()
                text = sched.iotimeout(p.read, timeout=timeout)
            else:
                text = p.read()
        finally:
            p.wait()
            p.close()
        return p.exitstatus, text

    def Debug(self):
        """Enter The Debugger (starring Bruce Li). 

        Forceably enter the dubugger. Win the prize, escape with your life. 
        Useful when developing tests.
        """
        debugger.set_trace(start=2)

    # runtime flag control
    def SetDebug(self, onoff=1):
        """Turn on or off the DEBUG flag.

        Set the debug flag from a test method. Useful for setting debug flag
        only around questionable code blocks during test development.

        Args:
            onoff: flag (boolean) to set the debug state on or off.
        """
        ov = self._debug
        self._debug = self.config.flags.DEBUG = onoff
        return ov

    def SetVerbose(self, onoff=1):
        """Turn on or off the VERBOSE flag.

        Make reports more, or less, verbose at run time.
        """
        ov = self._verbose
        self._verbose = self.config.flags.VERBOSE = onoff
        return ov

    # for checking verbosity in tests.
    verbose = property(lambda s: s._verbose, SetVerbose)

    def Prerequisites(self):
        """Get the list of prerequisites.

        Returns current list of prerequisite tests, which could be empty.
        """
        return self.OPTIONS.prerequisites

    ### the overrideable methods follow ###
    def initialize(self):
        """Hook method to initialize a test. 

        Override if necessary. Establishes the pre-conditions of the test.
        """
        pass

    def finalize(self, result):
        """Hook method when finalizing a test. 

        Override if necessary. Used to clean up any state in UUT.
        """
        pass

    def execute(self, *args, **kw):
        """The primary test method.

        Overrided this method in a subclass to implement a specific test. All
        primary test logic and control should go here.
        """
        return self.Failed(
                'you must define a method named "execute" in your subclass.')

    # result reporting methods
    def Passed(self, msg=constants.NO_MESSAGE):
        """Call this and return if the execute() passed.

        If your execute determined that the test passed, call this. 
        In a execute, the pattern is: `return self.Passed('message').
        """
        self._report.passed(msg, 2)
        return constants.PASSED

    def Failed(self, msg=constants.NO_MESSAGE):
        """Call this and return if the execute() failed.

        Call this if your test logic determines a failure. Only call this if
        your test implementation in the execute is positively sure that it
        does not meet the criteria. Other kinds of errors should return
        `Incomplete()`. 
        In the execute method, the pattern is: `return self.Failed('message').
        """
        if self.OPTIONS.bugid:
            self._report.diagnostic(
                            "This failure was expected. see bug: %s." % (self.OPTIONS.bugid,), 2)
            self._report.expectedfail(msg, 2)
            return constants.EXPECTED_FAIL
        else:
            self._report.failed(msg, 2)
            return constants.FAILED

    def Incomplete(self, msg=constants.NO_MESSAGE):
        """Test could not complete.

        Call this and return if your test implementation determines that the
        test cannot be completed for whatever reason.
        In a execute, the pattern is: `return self.Incomplete('message').
        """
        self._report.incomplete(msg, 2)
        return constants.INCOMPLETE

    def Abort(self, msg=constants.NO_MESSAGE):
        """Abort the test suite.

        Some drastic error occurred, or some condition is not met, and the
        suite cannot continue. Raises the TestSuiteAbort exception.
        """
        self._report.abort(msg, 2)
        raise TestSuiteAbort

    def Info(self, msg):
        """Informational messages for the report.

        Record non-critical information in the report object. This message is
        not effected by the VERBOSE flag.
        """
        self._report.info(msg, 2)

    def Verboseinfo(self, msg):
        """Verbose informational messages.
 
        Call this to record non-critical information in the report
        object that is only emitted when the VERBOSE flag is set.
        """
        if self._verbose:
            self._report.info(msg, 2)

    def Diagnostic(self, msg):
        """Emit diagnostic message to report.

        Call this one or more times if a failed condition is detected, and you
        want to record in the report some pertinent diagnostic information.
        The diagnostic information is typically some ephemeral state of the
        UUT you want to record.
        """
        self._report.diagnostic(msg, 2)

    # assertion methods make it convenient to check conditions. These names
    # match those in the standard `unittest` module for the benefit of those
    # people using that module.
    def assertPassed(self, arg, msg=None):
        """Assert a sub-test run by the `run_subtest()` method passed.

        Used when invoking test objects as a unit.
        """
        if arg != constants.PASSED:
            raise TestFailError, msg or "Did not pass test."

    def assertFailed(self, arg, msg=None):
        """Assert a sub-test run by the `run_subtest()` method failed.

        Useful for "negative" tests.
        """
        if arg not in (constants.FAILED, constants.EXPECTED_FAIL):
            raise TestFailError, msg or "Did not pass test."

    def assertEqual(self, arg1, arg2, msg=None):
        """Asserts that the arguments are equal,

        Raises TestFailError if arguments are not equal. An optional message
        may be included that overrides the default message.
        """
        if arg1 != arg2:
            raise TestFailError, msg or "%s != %s" % (arg1, arg2)

    def assertNotEqual(self, arg1, arg2, msg=None):
        """Asserts that the arguments are not equal,

        Raises TestFailError if arguments are equal. An optional message
        may be included that overrides the default message.
        """
        if arg1 == arg2:
            raise TestFailError, msg or "%s == %s" % (arg1, arg2)

    def assertGreaterThan(self, arg1, arg2, msg=None):
        """Asserts that the first argument is greater than the second
        argument.
        """
        if not (arg1 > arg2):
            raise TestFailError, msg or "%s <= %s" % (arg1, arg2)

    def assertGreaterThanOrEqual(self, arg1, arg2, msg=None):
        """Asserts that the first argument is greater or equal to the second
        argument.
        """
        if not (arg1 >= arg2):
            raise TestFailError, msg or "%s < %s" % (arg1, arg2)

    def assertLessThan(self, arg1, arg2, msg=None):
        """Asserts that the first argument is less than the second
        argument.
        """
        if not (arg1 < arg2):
            raise TestFailError, msg or "%s >= %s" % (arg1, arg2)

    def assertLessThanOrEqual(self, arg1, arg2, msg=None):
        """Asserts that the first argument is less than or equal to the second
        argument.
        """
        if not (arg1 <= arg2):
            raise TestFailError, msg or "%s > %s" % (arg1, arg2)

    def assertTrue(self, arg, msg=None):
        """Asserts that the argument evaluates to True by Python.

        Raises TestFailError if argument is not True according to Python truth
        testing rules.
        """
        if not arg:
            raise TestFailError, msg or "%s not true." % (arg,)

    def assertFalse(self, arg, msg=None):
        """Asserts that the argument evaluates to False by Python.

        Raises TestFailError if argument is not False according to Python truth
        testing rules.
        """
        if arg:
            raise TestFailError, msg or "%s not false." % (arg,)

    def assertApproximatelyEqual(self, arg1, arg2, fudge=None, msg=None):
        """Asserts that the numeric arguments are approximately equal.

        Raises TestFailError if the second argument is outside a tolerance
        range (defined by the "fudge factor").    The default is 5% of the first
        argument.
        """
        if fudge is None:
            fudge = arg1*0.05
        if abs(arg1-arg2) > fudge:
            raise TestFailError, \
                msg or "%s and %s not within %s units of each other." % \
                        (arg1, arg2, fudge)

    def assertRaises(self, exception, method, args=None, kwargs=None, msg=None):
        """Assert that a method and the given args will raise the given
        exception.

        Args:
            exception: The exception class the method should raise.
            method:    the method to call with the given arguments.
            args: a tuple of positional arguments.
            kwargs: a dictionary of keyword arguments
            msg: optional message string to be used if assertion fails.
        """
        args = args or ()
        kwargs = kwargs or {}
        try:
            rv = method(*args, **kwargs)
        except exception:
            return
        # it might raise another exception, which is marked INCOMPLETE
        raise TestFailError, msg or "%r did not raise %r." % (method, exception)

    # some logical aliases
    failIfEqual = assertNotEqual
    failIfNotEqual = assertEqual
    assertNotTrue = assertFalse
    assertNotFalse = assertTrue
    failUnlessRaises = assertRaises

    # data storage
    def SaveText(self, text, filename=None):
        """Save some text into a file in the results location.

        This may be called multiple times and the file will be appended to.

        Arguments:
            text: A blob of text as a string.
            filename: the base name of the file to write. Default is test name
                plus timestamp.
        """
        if filename is None:
            filename = self.GetFilename("saved", "txt")
        fo = UserFile.UserFile(filename, "a")
        try:
            fo.write(str(text))
        finally:
            fo.close()

    @classmethod
    def OpenFile(cls, fname):
        """Open a data file located in the same directory as the test case
        implmentation.

        Return the file object (actually a UserFile object). Make sure you
        close it.
        """
        fullname = os.path.join(
                    os.path.dirname(sys.modules[cls.__module__].__file__), fname)
        return UserFile.UserFile(fullname)

    def SaveData(self, obj, datatype=constants.DT_PICKLE, note=None, 
                packformat=None):
        """Send an add_data message to the report. The object is serialized into
        a type given by datatype.

        Arguments:
            obj: any python object.
            datatype: Enumeration from DATATYPES indicating the serialized
                format the data will take.
            packformat:    A string formatted according to the `struct` module
                documentation. Only used for the `packed` datatype.
            note: A text note describing the data for future users (optional).
        """
        if datatype == constants.DT_PICKLE:
            import cPickle as pickle
            data = pickle.dumps(obj)
        elif datatype == constants.DT_REPR:
            data = repr(obj)
        elif datatype == constants.DT_TEXT:
            data = str(obj)
        elif datatype == constants.DT_JSON:
            import simplejson
            data = simplejson.dumps(obj)
        elif datatype == constants.DT_PACKED:
            assert type(obj) is tuple, "pack format requires a tuple of basic types"
            assert type(packformat) is str, "need to supply a pack format string"
            import struct
            data = struct.pack(packformat, *obj)
        else:
            raise ValueError, "Unhandled datatype: %s" % (datatype,)
        self._report.add_data(data, datatype, note)

    def AddDatapoint(self, value):
        """Add a datapoint to the list of saved data.
        """
        self.__datapoints.append(value)

# --------------------

class PreReq(object):
    """A holder for test prerequisite.

    Used to hold the definition of a prerequisite test. A prerequisite is a
    Test implementation class plus any arguments it may be called with.
    No arguments means ANY arguments.
    """
    def __init__(self, implementation, args=None, kwargs=None):
        self.implementation = implementation
        self.args = args or ()
        self.kwargs = kwargs or {}

    def __repr__(self):
        return "%s(%r, args=%r, kwargs=%r)" % \
                (self.__class__.__name__, self.implementation, 
                        self.args, self.kwargs)

    def __str__(self):
        return ReprTest(self.implementation, self.args, self.kwargs)


class TestEntry(object):
    """Helper class used to run a Test with arguments and store the result.

    Holds an instance of a Test class and the parameters it will be called
    with.    This actually calls the test, and stores the result value for
    later summary.    It also supports pre-requisite checking.
    """
    def __init__(self, inst, args=None, kwargs=None, autoadded=False):
        self.inst = inst
        self.args = args or ()
        self.kwargs = kwargs or {}
        self._result = constants.INCOMPLETE
        self.autoadded = autoadded # True if automatically added as a prerequisite.

    def Run(self, config=None):
        """Invoke the test with its arguments. The config argument is passed
        when run directly from a TestRunner, but not from a TestSuite. It is
        ignored here.
        """
        try:
            self._result = self.inst(*self.args, **self.kwargs)
        except KeyboardInterrupt:
            self._result = constants.ABORT
            raise
        return self._result

    def __eq__(self, other):
        return self.inst == other.inst

    def _setResult(self, val):
        self._result = val

    result = property(lambda s: s._result, _setResult, 
                doc="The test rusult enumeration.")

    def Matches(self, name, args, kwargs):
        """Test signature matcher.

        Determine if a test name and set of arguments matches this test.
        """
        return (name, args, kwargs) == \
                    (self.inst.test_name, self.args, self.kwargs)

    def MatchPrerequisite(self, prereq):
        """Does this test match the specified prerequisite?

        Returns True if this test matches the supplied PreReq object.
        """
        return (self.inst.test_name, self.args, self.kwargs) == \
                    (prereq.implementation, prereq.args, prereq.kwargs)

    def Prerequisites(self):
        return self.inst.Prerequisites()

    def GetSignature(self):
        """Return a unique identifier for this test entry."""
        try:
            return self._signature
        except AttributeError:
            method_sig = methods.MethodSignature(self.inst.execute)
            arg_sig = repr((self.args, self.kwargs))
            self._signature = (id(self.inst.__class__), arg_sig)
            return self._signature

    signature = property(GetSignature, doc="unique signature string of test.")

    def Abort(self):
        """Abort the test suite.

        Causes this this test, and the suite, to be aborted.
        """
        self._result = self.inst.Abort("Abort forced by suite runner.")
        return self._result

    test_name = property(lambda s: s.inst.test_name)

    def __repr__(self):
        return ReprTest(self.inst.test_name, self.args, self.kwargs)

    def __str__(self):
        return "%s: %s" % (self.__repr__(), self._result)


class SuiteEntry(TestEntry):
    """Entry object that wraps other Suite objects. 

    Used when sub-suites are run as test cases.
    """
    def _get_result(self):
        self._results = self.inst.results
        for res in self._results:
            if res != constants.PASSED:
                self._result = res
                return res
        self._result = constants.PASSED
        return constants.PASSED

    def _setResult(self, val):
        self._result = val
    result = property(lambda s: s._get_result(),
                                        _setResult, None,
        """The test rusult enumeration PASSED if all tests in suite passed.""")

    results = property(lambda s: s._results, None, None,
        """The actual list of test results.""")


def PruneEnd(n, l):
    return l[:n]

class TestEntrySeries(TestEntry):
    """An entry for a series of a test case with a set of parameters.

    Provides an efficient means to add many test case instances without
    having to actually instantiate a TestEntry at suite build time.
    """
    def __init__(self, testinstance, N, chooser, filter, args, kwargs):
        self.inst = testinstance
        self.args = args or ()
        self.kwargs = kwargs or {}
        self._sig = methods.MethodSignature(testinstance.execute)
        self.result = constants.INCOMPLETE # Aggregate test result
        chooser = chooser or PruneEnd
        arglist = []
        if args:
            arglist.extend(args)
        if kwargs:
            for name, default in self._sig.kwarguments:
                try:
                    val = kwargs[name]
                except KeyError:
                    pass
                else:
                    arglist.append(val)
        self._counter = combinatorics.ListCounter(
                                                                combinatorics.prune(N, arglist, chooser))
        if filter:
            assert callable(filter)
            self._filter = filter
        else:
            self._filter = lambda *args, **kwargs: True

    test_name = property(lambda s: s.inst.test_name)

    def Run(self, config=None):
        resultset = {constants.PASSED:0, constants.FAILED:0, constants.INCOMPLETE:0}
        for argset in self._counter:
            kwargs = self._sig.GetKeywordArguments(argset)
            # kwargs also contains non-keyword args, but python maps them to
            # positional args anyway.
            if self._filter(**kwargs):
                entry = TestEntry(self.inst, (), kwargs)
                entryresult = entry.Run()
                resultset[entryresult] += 1
        if resultset[constants.FAILED] > 0:
            self.result = constants.FAILED
        elif resultset[constants.INCOMPLETE] > 0:
            self.result = constants.INCOMPLETE
        elif resultset[constants.PASSED] > 0: # must have all passed, anyway.
            self.result = constants.PASSED
        return self.result


def ReprTest(name, args, kwargs):
    """Produce repr form of test case signature.

    Returns a Test instantiation plus arguments as text (repr).
    """
    return "%s()(%s)" % (name, ReprArgs(args, kwargs))

def ReprArgs(args, kwargs):
    """Stringify a set of arguments.

    Arguments:
        args: tuple of arguments as a function would see it.
        kwargs: dictionary of keyword arguments as a function would see it.
    Returns:
        String as you would write it in a script.
    """
    args_s = aid.IF(args, 
                        aid.IF(kwargs, "%s, ", "%s") % ", ".join(map(repr, args)), 
                        "")
    kws = ", ".join(map(lambda it: "%s=%r" % (it[0], it[1]), kwargs.items()))
    return "%s%s" % (args_s, kws)


def ParseArgs(arguments):
    """Take a string of arguments and keyword arguments and convert back to
    objects.
    """
    # Try a possibly icky method of constructing a temporary function string
    # and exec it (leverage Python parser and argument handling).
    ANY = None # To allow "ANY" keyword in prereq spec.
    def _ArgGetter(*args, **kwargs):
        return args, kwargs
    funcstr = "args, kwargs = _ArgGetter(%s)\n" % arguments
    exec funcstr in locals()
    return args, kwargs # set by exec call


class TestSuite(object):
    """A Test holder and runner.

    A TestSuite contains a set of test cases (subclasses of Test class) that
    are run sequentially, in the order added. It monitors abort status of
    each test, and aborts the suite if required. 

    To run it, create a TestSuite object (or a subclass with some methods
    overridden), add tests with the `AddTest()` method, and then call the
    instance. The 'initialize()' method will be run with the arguments given
    when called.
    """
    def __init__(self, cf, nested=0):
        self.config = cf
        self.report = cf.report
        self._debug = cf.flags.DEBUG
        self._tests = []
        self._testset = set()
        self._multitestset = set()
        self._nested = nested
        self.suite_name = self.__class__.__name__
        cl = self.__class__
        self.test_name = "%s.%s" % (cl.__module__, cl.__name__)
        self.result = None
        self._merge_config()

    def _merge_config(self):
        # Merge any test-suite specific config files. Config file name is the
        # name of the suite class plus ".conf", located in the same directory
        # as the module it's in.
        cl = self.__class__
        mod = sys.modules[cl.__module__]
        # merge module config
        modconf = os.path.join(os.path.dirname(mod.__file__), 
                    "%s.conf" % (mod.__name__.split(".")[-1],))
        if self.config.mergefile(modconf):
            self.config.evalupdate(self.config.options_override)
        # merge suite config
        suiteconf = os.path.join(os.path.dirname(mod.__file__), 
                    "%s.conf" % (cl.__name__,))
        if self.config.mergefile(suiteconf):
            self.config.evalupdate(self.config.options_override)

    def __iter__(self):
        return iter(self._tests)

    def _get_results(self):
        return map(lambda t: t.result, self._tests)
    results = property(_get_results)

    def _addWithPrereq(self, entry):
        """Add a TestEntry instance to the list of tests.

        Also adds any prerequisites, if not already present, recursively.
        """
        for prereq in entry.inst.OPTIONS.prerequisites:
            pretestclass = module.GetObject(prereq.implementation)
            preentry = TestEntry(pretestclass(self.config),
                                                                                     prereq.args, prereq.kwargs, True)
            presig, argsig = preentry.GetSignature()
            if presig not in self._multitestset:
                self._addWithPrereq(preentry)
        testcaseid = entry.GetSignature()
        if testcaseid not in self._testset:
            self._testset.add(testcaseid)
            self._tests.append(entry)

    def AddTest(self, _testclass, *args, **kwargs):
        """Add a Test subclass and its arguments to the suite.

    Appends a test object in this suite. The test's `execute()` will be
    called (at the appropriate time) with the arguments supplied here. If
    the test case has a prerequisite defined it is checked for existence in
    the suite, and an exception is raised if it is not found.
    """
        if isinstance(_testclass, str):
            _testclass = module.GetClass(_testclass)
        _testclass.set_test_options()
        testinstance = _testclass(self.config)
        entry = TestEntry(testinstance, args, kwargs, False)
        self._addWithPrereq(entry)
    # alias method names for backwards compatibility
    addTest = AddTest
    add_test = AddTest

    def AddTestFromResult(self, dbtestresult):
        """Add a Test from information taken from a TestResult model object.

        This basically means duplicate the test call that originated that test
        result.
        """
        testclass = module.GetClass(dbtestresult.testimplementation)
        testclass.set_test_options()
        args, kwargs = ParseArgs(dbtestresult.arguments)
        testinstance = testclass(self.config)
        entry = TestEntry(testinstance, args, kwargs, False)
        self._addWithPrereq(entry)

    def AddIncompleteTests(self, queryset):
        """Add test cases from TestResult queryset that were INCOMPLETE."""
        for testresult in queryset.is_incomplete():
            self.AddTestFromResult(testresult)

    def AddTestSeries(self, _testclass, N=100, chooser=None, filter=None, 
                                        args=None, kwargs=None):
        """Add a Test case as a series. 

        The arguments must be lists of possible values for each parameter. The
        args and kwargs arguments are lists that are combined in all possible
        combinations, except pruned to N values. The pruning policy can be
        adjusted by the chooser callback, and the N value itself.

        Args:
            testclass (class): the Test class object (subclass of core.Test).

            N (integer): Maximum iterations to take from resulting set. Default
                    is 100 just to be safe.

            chooser (callable): callable that takes one number and a list
                    argument, returns a list of the specified (N) length. 
                    Default is to chop off the top end of the list.

            filter (callable): callable that takes a set of arguments with the
                    same semantics as the Test.execute() method and returns True or
                    False to indicate if that combination should be included in the
                    test. You might want to set a large N if you use this.

            args (tuple): tuple of positional arguments, each argument is a list.
                                        example: args=([1,2,3], [4,5]) maps to positional
                                        argumnts of execute() method of Test class.

            kwargs (dict): Dictionary of keyword arguments, with list of values
                    as value.
                                        example: kwargs={"arg1":["a", "b", "c"]}
                                        maps to keyword arguments of execute() method of Test
                                        class.
        """
        if isinstance(_testclass, str):
            _testclass = module.GetClass(_testclass)
        _testclass.set_test_options()
        testinstance = _testclass(self.config)
        try:
            entry = TestEntrySeries(testinstance, N, chooser, filter, args, kwargs)
        except ValueError, err: # ListCounter raises this if there is an empty list.
            self.Info("addTestSeries Error: %s. Not adding %s as series." % (
                    err, _testclass.__name__))
        else:
            # series tests don't get auto-added (can't know what all the args
            # are, and even so the set could be large.)
            mysig, myargsig = entry.GetSignature()
            self._multitestset.add(mysig) # only add by id.
            self._addWithPrereq(entry)

    def AddSuite(self, suite, test_name=None):
        """Add an entire suite of tests to this suite.

    Appends an embedded test suite in this suite. This is called a sub-suite
    and is treated as a single test by this containing suite.
    """
        if isinstance(suite, str):
            suite = module.GetClass(suite)
        if type(suite) is type(Test): # class type
            suite = suite(self.config, 1)
        else:
            suite.config = self.config
            suite._nested = 1
        self._tests.append(SuiteEntry(suite))
        # sub-tests need unique names
        if test_name:
            suite.test_name = test_name
        else:
            # Name plus index into suite list.
            suite.test_name = "%s-%s" % (suite.test_name, len(self._tests)-1)
        return suite

    def Add(self, klass, *args, **kwargs):
        """Add a Suite or a Test to this TestSuite.

    Most general method to add test case classes or other test suites.
    """
        if type(klass) is type:
            if issubclass(klass, Test):
                self.addTest(klass, *args, **kwargs)
            elif issubclass(klass, TestSuite):
                self.addSuite(klass, *args, **kwargs)
            else:
                raise ValueError, "TestSuite.add: invalid class type."
        else:
                raise ValueError, "TestSuite.add: need a class type."

    def GetTestEntries(self, name, *args, **kwargs):
        """Get a list of test entries that matches the signature.

        Return a list of Test entries that match the name and calling
        arguments.
        """
        for entry in self._tests:
            if entry.matches(name, args, kwargs):
                yield entry

    def AddArguments(self, name, args, kwargs):
        """Add calling arguments to an existing test entry that has no
        arguments.
        """
        for entry in self.getTestEntries(name):
            entry.addArguments(args, kwargs)

    def Info(self, msg):
        """Informational messages for the report.

        Record non-critical information in the report object.
        """
        self.report.info(msg, 1)

    def Prerequisites(self):
        """Get the list of prerequisites.

        This is here for polymorhism with Test objects. Always return empty list.
        """
        return ()

    def Run(self, config=None):
        """Called when run directly from the testrunner."""
        if config:
            self.config = config
            self.report = config.report
            self._debug = config.flags.DEBUG
        return self.__call__()

    def GetStartTimestamp(self):
        return timelib.strftime("%m%d%H%M%S", timelib.localtime(self.starttime))

    def __call__(self, *args, **kwargs):
        """Invoke the test suite.

        This is the primary way to invoke a suite of tests. call the instance.
        Any supplied parameters are passed onto the suite's initialize()
        method. The method name is consistent with other methods of a similiar
        nature on other objects (e.g. app.run()).
        """
        self.starttime = timelib.now()
        try:
            self._initialize(*args, **kwargs)
        except TestSuiteAbort:
            self._finalize()
            rv = constants.INCOMPLETE
        else:
            self._runTests()
            rv = self._finalize()
        endtime = timelib.now()
        self.report.add_message("STARTTIME", self.starttime, 1)
        self.report.add_message("ENDTIME", endtime, 1)
        return rv

    def _initialize(self, *args, **kwargs):
        """initialize phase handler for suite-level initialization.

        Handles calling the user `initialize()` method, and handling
        interrupts, reporting, and invoking the debugger if the DEBUG flag is
        set.
        """
        self.report.add_heading(self.test_name, 1)
        if self.config.flags.VERBOSE:
            s = ["Tests in suite:"]
            for i, entry in enumerate(self._tests):
                s.append("%3d. %r" % (i + 1, entry))
            self.report.info("\n".join(s), 1)
            del s
        try:
            self.initialize(*args, **kwargs)
        except KeyboardInterrupt:
            self.Info("Suite aborted by user in initialize().")
            raise TestSuiteAbort
        except:
            ex, val, tb = sys.exc_info()
            if self._debug:
                ex, val, tb = sys.exc_info()
                debugger.post_mortem(tb, ex, val)
            self.Info("Suite failed to initialize: %s (%s)" % (ex, val))
            raise TestSuiteAbort, val

    def CheckPrerequisites(self, currententry, upto):
        """Verify that the prerequisite test passed.

        Verify any prerequisites are met at run time.
        """
        for prereq in currententry.Prerequisites():
            for entry in self._tests[:upto]:
                if entry.MatchPrerequisite(prereq):
                    if entry.result == constants.PASSED:
                        continue
                    else:
                        self.report.add_heading(currententry.inst.test_name, 2)
                        self.report.diagnostic("Prerequisite: %s" % (prereq,), 2)
                        self.report.incomplete("Prerequisite did not pass.", 2)
                        currententry.result = constants.INCOMPLETE
                        return False
        return True # No prerequisite or prereq passed.

    def _runTests(self):
        """Runs all the tests in the suite. 

        Handles running the TestEntry, reporting interrupts, checking for
        abort conditions, If a Test returns None (the default), it is reported
        as a failure since it was not written correctly.
        """
        for i, entry in enumerate(self._tests):
            if not self.CheckPrerequisites(entry, i):
                continue
            # merge any test-class specific configuration.
            cl = entry.inst.__class__
            testconf = os.path.join(
                    os.path.dirname(sys.modules[cl.__module__].__file__), 
                        "%s.conf" % (cl.__name__,))
            self.config.mergefile(testconf)
            self.config.evalupdate(self.config.options_override)
            # Add a note to the logfile to delimit test cases there.
            if self.config.flags.VERBOSE:
                self.config.logfile.note("%s: %r" % (timelib.localtimestamp(), entry))
            try:
                rv = entry.Run()
            except KeyboardInterrupt:
                if self._nested:
                    raise TestSuiteAbort, "Sub-suite aborted by user."
                else:
                    if self.config.UI.yes_no("Test interrupted. Abort suite?"):
                        self.Info("Test suite aborted by user.")
                        break
            except TestSuiteAbort, err:
                self.Info("Suite aborted by test %s (%s)." % (entry.test_name, err))
                entry.result = constants.INCOMPLETE
                rv = constants.ABORT
                break
            # This should only happen with an incorrectly written execute() method.
            if rv is None:
                self.report.diagnostic(
                        "warning: test returned None, assuming Incomplete. "
                        "Please fix the %s.execute() method." % (entry.test_name))
                rv = constants.INCOMPLETE
            # check for abort condition and break the loop if so
            if rv == constants.ABORT:
                break

    def _finalize(self):
        """Run the finalize phase for suite level.

        Runs the user finalize and aborts the suite on error or interrupt. If
        this is a sub-suite then TestSuiteAbort is raised so that the
        top-level suite can handle it.
        """
        try:
            self.finalize()
        except KeyboardInterrupt:
            if self._nested:
                raise TestSuiteAbort, \
                            "Suite '%s' aborted by user in finalize()." % (self.suite_name,)
            else:
                self.Info("Suite aborted by user in finalize().")
        except:
            ex, val, tb = sys.exc_info()
            if self._debug:
                print # ensure debugger prompts starts on new line.
                debugger.post_mortem(tb, ex, val)
            self.Info("Suite failed to finalize: %s (%s)" % (ex, val))
            if self._nested:
                raise TestSuiteAbort, \
                        "subordinate suite '%s' failed to finalize." % (self.test_name,)
        self._reportSummary()
        return self.result

    def _reportSummary(self):
        """Summarize the results.

        Place a summary in the report that list all the test results.
        """
        self.report.add_heading(
                    "Summarized results for %s." % self.__class__.__name__, 3)
        entries = filter(lambda te: te.result is not None, self._tests)
        self.report.add_summary(entries)
        # check and report suite level result
        for entry in self._tests:
            if entry.result in (constants.FAILED, constants.INCOMPLETE,
                        constants.ABORT):
                result = constants.FAILED
                break
            elif entry.result is None:
                result = constants.INCOMPLETE
                break
        else:
            result = constants.PASSED
        self.result = result
        resultmsg = "Aggregate result for %r." % (self.test_name,)
        if not self._nested:
            if result == constants.PASSED:
                self.report.passed(resultmsg)
            elif result == constants.FAILED:
                self.report.failed(resultmsg)
            elif result == constants.INCOMPLETE:
                self.report.incomplete(resultmsg)

    def __str__(self):
        s = ["Tests in suite:"]
        s.extend(map(str, self._tests))
        return "\n".join(s)

    ### overrideable interface. ###
    def initialize(self, *args, **kwargs):
        """
        Override this if you need to do some initialization just before the
        suite is run. This is called with the arguments given to the TestSuite
        object when it was called.
        """ 
        pass

    def finalize(self):
        """
        Override this if you need to do some clean-up after the suite is run.
        """
        pass


def timestamp(t):
    return timelib.strftime("%a, %d %b %Y %H:%M:%S %Z", timelib.localtime(t))



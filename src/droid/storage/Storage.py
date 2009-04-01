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


# Keith Dart <keith@dartworks.biz>
# Copied from Gtest framework and modified.

"""Droid Configuration Storage.

Provides a persistent storage of objects for the Droid QA framework.
This is based on Durus <http://www.mems-exchange.org/software/durus/>
persistence framework.

The primary interface to the global configuration and database is the
RootContainer object. 

The RootContainer (which ends up as the "config" attribute of a test case)
is a hierarchical context and data storage object. It has methods
and attributes to get various kinds of objects from the configuration.

It also provides access to the framework database. Since the database uses
the Django ORM the API here fully Pythonic. In most cases objects are
retrieved by attribute access. This means a dot-delimited "path" name can
address any object in the system. This includes non-relational persistent
data and relational tabular data.

"""

__author__ = 'dart@google.com (Keith Dart)'


import sys
import os
import re
import itertools

from durus.client_storage import ClientStorage
from durus.file_storage import FileStorage
from durus.connection import Connection
from durus.persistent_dict import PersistentDict
from durus.persistent_list import PersistentList

from pycopia.durusplus.persistent_attrdict import PersistentAttrDict
from pycopia.aid import flatten, IF, removedups
from pycopia.dictlib import AttrDict

from droid import labmodel

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 2990

class Error(Exception):
  pass

class ConfigError(Error):
  pass

class ConfigMergeError(Error):
  pass

class NoSuchReport(Error):
  """No report with the given reportname was found.
  The argument will be a list of valid names."""


class Container(object):
  """General persistent container wrapper.

  Wrapper for a persistent dictionary providing attribute-style access.
  This class API is similar to a Python dictionary, or more specifically
  an AttrDict object. It wraps the Durus container and adds attribute
  style access and other methods.

  This object is analogous to a directory in a file system.
  """
  def __init__(self, container):
    self.__dict__["_container"] = container

  def __repr__(self):
    return "<Container>"

  # wrap any obtained PersistentDict objects to Container objects.
  def __getitem__(self, key):
    obj = self._container[key]
    if isinstance(obj, (PersistentDict, PersistentAttrDict)):
      return Container(obj)
    else:
      return obj

  def __setitem__(self, key, value):
    self._container[key] = value

  def __delitem__(self, key):
    del self._container[key]

  def get(self, key, default=None):
    try:
      return self.__getitem__(key)
    except KeyError:
      return default

  def _get_dict(self, name):
    d = self._container
    path = name.split(".")
    for part in path[:-1]:
      d = d[part]
    return d, path[-1]

  def getpath(self, key, default=None):
    """Get a leaf node given a dot-delimited path.

    given a name, or a dot-delimited path name, get the object by name.
    """
    d, key  = self._get_dict(key)
    if d is self._container:
      obj = self._container[key]
    else:
      try:
        obj = getattr(d, key) # use getattr to allow property objects to
                              # work.
      except (KeyError, AttributeError, NameError):
        return default
    if isinstance(obj, (PersistentDict, PersistentAttrDict)):
      return Container(obj)
    else:
      return obj

  def set(self, key, obj):
    """Set a key name to a value object.

    Set an object by name, to any object.
    """
    self._container[key] = obj

  def delete(self, key):
    """Delete an object by name.
    """
    del self._container[key]

  def rename(self, oldkey, newkey):
    """Rename an object.

    Given the old name, rename the entry to a new name.
    """
    obj = self._container[oldkey]
    self._container[newkey] = obj
    del self._container[oldkey]

  # attribute-style access to container contents
  def __getattribute__(self, key):
    try:
      return super(Container, self).__getattribute__(key)
    except AttributeError:
      try:
        return self.__dict__["_container"].__getattribute__( key)
      except AttributeError:
        try:
          obj = self.__dict__["_container"].__getitem__(key)
          if isinstance(obj, (PersistentDict, PersistentAttrDict)):
            return Container(obj) # wrap the returned mapping object also
          else:
            return obj
        except KeyError:
          raise AttributeError, "Container: No attribute or key '%s' found." % (key, )

  def __setattr__(self, key, obj):
    if self.__class__.__dict__.has_key(key): # to force property access
      object.__setattr__(self, key, obj)
    elif self.__dict__.has_key(key): # existing local attribute
      self.__dict__[key] =  obj
    else:
      self.__dict__["_container"].__setitem__(key, obj)

  def __delattr__(self, key):
    try: # to force handling of properties
      self.__dict__["_container"].__delitem__(key)
    except KeyError:
      object.__delattr__(self, key)


class RootContainer(object):
  """Root container and data interface.

  Primarily a dictionary-like interface to persistent configuration data.

  The root container is special, It looks like a Container (mapping)
  object, but also contains the computed (property) objects. The objects
  that are "expensive" to produce, or are singletons, are cached in a
  local cache. Any variables added at runtime by a test are also
  considered temporary and are placed in the cache, and not made
  persistent.

  This is the object that is called the "config" attribute that tests and
  test suites get. Consider it a "bag of stuff", or a context that tests
  can use to pull information or other objects out of.

  """
  def __init__(self, connection, container, cache=None):
    self.__dict__["_connection"] = connection
    self.__dict__["_container"] = container
    # local, non-persistent cache for computed and temporary variables
    self.__dict__["_cache"] = cache or AttrDict()

  def __repr__(self):
    return "<RootContainer>"

  def commit(self):
    """Commit changes to permanent storage.

    Changes made to the persistent container are not written to permanent
    storage until this is called.
    """
    self._connection.commit()

  def abort(self):
    """Abort any changes.

    Backs out changes made to the persistent container.
    """
    self._connection.abort()

  def pack(self):
    """Pack the persistent storage.

    Packs to persistent storage to make more efficient use of space.
    """
    self._connection.pack()

  def close(self):
    """close cached objects and clean up.
    """
    d = self.__dict__["_cache"]
    self.__dict__["_cache"] = AttrDict()
    for obj in d.values():
      try:
        d.close()
      except:
        pass
    self.__dict__["_connection"] = None
    self.__dict__["_container"] = None

  # attribute-style access to container contents, also prefer the local cache.
  def __getattribute__(self, key):
    try:
      return super(RootContainer, self).__getattribute__(key)
    except AttributeError:
      try:
        return self.__dict__["_container"].__getattribute__( key)
      except AttributeError:
        try:
          # check the local cache first, overrides persistent storage
          obj = self.__dict__["_cache"].__getitem__(key)
          if isinstance(obj, (PersistentDict, PersistentAttrDict)):
            return Container(obj)
          else:
            return obj
        except KeyError:
          pass
        try:
          obj = self.__dict__["_container"].__getitem__(key) # the persistent container
          if isinstance(obj, (PersistentDict, PersistentAttrDict)):
            return Container(obj)
          else:
            return obj
        except KeyError:
          raise AttributeError, "RootContainer: No attribute or key '%s' found." % (key, )

  def __setattr__(self, key, obj):
    if self.__class__.__dict__.has_key(key): # to force property access
      object.__setattr__(self, key, obj)
    elif self.__dict__.has_key(key): # existing local attribute
      self.__dict__[key] =  obj
    else:
      self.__dict__["_cache"].__setitem__(key, obj)

  def __delattr__(self, key):
    try:
      self.__dict__["_cache"].__delitem__(key)
    except KeyError:
      object.__delattr__(self, key)

  def copy(self):
    return self.__class__(self._connection, self._container.copy(), self._cache.copy())

  # can get dot-delimited names from the root, for convenience.
  def _get_dict(self, name):
    d = self._container
    path = name.split(".")
    for part in path[:-1]:
      d = d[part]
    return d, path[-1]

  def __getitem__(self, key):
    try:
      return self._cache[key]
    except (AttributeError, KeyError, NameError):
      pass
    d, key  = self._get_dict(key)
    if d is self._container:
      obj = self._container[key]
    else:
      try:
        obj = getattr(d, key)
      except (KeyError, AttributeError, NameError):
        raise KeyError, "RootContainer: key %r not found." % (key,)
    if isinstance(obj, (PersistentDict, PersistentAttrDict)):
      return Container(obj)
    else:
      return obj

  def __setitem__(self, key, value):
    if self._cache.has_key(key):
      self._cache[key] = value
    else:
      d, key = self._get_dict(key)
      d[key] = value

  def __delitem__(self, key):
    if self._cache.has_key(key):
      del self._cache[key]
    else:
      d, key = self._get_dict(key)
      del d[key]

  def get(self, name, default=None):
    """Get a value given the key name, or a default.

    Like the standard dictionary `get()` method.
    """
    try:
      obj = self._cache[name]
    except KeyError:
      d, name  = self._get_dict(name)
      if d is self._container:
        #obj = self._container.get(name, default)
        try:
          obj = getattr(self, name)
        except (KeyError, AttributeError, NameError):
          return default
      else:
        try:
          obj = d[name]
        except KeyError:
          return default
    if isinstance(obj, (PersistentDict, PersistentAttrDict)):
      return Container(obj)
    else:
      return obj

  def set(self, key, obj):
    """Set any leaf node.

    Sets the leaf node given by key to any value. If the key contains dots
    (.) then the change is made in the addressed sub-container.
    """
    d, key = self._get_dict(key)
    d[key] = obj

  def delete(self, key):
    """Delete a path name.
    """
    d, key = self._get_dict(key)
    del d[key]

  def keys(self):
    """Return list of key values.

    Reflects current set of keys, combining container keys and cached
    keys.
    """
    return removedups(self._container.keys()+self._cache.keys())

  def has_key(self, key):
    """Check for existence of a key.

    Returns a boolean of True if persistent container OR the cache has the
    key.
    """
    return self._container.has_key(key) or self._cache.has_key(key)

  def iteritems(self):
    return itertools.chain(self._cache.iteritems(), self._container.iteritems())

  def iterkeys(self):
    return itertools.chain(self._cache.iterkeys(), self._container.iterkeys())

  def itervalues(self):
    return itertools.chain(self._cache.itervalues(), self._container.itervalues())

  def addContainer(self, name):
    """Add a new Container object to the storeage.

    Automatically commits it.
    """
    obj = PersistentAttrDict()
    self._container[name] = obj
    self._connection.commit()
    return obj

  def mergefile(self, filename):
    """Merge a configuration file.

    Reads a file and adds it to this configuration. Files update the local
    cache only. The file must be able to be evaluated by the Python
    interpreter. Any object assignments in there are made to this
    container.
    """
    if os.path.isfile(filename):
      gb = dict(self._container)
      try:
        execfile(filename, gb, self._cache)
      except:
        ex, val, tb = sys.exc_info()
        raise ConfigMergeError("%s:%s" % (ex, val))
      else:
        return True
    else:
      return False # no config

  def update(self, other):
    """Update this container from a dictionary.

    Updates done from external dicts only update the local cache. If you
    want it persistent, enter it into the persistent store another way.
    """
    for k, v in other.items():
      d, k = self._GetCacheContainer(k)
      # Use setattr for attribute-dicts, properties, and other objects.
      setattr(d, k, v) 

  def setdefault(self, key, val):
    d, key = self._GetCacheContainer(key)
    return d.setdefault(key, val) 

  def evalset(self, k, v):
    """Set the key to the evaluated value.

    Evaluates the (string) value in the context of this container, and
    sets the container key to map to the result.  Useful for specifying
    objects from string-sources, such as the command line. 
    """
    if type(v) is str:
      try:
        v = eval(v, globals(), self._container)
      except:
        if __debug__:
          ex, val, tb = sys.exc_info()
          print >>sys.stderr, "RootContainer conversion warning:", ex, val
          print >>sys.stderr, repr(v)

    d, k = self._GetCacheContainer(k)
    # Use setattr for attribute-dicts, properties, and other objects.
    setattr(d, k, v) 

  def _GetCacheContainer(self, key):
    """Get the subcontainer if the key has a dot in it (representing a
    path).
    """
    d = self._cache
    container = self._container
    path = key.split(".") # allows for keys with dot-path 
    for part in path[:-1]:
      try:
        d = d[part]
      except KeyError:
        # if a container is being overridden then the whole contents
        # must be copied.
        container = container[part].copy()
        d[part] = container
        d = d[part]
    return d, path[-1]

  def evalupdate(self, other):
    """Evaluate the values in the mapping and update this container.

    Like a dictionary update, but the values are evaluated in the context
    of this container and this container's key is mapped to the result of
    that. 
    """
    for k, v in other.items():
      self.evalset(k, v)

  _var_re = re.compile(r'\$([a-zA-Z0-9_\?]+|\{[^}]*\})')

  def expand(self, value):
    """Expand a string that contains dollar prefixes ($).

    Any dollar-prefix is expanded to the value contained in this
    container. The objects string representation is then inserted back
    into the string in place of the name. This is Posix shell-like
    variable expansion.
    """
    if '$' not in value:
      return value
    i = 0
    while 1:
      m = self._var_re.search(value, i)
      if not m:
        return value
      i, j = m.span(0)
      oname = vname = m.group(1)
      if vname.startswith('{') and vname.endswith('}'):
        vname = vname[1:-1]
      tail = value[j:]
      value = value[:i] + str(self.get(vname, "$"+oname))
      i = len(value)
      value += tail

  ### computed attributes (properties) and object constructors follow ###

  changed = property(lambda s: bool(s._connection.changed), None, None,
      """Boolean indicating if persistent container has changed.""")

  reportpath = property(lambda s: os.path.join(s.logfiledir, s.reportfilename),
      None, None, """Full path to the report file.""")

  def getReport(self):
    """Report object constructor.

    Builds the report object, or returns the previously built one from the
    cache. The report is specified by a description fetched from the
    "reports" namespace. The name is pre-selected by setting the
    "reportname" variable in this container.
    """
    if self._cache.get("_report") is None:
      rep = self._buildReport(None)
      self._cache["_report"] = rep
      return rep
    else:
      return self._cache["_report"]

  def _buildReport(self, name):
    """Does the actual report construction. 

    Given a name of a definition found in the "reports" namespace of this
    configuration, return the resulting report object.
    """
    from pycopia import reports
    if name is None:
      name = self.get("reportname", "default") 
    paramlist = []
    for n in name.split(","):
      spec = self.reports.get(n)
      if spec is not None:
        paramlist.append(spec)
    if len(paramlist) == 0:
        raise NoSuchReport, self.reports.keys()
    paramlist = flatten(paramlist)
    paramlist = map(self._param_expand, paramlist)
    # passing a list results in a stacked report
    if len(paramlist) == 1:
      return reports.get_report(paramlist[0])
    else:
      return reports.get_report(paramlist)

  # reconstruct the report parameter list with dollar-variables expanded.
  def _param_expand(self, tup):
    rv = []
    for arg in tup:
      if type(arg) is str:
        rv.append(self.expand(arg))
      else:
        rv.append(arg)
    return tuple(rv)

  def setReport(self, reportname):
    """Set the report object to a pre-constructed report.

    If you have a report object from elsewhere, you can place it into this
    storage cache. Or, if you supply a string, a report is construct using
    the string as the reportname.
    """
    if type(reportname) is str:
      rep = self._buildReport(reportname)
      self._cache["_report"] = rep
    else:
      self._cache["_report"] = reportname # hopefully a report object already

  def delReport(self):
    """Remove the report object from the cache.
    """
    self._cache["_report"] = None

  report = property(getReport, setReport, delReport, "The report object.")

  def getLogfile(self):
    """Get a log file.

    Get a log file (a ManagedLog object defined in the logfile module).
    This is a self-rotating and size-capped file you can write to. Most
    device configurator objects get the log file constructed here. Set the
    variable "logfilesize" to get a max size other than the default of
    1,000,000 bytes.

    If the log file could not be obtained for some reason then None is
    returned.
    """
    from pycopia import logfile
    if self._cache.get("_logfile") is None:
      logfilename = self.getLogfilename()
      lf = logfile.ManagedLog(logfilename, self.get("logfilesize", 1000000))
      self._cache["_logfile"] = lf
      return lf
    else:
      return self._cache["_logfile"]

  def setLogfile(self, lf=None):
    """Set the log file object.

    Set the container cache to the given object. It shold be a file-like
    object.
    """
    self._cache["logfile"] = lf

  def delLogfile(self):
    """Remove the logfile object from cache. Also closes it."""
    try:
      self._cache["_logfile"].flush()
      self._cache["_logfile"].close()
    except:
      pass
    self._cache["_logfile"] = None

  logfile = property(getLogfile, setLogfile, delLogfile, "ManagedLog object")

  def getLogfilename(self):
    """Get the full path to the base log file name.

    Expands the logfiledir variable and combines it with the logbasename
    (set by the test runner), and returns the result.
    """
    return os.path.join(self.getLogfileDir(), self.logbasename)

  logfilename = property(getLogfilename, None, None, 
          """The logfile object's path name.""")

  def getLogfileDir(self):
    lfdir = os.path.join(
          os.path.expandvars(os.path.expanduser(self.logdirbase)), 
          "%s_logs" % (os.environ.get("USER", "nouser"),))
    if not os.path.isdir(lfdir):
      os.makedirs(lfdir)
    return lfdir

  logfiledir = property(getLogfileDir, None, None, 
            "Directory where user logs are placed.")

  def _get_environment(self):
    """Get the EnvironmentRuntime object defined by the test configuration.

    Takes the attribute "environmentname" defined in the users configuration
    or elsewhere and returns the EnvironmentRuntime wrapping the
    Environment object from the database.
    """
    if self._cache.get("_environment") is None:
      name = self.get("environmentname", "default")
      if name:
        env = labmodel.EnvironmentRuntime(self)
        self._cache["_environment"] = env
      else:
        raise ConfigError, "Bad environment %r." % (name,)
    return self._cache["_environment"]

  def _del_environment(self):
    self._cache["_environment"] = None

  environment = property(_get_environment, None, _del_environment)

  # user interface for interactive tests.

  def GetUserInterface(self):
    if self._cache.get("_UI") is None:
      ui = self._BuildUserInterface()
      self._cache["_UI"] = ui
      return ui
    else:
      return self._cache["_UI"]

  def _BuildUserInterface(self):
    from pycopia import UI
    uitype = self.get("userinterfacetype", "default")
    params = self.userinterfaces.get(uitype)
    if params:
      params = self._param_expand(params)
    else:
      params = self.userinterfaces.get("default")
    return UI.get_userinterface(*params)

  def DelUserInterface(self):
    """Remove the UI object from the cache.  """
    ui = self._cache.get("_UI")
    self._cache["_UI"] = None
    if ui:
      try:
        ui.close()
      except:
        pass

  UI = property(GetUserInterface, None, DelUserInterface, 
            "User interface object used for interactive tests.")




#### Persistent storage access ####

class _DB(object):
  """Base class for the Durus connection.

  This unifies the Durus ClientStorage and FileStorage interface and
  provides a container constructor.
  """
  def getRoot(self, cache=None, initializer=None):
    root = self._connection.get_root()
    if len(root) == 0: # auto-initialize empty storage
      if callable(initializer):
        initializer(root)
      else:
        _initialize(root) # default initializer
      self._connection.commit()
    return RootContainer(self._connection, root, cache)

  connection = property(lambda s: s._connection)
  root = property(getRoot)
  changed = property(lambda s: bool(s._connection.changed))

  def commit(self):
    self._connection.commit()

  def abort(self):
    self._connection.abort()

  def pack(self):
    self._connection.pack()

  def addContainer(self, dst, name):
    obj = PersistentAttrDict()
    dst[name] = obj
    self._connection.commit()
    return obj

class DBClient(_DB):
  """A connection to a Durus ClientStorage."""
  def __init__(self, host, port):
    self._connection = Connection(ClientStorage(host=host, port=port))

class DBFile(_DB):
  """A connection to a Durus FileStorage."""
  def __init__(self, filename):
    self._connection = Connection(FileStorage(filename))


def GetClient(config=None):
  """Get a Durus ClientStorage.

  This gets parameters from the external configuration file. The "host"
  and "port" values are used from this file. The file is
  /etc/droid/storage.conf.
  """
  if config is None:
    from pycopia import basicconfig
    config = basicconfig.get_config(
                      os.path.join("/", "etc", "droid", "storage.conf"))
  host = config.get("host", DEFAULT_HOST)
  port = config.get("port", DEFAULT_PORT)
  return DBClient(host, port)

def GetStorage(config=None):
  """Get a Durus FileStorage.

  This gets parameters from the external configuration file. The "dbfile"
  value is used from this file. The file is /etc/droid/storage.conf.
  """
  if config is None:
    from pycopia import basicconfig
    config = basicconfig.get_config(os.path.join("/", "etc", 
                    "droid", "storage.conf"))
  filename = config.get("dbfile")
  if filename:
    return DBFile(os.path.expandvars(os.path.expanduser(filename)))
  else:
    raise ValueError, "no file name supplied or found in configuration."


def GetConfig(extrafiles=None, initdict=None, clientconfig=None, 
              initializer=None):
  """Primary configuration constructor.

  Returns a RootContainer instance containing configuration parameters.
  An extra dictionary may be merged in with the 'initdict' parameter.  And
  finally, extra options may be added with keyword parameters when calling
  this. It also merges in configuration values found in the user-private
  "~/.droidrc" configuration file.

  """
  SOURCES = []
  # user-private configuration overrides
  SOURCES.append(os.path.join(os.environ["HOME"], ".droidrc"))

  if type(extrafiles) is str:
    extrafiles = [extrafiles]
  if extrafiles:
    FILES = SOURCES + extrafiles
  else:
    FILES = SOURCES
  db = GetClient(clientconfig)
  if not db:
    raise ValueError, "Unable to get storage. Check your configuration."
  cache = AttrDict()
  cache["Container"] = AttrDict
  cf = db.getRoot(cache, initializer)
  # copy default flags to cache so they don't get altered in persistent
  # storage.
  cache.flags = cf["flags"].copy()
  # merge in extra configuration files.
  for f in FILES:
    cf.mergefile(f)
  # merge in extra dictionary, if provided.
  if type(initdict) is dict:
    cf.evalupdate(initdict)
  return cf

get_config = GetConfig # alias for backward compatibility


def _initialize(db):
  """Initial persistent storage values.

  Performs an initial set up of the persistent storage. This usually only
  runs once, when first installing. 
  """
  db["flags"] = PersistentAttrDict()
  db["flags"].VERBOSE = 0 # levels of verbosity
  db["flags"].DEBUG = 0 # levels of debugging
  db["flags"].NONOTE = False # Don't ask for a note in the testrunner
  db["flags"].INTERACTIVE = False # Don't run interactive tests by default.
  db["reportname"] = "default"
  db["environmentname"] = "default"
  db["userinterfacetype"] = "default"
  db["logbasename"] = "droid.log"  # default logfile name
  db["logdirbase"] = "/var/tmp"   # where log files will go
  db["resultsdirbase"] = "/var/tmp" # base dir where results subdirs will be created
  db["reportfilename"] = "defaultreport" # set by test runner
  db["baseurl"] = None   # set to baseurl of web server where reports can be served from
  db["documentroot"] = None # set to the web server's documentroot setting
  # user interface constructor signatures
  db["userinterfaces"] = PersistentAttrDict()  # For user interface constructors
  db["userinterfaces"].default = ("UI.UserInterface", "IO.ConsoleIO", 
                   "UI.DefaultTheme")
  db["userinterfaces"].console = ("UI.UserInterface", "IO.ConsoleIO", 
                   "UI.DefaultTheme")
  # pre-defined report definitions. select at run-time with the reportname variable.
  db["reports"] = PersistentAttrDict()  # For report constructors
  db["reports"].default = ("StandardReport", "-", "text/ansi")
  db["reports"].unittest = ("StandardReport", "-", "text/ansi")
  db["reports"].html = ("StandardReport", "$reportpath", "text/html")
  db["reports"].email = [("StandardReport", "-", "text/ansi"),
              ("pycopia.reports.Email.EmailReport", "text/html")]


def _test(argv):
  db = GetClient()
  return db

if __name__ == "__main__":
  db = _test(sys.argv)
  r = db.getRoot()



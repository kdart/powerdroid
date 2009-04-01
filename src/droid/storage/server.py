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
#

"""The Droid persistent storage server.

Runs the Durus storage server.
"""

__author__ = 'keith@dartworks.biz (Keith Dart)'


import sys, os

from durus.storage_server import DEFAULT_PORT, DEFAULT_HOST, StorageServer
from durus.file_storage import FileStorage, TempFileStorage
from durus.logger import log, logger, direct_output

from pycopia import logfile



def startDurus(host, port, logfilename, dbfilename):
  """Start and initialize the Durus server component.

  Also opens a log file.
  """
  lf = logfile.open(logfilename, 50000)
  direct_output(lf)
  logger.setLevel(9)
  storage = FileStorage(dbfilename, repair=False, readonly=False)
  log(20, 'Storage file=%s host=%s port=%s', storage.get_filename(), host, port)
  StorageServer(storage, host=host, port=port).serve()


def storaged(argv):
  """The Droid storage server.

  storaged [-h <serverhost>] [-p <serverport>] [-d <databasefile>] 
          [-l <logfile>] [-n] [-?]

  where:

      -h <host> is the server hostname to bind to.
      -p <port> is the TCP port to use (other than the default).
      -d <filename> specifies the Durus file to use for the database.
      -l <logfilename> file name to use for logging.
      -n Do NOT become a daemon, stay in foreground (for debugging).
      -? This help screen.

  Uses the configuration file /etc/droid/storage.conf to obtain the
  default option values.

  """

  import getopt
  from pycopia import daemonize
  from pycopia import basicconfig
  cf = basicconfig.get_config(os.path.join("/", "etc", "droid", 
                      "storage.conf"))
  host = cf.get("host", DEFAULT_HOST)
  port = cf.get("port", DEFAULT_PORT)
  DBFILE = os.path.expandvars(cf.get("dbfile"))
  LOGFILE = os.path.expandvars(cf.get("dblog"))
  del cf
  do_daemon = True

  try:
    optlist, args = getopt.getopt(argv[1:], "d:l:h:p:n?")
  except getopt.GetoptError:
    print storaged.__doc__
    sys.exit(2)

  for opt, optarg in optlist:
    if opt == "-d":
      DBFILE = optarg
    elif opt == "-l":
      LOGFILE = optarg
    elif  opt == "-h":
      host = optarg
    elif opt == "-p":
      port = int(optarg)
    elif opt == "-n":
      do_daemon = False
    elif opt == "-?":
      print storaged.__doc__
      return 2

  if do_daemon:
    daemonize.daemonize(pidfile="/var/run/%s.pid" % (os.path.basename(argv[0]),))
  try:
    startDurus(host, port, LOGFILE, DBFILE)
  except KeyboardInterrupt:
    return


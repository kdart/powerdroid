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

import sys
import os

os.umask(022)

from distutils.core import setup, Extension
from glob import glob

# Set envar to 0 if you don't have any GPIB package installed.
COMPILE_GPIB = int(os.environ.get("COMPILE_GPIB", 1))

# 1 means compile gpib wrapper with Ines libraries (Ines package must
# be installed).
# 0 means use linux-gpib libraries (which must be installed).
USE_INES = int(os.environ.get("USE_INES", 1)) 

HOSTNAME = os.uname()[1]
WEBHOME = "/var/www/" + HOSTNAME

if COMPILE_GPIB and sys.platform == "linux2":

  if USE_INES:
    gpibmodule = Extension("_gpib",
        ["_gpibmodule.c"],
        define_macros=[("USE_INES", "1")],
        libraries=["gpibapi", "lockdev"])
  else: # linux-gpib
    gpibmodule = Extension("_gpib",
        ["_gpibmodule.c"],
        libraries=["gpib", "lockdev"])

  compiled_extensions = [gpibmodule]
else:
  compiled_extensions = []

setup(name="droid",
  version="0.10",
  url="http://psyche.corp.google.com/",
  maintainer="Keith Dart",
  maintainer_email="dart@google.com",
  description="Android lab automation.",
  package_dir = {'': 'src'},
  packages = [
      "droid",
      "droid.util",
      "droid.physics",
      "droid.instruments",
      "droid.reports",
      "droid.measure",
      "droid.webui",
      "droid.remote",
      "droid.qa",
      "droid.storage",
      "droid.testcaselib",
    ],
  package_data = {
      'droid.testcaselib': ['*.txt'],
    },
  ext_modules = compiled_extensions,
  data_files = [
      ("/etc/droid", glob("etc/*.example")+glob("etc/*.conf")+["etc/matplotlibrc"]),
      ("/etc/apache2/sites-available", ["etc/apache2/powerdroid.conf"]),
      (WEBHOME + "/htdocs", glob("media/htdocs/*.html")),
      (WEBHOME + "/media/images", glob("media/images/*.jpg")+glob("media/images/*.png")),
      (WEBHOME + "/media/css", glob("media/css/*.css")),
      (WEBHOME + "/media/js", glob("media/js/*.js")),
    ],
  scripts = glob("bin/*"),
)


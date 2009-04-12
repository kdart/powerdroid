#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=2:smarttab:expandtab


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

WEBHOME = "/var/www/powerdroid"

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
  version="0.21",
  url="http://psyche.corp.google.com/",
  maintainer="Keith Dart",
  maintainer_email="dart@google.com",
  description="Android lab automation.",
  package_dir = {'': 'src'},
  packages = [
      "droid",
      "droid.android",
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


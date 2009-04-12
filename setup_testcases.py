#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project


import sys
import os

os.umask(022)

from distutils.core import setup
from glob import glob

setup(name="droid_testcases",
    version="0.21",
    url="http://psyche.corp.google.com/",
    maintainer="Keith Dart",
    maintainer_email="dart@google.com",
    description="Android lab automation test cases.",
    package_dir = {'': 'src'},
    packages = [
        "testcases",
        "testcases.android",
        "testcases.android.measure",
        "testcases.android.radio",
        "testcases.android.battery",
        "testcases.currentdraw",
        ],
    package_data = {
        'testcases': ['*.conf'],
        'testcases.android': ['*.conf'],
        'testcases.android.measure': ['*.conf'],
        'testcases.android.radio': ['*.conf'],
        'testcases.android.battery': ['*.conf'],
        'testcases.currentdraw': ['*.conf'],
        },
)


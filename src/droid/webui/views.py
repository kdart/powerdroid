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



"""Web UI views for droid.

"""

__author__ = 'dart@google.com (Keith Dart)'

from pycopia.WWW import framework


def _DocumentConstructor(request, **kwargs):
    doc = framework.get_acceptable_document(request)
    for name, val in kwargs.items():
        setattr(doc, name, val)
    doc.stylesheet = request.get_url("css", name="droid.css")
    doc.javascriptlink = request.get_url("js", name="MochiKit.js")
    doc.javascriptlink = request.get_url("js", name="proxy.js")
    doc.javascriptlink = request.get_url("js", name="droid.js")
    container = doc.add_section("container")
    header = container.add_section("container", id="header")
    wrapper = container.add_section("container", id="wrapper")
    content = wrapper.add_section("container", id="content")
    navigation = container.add_section("container", id="navigation")
    extra = container.add_section("container", id="extra")
    footer = container.add_section("container", id="footer")
    doc.header = header
    doc.content = content
    doc.nav = navigation
    doc.extra = extra
    doc.footer = footer
    return doc

def charts(request):
  resp = framework.ResponseDocument(request, _DocumentConstructor,
           title="Get A Chart")
  resp.doc.javascriptlink = request.get_url("js", name="charts.js")
  resp.doc.header.add_header(1, "Get A Chart")
  return resp.finalize()

def measure(request):
  resp = framework.ResponseDocument(request, _DocumentConstructor,
           title="Take A Measurement")
  resp.doc.javascriptlink = request.get_url("js", name="measure.js")
  resp.doc.header.add_header(1, "Take A Measurement")
  return resp.finalize()

def main(request):
  resp = framework.ResponseDocument(request, _DocumentConstructor,
              title="Droid Tools")
  resp.doc.javascriptlink = request.get_url("js", name="main.js")
  resp.doc.header.add_header(1, "Lab Automation Utilities and Tools")
  return resp.finalize()


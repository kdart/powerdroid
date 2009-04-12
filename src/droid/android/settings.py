#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project


"""Android XML stuff handling.

Parse and generate Android specific XML files. 
Uses newer xml.sax2 parser.
"""


import xml.sax.sax2exts
import xml.sax.handler

from pycopia.XML import POM


class SimpleXMLNode(list):
  def __init__(self, name, attribs):
    super(SimpleXMLNode, self).__init__()
    self._name = name
    self._attribs = attribs

  def __str__(self):
    if self._attribs:
      attstr = " ".join(['%s="%s"' % t for t in self._attribs.items()])
      return "<%s %s></%s>" % (self._name, attstr, self._name)
    else:
      return "<%s></%s>" % (self._name, self._name)

  def GetAttribute(self, name):
    return self._attribs[name]


class StandaloneXMLContentHandler(object):

  def __init__(self):
    self._locator = None
    self.stack = []
    self.msg = None
    self.encoding = "utf-8"

  def setDocumentLocator(self, locator):
    self._locator = locator

  def startDocument(self):
    self.stack = []

  def endDocument(self):
    if self.stack: # stack should be empty now
      raise ValidationError, "unbalanced document!"

  def startElement(self, elname, elattr):
    "Handle an event for the beginning of an element."
    attr = {}
    for name, value in elattr.items():
        attr[POM.normalize_unicode(name)] = POM.unescape(value)
    obj = SimpleXMLNode(elname, attr)
    self.stack.append(obj)

  def endElement(self, name):
    "Handle an event for the end of an element."
    obj = self.stack.pop()
    try:
      self.stack[-1].append(obj)
    except IndexError:
      self.msg = obj

  def characters(self, text):
    pass

  def processingInstruction(self, target, data):
    'handle: xml version="1.0" encoding="ISO-8859-1"?'
    pass

  def startPrefixMapping(self, prefix, uri):
    pass

  def endPrefixMapping(self, prefix):
    pass

  def skippedEntity(self, name):
    pass

  def ignorableWhitespace(self, whitespace):
    pass


def GetStandaloneXMLParser(namespaces=0, validate=0, external_ges=0):
  handler = StandaloneXMLContentHandler()
  # create parser 
  parser = xml.sax.sax2exts.XMLParserFactory.make_parser()
  parser.setFeature(xml.sax.handler.feature_namespaces, namespaces)
  parser.setFeature(xml.sax.handler.feature_validation, validate)
  parser.setFeature(xml.sax.handler.feature_external_ges, external_ges)
  parser.setFeature(xml.sax.handler.feature_external_pes, 0)
  parser.setFeature(xml.sax.handler.feature_string_interning, 1)
  # set handlers 
  parser.setContentHandler(handler)
  parser.setEntityResolver(handler)
  return parser


def ParseSimpleXML(text):
  parser = GetStandaloneXMLParser()
  parser.feed(text)
  parser.close()
  return parser.getContentHandler().msg




if __name__ == "__main__":
  from pycopia import interactive
  XTEXT = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
<boolean name="bt_checkbox" value="false" />
<boolean name="location_gps" value="false" />
<boolean name="sync_calendar" value="true" />
<boolean name="24 hour" value="true" />
<boolean name="location_network" value="true" />
<boolean name="lockenabled" value="false" />
<boolean name="sync_contacts" value="true" />
<boolean name="sync_gmail-ls" value="true" />
<boolean name="autoSyncCheckBox" value="false" />
<boolean name="auto_time" value="true" />
<boolean name="autoSyncToggle" value="true" />
<boolean name="visiblepattern" value="false" />
</map>
"""
  msg = ParseSimpleXML(XTEXT)
  print msg




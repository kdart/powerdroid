#!/usr/bin/python2.4
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#

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


"""Provides easier access to web content from Python.
"""

__author__ = 'dart@google.com (Keith Dart)'


import re
import os
import itertools
import signal

import pycurl

from pycopia import aid
from pycopia import urlparse
from pycopia.WWW import XHTML
from pycopia.WWW import useragents
from pycopia.inet import httputils


DEFAULT_UA = "firefox15_w_goog" # short form
DEFAULT_LANGUAGE = "en"
DEFAULT_ENCODING = "utf-8"
DEFAULT_ACCEPT = \
    "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9"
DEFAULT_ACCEPT_ENCODING = "identity"


class Error(Exception):
  pass


class EncodingError(Error):
  """Raised when trying to coerce a source to a unicode string and that
  fails. Indicates a badly encoded source.
  """


class ContentEncodingError(Error):
  """Raised when a Content-Encoding was received that can't be handled.
  """

class InvalidURLFormatException(Error):
  """Raised when the URL supplied to the Request object is malformed.
  """


class BadStatusLineError(Error):
  """Raised if the HTTP response status is un-parseable.
  """


class RequestResponseError(Error):
  """Raised if there was an error with a request, when you get the
  response.
  """


def MakeURL(url, strict=True):
    return urlparse.UniversalResourceLocator(url, strict)


def GetCookieJar(cookiefile=None):
    return httputils.CookieJar(cookiefile)


def GetPage(url, data=None, logfile=None, cookiefile=None, retries=1, 
      filename=None, **kwargs):
  """Simple page fetcher using the HTTPRequest.

  Args:
    url         : A string or UniversalResourceLocator object.
    data        : Dictionary of POST data (of not provided a GET is performed).
    logfile     : A file-like object to write the transaction to.
    cookiefile  : Update cookies in this file, if provided.
    retries     : Number of times to retry the transaction.
    filename    : Name of file to write target object directly to.

  Extra keyword arguments are passed to the HTTPRequest object.

  Returns: 
    an HTTPResponse object.
  """
  request = HTTPRequest(url, data, **kwargs)
  return request.Perform(logfile, cookiefile, retries, filename)


class RequestResponse(object):
  """Collects received text. Provides properties for later collection of
  text and header objects.
  The `doc` attribute returns a parsed document.
  """
  def __init__(self, requested_encoding):
    self.requested_encoding = requested_encoding
    self._contents = []
    self._responseline = None
    self._body = None # collected full-text body cache
    self._logfile = None
    self._headers = [] # collected headers
    self._headersobjects = None # cached header objects
    self._redirectcount = 0 # Number of redirects
    self._status = None
    self._url = None
    self._timing = None
    self._error = None
    self._cookielist = None
    self._downloadfile = None

  def __str__(self):
    if self._error:
      return "RequestResponse: error=%s" % (self._error,)
    else:
      st = self._GetStatus()
      return "RequestResponse: url=%r, status=%s (%s)" % (self._url,
          st.code, st.reason)

  def __repr__(self):
    return "%s(%r)" % (self.__class__.__name__, self.requested_encoding)

  def __unicode__(self):
    try:
      return unicode(self._make_body(), self.requested_encoding, "strict")
    except ValueError, err:
      raise EncodingError(str(err))

  def _BodyCallback(self, buf):
    if self._logfile is not None:
      self._logfile.write(buf)
    if self._downloadfile is not None:
      self._downloadfile.write(buf)
    else:
      self._contents.append(buf)

  def _HeaderCallback(self, buf):
    if self._logfile:
      self._logfile.write(buf)
    if buf.startswith("HTTP"):
      if self._responseline and self._responseline.find("302") >= 0:
        self._headers = [] # clear headers if redirected.
      self._responseline = buf
    else:
      self._headers.append(buf)

  def _SetLogfile(self, fo):
    if hasattr(fo, "write"):
      self._logfile = fo

  def _GetLogfile(self):
    return self._logfile

  def _ClearLogfile(self):
    self._logfile = None

  def _MakeHeaders(self):
    if self._headersobjects:
      return self._headersobjects
    else:
      rv = httputils.Headers()
      for ht in self._headers:
        ht = ht.strip()
        if ht:
          rv.append(httputils.get_header(ht))
      self._headersobjects = rv
      self._headers = []
      return rv

  def _MakeBody(self):
    if self._body:
      return self._body
    else:
      self._body = "".join(self._contents)
      self._contents = [] # free up memory
      return self._body

  def _make_status(self):
    # HTTP/1.1 200 OK
    line = self._responseline
    try:
      [version, status, reason] = line.split(None, 2)
    except ValueError:
      try:
        [version, status] = line.split(None, 1)
        reason = ""
      except ValueError:
        raise BadStatusLineError(line)
    try:
      status = int(status)
      if status < 100 or status > 999:
        raise BadStatusLine(line)
    except ValueError:
      raise BadStatusLineError(line)
    try:
      version = float(version.split("/")[1])
    except (IndexError, ValueError):
      version = 0.9
    reason = reason.strip()
    reason = reason or httputils.STATUSCODES.get(status, "")
    self._responseline = None
    return _ResponseLine(version, status, reason)

  def _GetStatus(self):
    if self._error is not None:
      raise RequestResponseError(self._error)
    if self._status is not None:
      return self._status
    else:
      self._status = self._make_status()
      return self._status

  def GetDoc(self):
    text = self._MakeBody()
    hdrs = self._MakeHeaders()
    actualtype = hdrs["content-type"].value
    p = XHTML.get_parser(mimetype=actualtype)
    p.feed(text)
    p.close()
    doc = p.getContentHandler().doc
    doc.headers = self.headers # stash headers in the doc in case you need them.
    return doc

  def SetSavefile(self, fileobject):
    if hasattr(fileobject, "write"):
      self._downloadfile = fileobject

  def _DelSavefile(self):
    self._downloadfile = None

  def Finalize(self, c):
    """Finalize a Curl object and extract information from it."""
    self._url = c.getinfo(pycurl.EFFECTIVE_URL)
    # timing info
    NT = c.getinfo(pycurl.NAMELOOKUP_TIME)
    CT = c.getinfo(pycurl.CONNECT_TIME)
    PT = c.getinfo(pycurl.PRETRANSFER_TIME)
    ST = c.getinfo(pycurl.STARTTRANSFER_TIME)
    TT = c.getinfo(pycurl.TOTAL_TIME)
    RT = c.getinfo(pycurl.REDIRECT_TIME)
    self._timing = TimingInfo(NT, CT, PT, ST, TT, RT)
    self._redirectcount = c.getinfo(pycurl.REDIRECT_COUNT)
    self._cookielist = c.getinfo(pycurl.INFO_COOKIELIST)
    c.close()
    self._downloadfile = None

  def _SetError(self, err):
    if err is not None:
      self._error = aid.Enum(err[0], err[1])

  # properties that return response components. This is a the primary user
  # interface to this object.
  logfile = property(_GetLogfile, _SetLogfile, _ClearLogfile,
      "A write-able object that will get text from the fetch.")
  headers = property(_MakeHeaders, None, None,
      "A list-like object containing HTTPHeader objects.")
  body = property(_MakeBody, None, None,
      "The complete body of the response, as text string.")
  content = body # alias
  responseline = property(_GetStatus, None, None,
      "A ResponseLine object with code, reason, and version.")
  status = responseline
  doc = property(GetDoc, None, None, "Parsed XHTMLDocument document.")
  url = property(lambda s: s._url, None, None, "Effective URL.")
  timing = property(lambda s: s._timing, None, None, "Timing information.")
  error = property(lambda s: s._error, _SetError, None, "Error information.")
  redirectcount = property(lambda s: s._redirectcount, None, None,
      "Redirect count.")
  cookielist = property(lambda s: s._cookielist, None, None,
      "Netscape cookies.")
  savefile = property(lambda s: s._downloadfile, SetSavefile, _DelSavefile, 
      "File object to write response to.")


class _ResponseLine(object):
  """HTTP response line container.

  Attributes:
    version: HTTP version as a float.
    code:  HTTP Response code as an int.
    reason:  HTTP response reason.
  """
  __slots__ = ["version", "code", "reason"]
  def __init__(self, version, code, reason):
    self.version = version
    self.code = code
    self.reason = reason

  def __str__(self):
    return "%s %s" % (self.code, self.reason)

  # evaluates true on good response
  def __nonzero__(self):
    return self.code == 200


class TimingInfo(object):
  def __init__(self, namelookup, connect, pretransfer,
                                     starttransfer, total, redirect):
    self.namelookup = namelookup
    self.connect = connect
    self.pretransfer = pretransfer
    self.starttransfer = starttransfer
    self.total = total
    self.redirect = redirect

  def __str__(self):
    return """Timing:
     |--%(namelookup)s namelookup (s)
     |--|--%(connect)s connect (s)
     |--|--|--%(pretransfer)s pretransfer (s)
     |--|--|--|--%(starttransfer)s starttransfer (s)
     |--|--|--|--|--%(total)s total (s)
     |--|--|--|--|--%(redirect)s redirect (s)
    NT CT PT ST TT RT
""" % self.__dict__

  def __float__(self):
    return self.total

  def __coerce__(self, other):
    try:
      return self.total, float(other)
    except:
      return None

  def __add__(self, other):
    return TimingInfo(
      self.namelookup + other.namelookup,
      self.connect + other.connect,
      self.pretransfer + other.pretransfer,
      self.starttransfer + other.starttransfer,
      self.total + other.total,
      self.redirect + other.redirect,
      )

  def __div__(self, other):
    other = float(other)
    return TimingInfo(
      self.namelookup / other,
      self.connect / other,
      self.pretransfer / other,
      self.starttransfer / other,
      self.total / other,
      self.redirect / other,
      )

  def __iadd__(self, other):
    self.namelookup += other.namelookup
    self.connect += other.connect
    self.pretransfer += other.pretransfer
    self.starttransfer += other.starttransfer
    self.total += other.total
    self.redirect += other.redirect
    return self


class Request(object):
  """Base class for all types of URL requests.
  """


class HTTPRequest(Request):
  """General HTTP Requst object.

  Arguments:
     url         : (None)             String or UniversalResourceLocator object.
     data        : (None)             Dictionary of POST data.
     query       : (None)             Dictionary of extra URL query items.
     encoding    : (DEFAULT_ENCODING) String indicating encoding request.
     language    : (DEFAULT_LANGUAGE) String indicating language.
     useragent   : (DEFAULT_UA)       String for User-Agent header.
     accept      : (DEFAULT_ACCEPT)   String for Accept header.
     extraheaders: (None)             List of extra headers.
     strict      : (True)             Parse URL string strictly.
     proxy       : (None)             Proxy host to use, if any.
     cookiejar   : (None)             A CookieJar object to get cookies from.
  """
  def __init__(self, url, data=None, query=None, method="GET", 
        encoding=DEFAULT_ENCODING, language=DEFAULT_LANGUAGE, 
        useragent=DEFAULT_UA, accept=DEFAULT_ACCEPT,
        extraheaders=None, strict=True, proxy=None, cookiejar=None,
        accept_encoding=None):
    self.Reset(url, data, query, method, 
        encoding, language, 
        useragent, accept,
        extraheaders, strict, proxy, cookiejar,
        accept_encoding)

  def __str__(self):
    s = ["%s %s" % (self._method, self._url)]
    s.extend(map(str, self._headers))
    return "\n".join(s)

  def __repr__(self):
    return "%s(%r, data=%r, encoding=%r, proxy=%r)" % (self.__class__.__name__,
              self._url, self._data, self._encoding, self._proxy)

  def __nonzero__(self):
    return bool(self._url)

  def ClearState(self):
    self._method = "GET"
    self._url = None
    self._headers = httputils.Headers()
    self._data = {}
    self._proxy = None
    self._encoding = DEFAULT_ENCODING
    self._language = DEFAULT_LANGUAGE
    self._accept_encoding = DEFAULT_ACCEPT_ENCODING

  def copy(self):
    new = self.__class__(self._url, self._data.copy(), self._encoding,
    self._language, proxy=self._proxy)
    new.SetHeaders(self._headers)
    return new

  def GetRequester(self):
    method = self._method
    if method == "GET":
      return self.GetGetter()
    elif method == "POST":
      return self.GetPoster()
    elif method == "PUT":
      return self.GetUploader()
    elif method == "DELETE":
      return self.GetDeleter()
    else:
      raise ValueError("Invalid method type: %r" % (meth,))

  def GetGetter(self):
    """Initialze a Curl object for a single GET request.

    Returns a tuple of initialized Curl and RequestResponse objects.
    """
    c = pycurl.Curl()
    resp = RequestResponse(self._encoding)
    c.setopt(pycurl.HTTPGET, 1)
    if self._query:
      self._url.query.update(self._query)
      self._query = None
    c.setopt(c.URL, str(self._url))
    c.setopt(c.WRITEFUNCTION, resp._BodyCallback)
    c.setopt(c.HEADERFUNCTION, resp._HeaderCallback)
    c.setopt(c.HTTPHEADER, map(str, self._headers))
    self._setCommon(c)
    return c, resp

  def GetPoster(self):
    if isinstance(self._data, HTTPForm):
      return self.GetFormPoster()
    elif isinstance(self._data, (dict, list)):
      return self.GetURLEncodedPoster()
    else:
      return self.GetRawPoster()

  def GetURLEncodedPoster(self):
    """Initialze a Curl object for a single POST request.

    Returns a tuple of initialized Curl and RequestResponse objects.
    """
    data = urlparse.urlencode(self._data, True)
    c = pycurl.Curl()
    resp = RequestResponse(self._encoding)
    c.setopt(c.URL, str(self._url))
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.setopt(c.WRITEFUNCTION, resp._BodyCallback)
    c.setopt(c.HEADERFUNCTION, resp._HeaderCallback)
    headers = self._headers[:]
    headers.append(httputils.ContentType("application/x-www-form-urlencoded"))
    headers.append(httputils.ContentLength(str(len(data))))
    c.setopt(c.HTTPHEADER, map(str, headers))
    self._setCommon(c)
    return c, resp

  def GetFormPoster(self):
    """Initialze a Curl object for a single POST request.

    This sends a multipart/form-data, which allows you to upload files.

    Returns a tuple of initialized Curl and RequestResponse objects.
    """
    data = self._data.items()
    c = pycurl.Curl()
    resp = RequestResponse(self._encoding)
    c.setopt(c.URL, str(self._url))
    c.setopt(pycurl.HTTPPOST, data)
    c.setopt(c.WRITEFUNCTION, resp._BodyCallback)
    c.setopt(c.HEADERFUNCTION, resp._HeaderCallback)
    self._setCommon(c)
    return c, resp

  def GetRawPoster(self):
    """Initialze a Curl object for a single POST request.

    This sends whatever data you give it, without specifying the content
    type.

    Returns a tuple of initialized Curl and RequestResponse objects.
    """
    ld = len(self._data)
    c = pycurl.Curl()
    resp = RequestResponse(self._encoding)
    c.setopt(c.URL, str(self._url))
    c.setopt(pycurl.POST, 1)
    c.setopt(c.READFUNCTION, DataWrapper(self._data).read)
    c.setopt(c.POSTFIELDSIZE, ld)
    c.setopt(c.WRITEFUNCTION, resp._BodyCallback)
    c.setopt(c.HEADERFUNCTION, resp._HeaderCallback)
    headers = self._headers[:]
    headers.append(httputils.ContentType("")) # removes libcurl internal header
    headers.append(httputils.ContentLength(str(ld)))
    c.setopt(c.HTTPHEADER, map(str, headers))
    self._setCommon(c)
    return c, resp

  def GetUploader(self):
    """Initialze a Curl object for a single PUT request.

    Returns a tuple of initialized Curl and RequestResponse objects.
    """
    c = pycurl.Curl()
    resp = RequestResponse(self._encoding)
    c.setopt(pycurl.UPLOAD, 1) # does an HTTP PUT
    data = self._data.get("PUT", "")
    filesize = len(data)
    c.setopt(pycurl.READFUNCTION, DataWrapper(data).read)
    c.setopt(pycurl.INFILESIZE, filesize)
    c.setopt(c.WRITEFUNCTION, resp._BodyCallback)
    c.setopt(c.HEADERFUNCTION, resp._HeaderCallback)
    # extra options to avoid hanging forever
    c.setopt(c.URL, str(self._url))
    c.setopt(c.HTTPHEADER, map(str, self._headers))
    self._setCommon(c)
    return c, resp

  def GetDeleter(self):
    """Initialze a Curl object for a single DELETE request.

    Returns a tuple of initialized Curl and RequestResponse objects.
    """
    c = pycurl.Curl()
    resp = RequestResponse(self._encoding)
    c.setopt(pycurl.CUSTOMREQUEST, "DELETE")
    c.setopt(c.URL, str(self._url))
    c.setopt(c.WRITEFUNCTION, resp._BodyCallback)
    c.setopt(c.HEADERFUNCTION, resp._HeaderCallback)
    c.setopt(c.HTTPHEADER, map(str, self._headers))
    self._setCommon(c)
    return c, resp

  # sets options common to all operations
  def _setCommon(self, c):
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    # uncomment when new pycurl/libcurl installed.
    #c.setopt(pycurl.AUTOREFERER, 1) 
    c.setopt(pycurl.ENCODING, self._accept_encoding)
    c.setopt(pycurl.MAXREDIRS, 255)
    c.setopt(pycurl.CONNECTTIMEOUT, 30)
    c.setopt(pycurl.TIMEOUT, 300)
    c.setopt(pycurl.NOSIGNAL, 1)
    if self._proxy:
      c.setopt(pycurl.PROXY, self._proxy)
    if self._url.scheme == 'https':
      c.setopt(pycurl.SSLVERSION, 3)
      c.setopt(pycurl.SSL_VERIFYPEER, 0)

  def _Perform(self, logfile, cookiefile, filename):
    """Simple perform to get a single request.
    """
    if filename is not None:
      savefile = open(filename, "w")
    else:
      savefile = None
    c, resp = self.GetRequester()
    if cookiefile:
      c.setopt(pycurl.COOKIEJAR, cookiefile) # write any cookies here
    else:
      # needed to enable cookie handling
      c.setopt(pycurl.COOKIEJAR, "/dev/null") 
    if logfile is not None:
      logfile.write(self.__str__())
      logfile.write("\n\n")
      resp.logfile = logfile
    if savefile is not None:
      resp.SetSavefile(savefile)
    # The curl library takes control here.
    try:
      c.perform()
    except pycurl.error, e:
      resp.error = e
    resp.Finalize(c)
    del resp.logfile
    if savefile is not None:
      savefile.close()
    return resp

  def Perform(self, logfile=None, cookiefile=None, retries=1,
      filename=None):
    retry = 0
    while retry < retries:
      resp = self._Perform(logfile, cookiefile, filename)
      if resp.error or resp.responseline.code != 200:
        retry += 1
      else:
        break
    return resp

  def Reset(self, url, data=None, query=None, method="GET", 
      encoding=DEFAULT_ENCODING, language=DEFAULT_LANGUAGE, 
      useragent=DEFAULT_UA, accept=DEFAULT_ACCEPT,
      extraheaders=None, strict=True, proxy=None, cookiejar=None,
      accept_encoding=None):
    self.ClearState()
    self._url = urlparse.UniversalResourceLocator(url, strict)
    self._proxy = proxy
    if accept_encoding:
      assert accept_encoding in ("identity", "gzip", "deflate")
      self._accept_encoding = accept_encoding
    h = httputils.Headers()
    if cookiejar:
      c = cookiejar.get_cookie(self._url)
      if c:
        h.append(c)
    h.append(httputils.UserAgent(
        useragents.USER_AGENTS.get(useragent, useragent)))
    h.append(httputils.Accept(accept))
    h.append(httputils.AcceptLanguage(language))
    h.append(httputils.AcceptCharset("%s,*;q=0.7" % (encoding,)))
    self._encoding = encoding
    self._language = language
    self._query = query
    self._headers = h
    # add header objects, which could be a list, or inet.httplib.Headers.
    if extraheaders and isinstance(extraheaders, list):
      self._headers.extend(map(httputils.get_header, extraheaders))
    if data:
      self.SetData(data)
    else:
      self._data = {}
    self.SetMethod(method)

  def AddHeader(self, obj, value=None):
    self._headers.add_header(obj, value=None)

  def SetProxy(self, value):
    """Set a proxy in Request object to be used by Connection Manager."""
    if urlparse.URI_RE_STRICT.search(value) is None:
      self._proxy = None
      raise InvalidURLFormatException, "Proxy URL Passed is invalid"
    else:
      self._proxy = value

  def SetURL(self, url, strict=True):
    self._url = urlparse.UniversalResourceLocator(url, strict)

  def SetData(self, data):
    if isinstance(data, (dict, list, str)):
      self._data = data
    else:
      raise ValueError("Data must be dict, HTTPForm, list, or string.")

  def SetMethod(self, meth):
    if meth not in ("GET", "POST", "PUT", "DELETE"):
      raise ValueError("Incorrect method value: %r" % (meth,))
    self._method = meth

  def SetHeaders(self, headers):
    h = httputils.Headers()
    if isinstance(headers, list):
      h.extend(map(httputils.get_header, headers))
    elif type(headers) is str:
      h.add_header(headers)
    self._headers = h

  def GetQuery(self):
    return self._query

  def SetQuery(self, val):
    assert isinstance(val, (dict, list))
    self._query = val

  def DelQuery(self):
    self._query = None

  def __getitem__(self, name):
    self._headers.__getitem__(name)

  # request parts
  url       = property(lambda s: s._url, SetURL, None, "Url Property")
  headers   = property(lambda s: s._headers, SetHeaders, None, 
      "Headers to use")
  data      = property(lambda s: s._data, SetData, None, "Form data")
  proxy     = property(lambda s: s._proxy, SetProxy, None, "Proxy")
  encoding  = property(lambda s: s._encoding, None, None, 
      "Requested char encoding")
  method    = property(lambda s: s._method, SetMethod, None, "Request method")
  query     = property(GetQuery, SetQuery, DelQuery, "Update your query.")


class ConnectionManager(object):
  """This is the interface for the Connection Manager used to
  manage HTTP, HTTPS, FTP connections"""

  def __init__(self):
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    self._requests = []
    self.Initialize()

  def Initialize(self):
    pass

  def AddRequest(self, request):
    return NotImplemented

  def Perform(self, logfile=None):
    return NotImplemented


class HTTPConnectionManager(ConnectionManager):
  """This is the Connection Manager that takes HTTP/HTTPS Request objects
  and uses is to connect.  Response codes are obtained and number of retries
  can be Set.  It uses default proxy is proxies are not provided.  Also,
  response object can be returned as response HTML/XML and Response POM.
  """

  def AddRequest(self, request):
    assert isinstance(request, HTTPRequest)
    self._requests.append(request)

  def GetRequest(self, url, **kwargs):
    """Convenient constructor method for getting a Request object.
    """
    return HTTPRequest(url, **kwargs)

  def GetURL(self, obj, logfile=None, cookiefile=None, **kwargs):
    """Simple interface for making requests with uniform headers.
    If you supply a string, it is taken as the URL to fetch. If you supply
    a list, multiple requests are issued. Returns two lists, as the
    Perform() method does.
    """
    obj_t = type(obj)
    if issubclass(obj_t, (str, urlparse.UniversalResourceLocator)):
      r = HTTPRequest(obj, **kwargs)
      resp = r.Perform(logfile, cookiefile)
      if resp.error:
        return [], [resp] # consistent API
      else:
        return [resp], []
    elif issubclass(obj_t, HTTPRequest):
      resp = obj.Perform(logfile)
      if resp.error:
        return [], [resp]
      else:
        return [resp], []
    else: # assumed to be iterable
      for url in iter(obj):
        r = HTTPRequest(url, **kwargs)
        self._requests.append(r)
        return self.Perform(logfile)

  def PostURL(self, obj, data, logfile=None, **kwargs):
    """Perform a POST method.
    """
    obj_t = type(obj)
    if issubclass(obj_t,  (str, urlparse.UniversalResourceLocator)):
      r = HTTPRequest(obj, **kwargs)
      r.method = "POST"
      r.data = data
      resp = r.Perform(logfile)
      if resp.error:
        return [], [resp] # consistent API
      else:
        return [resp], []
    elif issubclass(obj_t, HTTPRequest):
      obj.method = "POST"
      obj.data = data
      resp = obj.Perform(logfile)
      return [resp], []
    else: # assumed to be iterables
      for url, rd in itertools.izip(iter(obj), iter(data)):
        r = HTTPRequest(str(url), **kwargs)
        r.method = "POST"
        r.data = rd
        self._requests.append(r)
        return self.Perform(logfile)

  def Perform(self, logfile=None):
    """Fetch all of the added Request objects. Return two lists. The first
    list is a list of responses that completed. The second is list of the
    requests that errored.
    """
    m = pycurl.CurlMulti()
    requests = []
    num_q = num_urls = len(self._requests)
    reqs = self._requests
    self._requests = []
    for req in reqs:
      c, resp = req.GetRequester()
      c.resp = resp
      m.add_handle(c)
      requests.append(c)
    del reqs

    while 1:
      ret, num_handles = m.perform()
      if ret != pycurl.E_CALL_MULTI_PERFORM:
        break

    num_handles = num_urls
    while num_handles:
      ret = m.select(5.0)
      if ret == -1:
        continue
      while 1:
        ret, num_handles = m.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
          break

    goodlist = []
    errlist = []
    while 1:
      num_q, ok_list, err_list = m.info_read(num_urls)
      for c in ok_list:
        resp = c.resp
        del c.resp
        resp.error = None
        m.remove_handle(c)
        resp.Finalize(c)
        goodlist.append(resp)
      for c, errno, errmsg in err_list:
        resp = c.resp
        del c.resp
        resp.error = (errno, errmsg)
        m.remove_handle(c)
        errlist.append(resp)
      if num_q == 0:
        break
    m.close()
    return goodlist, errlist


class DocumentAdapter(object):
  def __init__(self, fp):
    self.fp = fp

  def read(self, size):
    return self.fp.read(size)


class DataWrapper(object):
  def __init__(self, data):
    self._data = str(data)

  def read(self, amt):
    data = self._data[:amt]
    self._data = self._data[amt:]
    return data


class HTTPForm(dict):
  """A dictionary of HTTP form data.

  Set an HTTPRequest's data attribute to one of these to cause it to send
  a form with this object as contents. The values are maintained in a
  format that pycurl needs.
  """

  def AddFile(self, fieldname, pathname, mimetype=None, filename=None):
    """Add a file section.

    The file will be uploaded. You must use the full path name.

    Args:
      fieldname: name of the form field.
      pahtname:  Full path to the file.
      mimetype:  Override the auto-detected mime type.
      filename:  Override the base name of the given pathname.
    """
    new = [pycurl.FORM_FILE, pathname]
    if mimetype:
      new.append(pycurl.FORM_CONTENTTYPE)
      new.append(mimetype)
    if filename:
      new.append(pycurl.FORM_FILENAME)
      new.append(filename)
    if fieldname in self:
      dict.__setitem__(self, fieldname, self[fieldname] + tuple(new))
    else:
      dict.__setitem__(self, fieldname, tuple(new))

  def __setitem__(self, key, value):
    if key in self:
      dict.__setitem__(self, key, self[key]+(pycurl.FORM_CONTENTS, str(value)))
    else:
      dict.__setitem__(self, key, (pycurl.FORM_CONTENTS, str(value)))

  def FromForm(self, formnode):
    """Set the data from a Form object node (from WWW.XHTML module).
    """
    for name, value in formnode.fetch_form_values():
      self.__setitem__(name, value)

  def GetValue(self, key):
    """Get a value, without the pycurl form content type."""
    val = dict.__getitem__(self, key)
    return val[-1] # assumes one value with key name.

#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Real-time plotting using a client and server. 

Client plots incoming data in a stripchart. 
Server sends data to client.
"""

__author__ = 'dart@google.com (Keith Dart)'



from pycopia import socket



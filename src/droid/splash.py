#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Tools to create splash screens for Dream.

"""

import sys
import os
import struct
import getopt

import Image


def ImageToRaw565(image, outf):
  """Write PIL Image instance to raw 565 format.
  """
  assert image.mode == "RGB", "Must be RGB image"
  assert image.size == (320, 480), "Must use 320x480 image size"
  for red, green, blue in image.getdata():
    encoded = (_Scale(red, 0x1f) << 11) + \
        (_Scale(green, 0x3f) << 5) + \
        (_Scale(blue, 0x1f))
    outf.write(struct.pack('@H', encoded))

def _Scale(value, scaling): 
  return int(value * scaling / 255)


def FileToRaw565File(infile, outfile, crop=(0, 0, 320, 480)):
  image = Image.open(infile)
  image = image.crop(crop)
  if image.mode != "RGB":
    image = image.convert("RGB")
  outf = open(outfile, "w")
  try:
    ImageToRaw565(image, outf)
  finally:
    outf.close()


def Flash(filename):
  if os.path.exists(filename):
    cmd = "fastboot flash splash1 %s" % filename
    rv = os.system(cmd)
    if os.WIFEXITED(rv) and os.WEXITSTATUS(rv) == 0:
      os.system("fastboot reboot")
    else:
      print "Failed to flash."


def splash(argv):
  """splash [-o offsetx,offsety] [-f] <infile> [<outfile>]

  Convert infile to raw 320x480 565 image. The infile can be any format
  that PIL supports. Optionally supply an output file. 

  Large images will automatically be cropped to screen size. An optional
  X,Y offeset my be provided.

  Options:
    -o  x,y offset from source image (0,0 is default, upper left).
    -f  Flash the result directly to a device in bootloader mode.
  """
  offsetx = 0
  offsety = 0
  flash = False
  try:
    opts, args = getopt.getopt(argv[1:], "o:h?fd")
  except getopt.GetoptError, err:
    print >>sys.stderr, err
    return
  for opt, optarg in opts:
    if opt in ("-h", "-?"):
      print argv[0], ":"
      print splash.__doc__
      return
    elif opt == "-o":
      offsetx, offsety = map(int, optarg.split(","))
    elif opt == "-f":
      flash = True
    elif opt == "-d":
      from pycopia import autodebug

  try:
    infile = os.path.expandvars(os.path.expanduser(args[0]))
  except IndexError:
    print splash.__doc__
    return
  try:
    outfile = os.path.expandvars(os.path.expanduser(args[1]))
  except IndexError:
    outfile = "/var/tmp/dreamsplash.565"

  if not outfile.endswith(".565"):
    outfile = os.path.splitext(outfile)[0] + ".565"

  crop = (offsetx, offsety, offsetx + 320, offsety + 480)
  FileToRaw565File(infile, outfile, crop)
  if flash:
    print "Flashing", outfile
    Flash(outfile)



# Dictionary containing numbers
#
# These objects are meant to be used like arrays with generalized

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


#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-23
#
# Modified by Keith Dart.

from pycopia import dictlib


class NumberDict(dictlib.AttrDictDefault):

  """Dictionary storing numerical values

  Constructor: NumberDict()

  An instance of this class acts like an array of number with
  generalized (non-integer) indices. A value of zero is assumed
  for undefined entries. NumberDict instances support addition,
  and subtraction with other NumberDict instances, and multiplication
  and division by scalars.
  """

  def __coerce__(self, other):
    if isinstance(other, dict):
      return self, self.__class__(other, self._default)

  def __add__(self, other):
    sum = self.copy()
    for key in other.keys():
      sum[key] = sum[key] + other[key]
    return sum

  __radd__ = __add__

  def __sub__(self, other):
    sum = self.copy()
    for key in other.keys():
      sum[key] = sum[key] - other[key]
    return sum

  def __rsub__(self, other):
    sum = self.copy()
    for key in other.keys():
      sum[key] = other[key] - self[key]
    return sum

  def __mul__(self, other):
    new = self.__class__(default=self._default)
    for key in self.keys():
      new[key] = other * self[key]
    return new

  __rmul__ = __mul__

  def __div__(self, other):
    new = self.__class__(default=self._default)
    for key in self.keys():
      new[key] = self[key] / other
    return new


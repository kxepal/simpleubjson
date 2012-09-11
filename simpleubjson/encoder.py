# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

from collections import Iterable, Sized, Mapping
from decimal import Decimal

from simpleubjson import NOOP, EOS, EOS_A, EOS_O
from simpleubjson.compat import (
    basestring, bytes, long, unicode, XRangeType,
    dict_itemsiterator, dict_keysiterator, dict_valuesiterator
)
from simpleubjson.markers import (
    DRAFT8_MARKERS, DRAFT9_MARKERS,
    StreamedArrayMarker, StreamedObjectMarker
)

def maybe_one_of(tval, *types):
    if tval in types:
        return True
    for item in types:
        if isinstance(tval, item):
            return True
    return False


class Encoder(object):

    markers = {}

    def __call__(self, obj, output=None, default=None):
        if output is None:
           return bytes().join(self.encode(obj, default))
        for chunk in self.encode(obj, default):
            output.write(chunk)

    def encode(self, obj, default=None):
        if obj is None:
            return self.markers['Z'].encode(self, obj)
        elif isinstance(obj, bool):
            return self.markers[['F', 'T'][obj]].encode(self, obj)
        elif obj is NOOP:
            return self.markers['N'].encode(self, obj)
        elif default is not None:
            return self.encode(default(obj))
        raise TypeError('unable to encode value %r %r' % (obj, type(obj)))


class Draft8Encoder(Encoder):

    __slots__ = ()

    markers = dict((marker.tag, marker) for marker in DRAFT8_MARKERS)

    def encode(self, obj, default=None):
        if isinstance(obj, (int, long)) and not isinstance(obj, bool):
            if (-2 ** 7) <= obj <= (2 ** 7 - 1):
                marker = self.markers['B']
            elif (-2 ** 15) <= obj <= (2 ** 15 - 1):
                marker = self.markers['i']
            elif (-2 ** 31) <= obj <= (2 ** 31 - 1):
                marker = self.markers['I']
            elif (-2 ** 63) <= obj <= (2 ** 63 - 1):
                marker = self.markers['L']
            else:
                obj = unicode(obj).encode('utf-8')
                marker = self.markers[['h', 'H'][len(obj) >= 255]]
            return marker.encode(self, obj)
        elif isinstance(obj, float):
            if 1.18e-38 <= abs(obj) <= 3.4e38:
                marker = self.markers['d']
            elif 2.23e-308 <= abs(obj) < 1.8e308:
                marker = self.markers['D']
            elif obj == float('inf') or obj == float('-inf'):
                marker = self.markers['Z']
            else:
                obj = unicode(obj).encode('utf-8')
                marker = self.markers[['h', 'H'][len(obj) >= 255]]
            return marker.encode(self, obj)
        elif isinstance(obj, basestring):
            marker = self.markers[['s', 'S'][len(obj) >= 255]]
            return marker.encode(self, obj)
        elif isinstance(obj, Mapping):
            marker = self.markers[['o', 'O'][len(obj) >= 255]]
            return marker.encode(self, obj)
        elif isinstance(obj, dict_itemsiterator):
            return StreamedObjectMarker().encode(self, obj)
        elif isinstance(obj, XRangeType):
            return StreamedArrayMarker().encode(self, obj)
        elif isinstance(obj, (dict_keysiterator, dict_valuesiterator)):
            return StreamedArrayMarker().encode(self, obj)
        elif isinstance(obj, Iterable) and isinstance(obj, Sized):
            marker = self.markers[['a', 'A'][len(obj) >= 255]]
            return marker.encode(self, obj)
        elif isinstance(obj, Iterable):
            return StreamedArrayMarker().encode(self, obj)
        elif obj is EOS:
            return self.markers['E'].encode(self, obj)
        elif isinstance(obj, Decimal):
            obj = unicode(obj).encode('utf-8')
            marker = self.markers[['h', 'H'][len(obj) >= 255]]
            return marker.encode(self, obj)
        else:
            return super(Draft8Encoder, self).encode(obj, default)


class Draft9Encoder(Encoder):

    __slots__ = ()

    markers = dict((marker.tag, marker) for marker in DRAFT9_MARKERS)

    def encode(self, obj, default=None):
        if isinstance(obj, (int, long)) and not isinstance(obj, bool):
            if (-2 ** 7) <= obj <= (2 ** 7 - 1):
                marker = self.markers['i']
            elif (-2 ** 15) <= obj <= (2 ** 15 - 1):
                marker = self.markers['I']
            elif (-2 ** 31) <= obj <= (2 ** 31 - 1):
                marker = self.markers['l']
            elif (-2 ** 63) <= obj <= (2 ** 63 - 1):
                marker = self.markers['L']
            else:
                marker = self.markers['H']
                obj = unicode(obj).encode('utf-8')
            return marker.encode(self, obj)
        elif isinstance(obj, float):
            if 1.18e-38 <= abs(obj) <= 3.4e38:
                marker = self.markers['d']
            elif 2.23e-308 <= abs(obj) < 1.8e308:
                marker = self.markers['D']
            elif obj == float('inf') or obj == float('-inf'):
                marker = self.markers['Z']
            else:
                marker = self.markers['H']
                obj = unicode(obj).encode('utf-8')
            return marker.encode(self, obj)
        elif isinstance(obj, basestring):
            return self.markers['S'].encode(self, obj)
        elif isinstance(obj, (Mapping, dict_itemsiterator)):
            return self.markers['{'].encode(self, obj)
        elif isinstance(obj, Iterable):
            return self.markers['['].encode(self, obj)
        elif obj is EOS_A:
            return self.markers[']'].encode(self, obj)
        elif obj is EOS_O:
            return self.markers['}'].encode(self, obj)
        elif isinstance(obj, Decimal):
            return self.markers['H'].encode(self, obj)
        else:
            return super(Draft9Encoder, self).encode(obj, default)

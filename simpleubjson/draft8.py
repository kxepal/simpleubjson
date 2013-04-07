# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2013 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#


from collections import Iterable, Sized, Mapping
from decimal import Decimal

from simpleubjson import EOS
from simpleubjson.common import Decoder, Encoder
from simpleubjson.markers import (
    DRAFT8_MARKERS, StreamedArrayMarker, StreamedObjectMarker
)
from simpleubjson.compat import (
    basestring, b, long, unicode, XRangeType,
    dict_itemsiterator, dict_keysiterator, dict_valuesiterator
)


__all__ = ['Draft8Decoder', 'Draft8Encoder']


class Draft8Decoder(Decoder):
    """Decoder of UBJSON data to Python object that follows Draft 8
    specification rules with next data mapping:

    +--------+----------------------------+----------------------------+-------+
    | Marker | UBJSON type                | Python type                | Notes |
    +========+============================+============================+=======+
    | ``N``  | noop                       | :const:`~simpleubjson.NOOP`| \(1)  |
    +--------+----------------------------+----------------------------+-------+
    | ``Z``  | null                       | None                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``F``  | false                      | bool                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``T``  | true                       | bool                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``B``  | byte                       | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``i``  | int16                      | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``I``  | int32                      | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``L``  | int64                      | long                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``d``  | float                      | float                      |       |
    +--------+----------------------------+----------------------------+-------+
    | ``D``  | double                     | float                      |       |
    +--------+----------------------------+----------------------------+-------+
    | ``h``  | hugeint - 2 bytes          | decimal.Decimal            |       |
    +--------+----------------------------+----------------------------+-------+
    | ``H``  | hugeint - 5 bytes          | decimal.Decimal            |       |
    +--------+----------------------------+----------------------------+-------+
    | ``s``  | string - 2 bytes           | unicode                    |       |
    +--------+----------------------------+----------------------------+-------+
    | ``S``  | string - 5 bytes           | unicode                    |       |
    +--------+----------------------------+----------------------------+-------+
    | ``a``  | array - 2 bytes            | list                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``a``  | array - unsized            | generator                  | \(2)  |
    +--------+----------------------------+----------------------------+-------+
    | ``A``  | array - 5 bytes            | list                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``o``  | object - 2 bytes           | dict                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``o``  | object - unsized           | generator                  | \(3)  |
    +--------+----------------------------+----------------------------+-------+
    | ``O``  | object - 5 bytes           | dict                       |       |
    +--------+----------------------------+----------------------------+-------+

    Notes:

    (1)
        Noop values are ignored by default if only `allow_noop` argument wasn't
        passed as ``True`` to :func:`~simpleubjson.decoder.streamify` wrapper.

    (2)
        Nested generators are automatically converted to lists.

    (3)
        Unsized objects are represented as list of 2-element tuples with object
        key and value.
    """
    _markers = dict((marker.tag, marker) for marker in DRAFT8_MARKERS)

    def decode_tlv(self, stream, marker, tlv):
        tag, length, value = tlv
        if tag == b('a') and length == 255:
            return StreamedArrayMarker().decode(self, stream, tlv)
        if tag == b('o') and length == 255:
            return StreamedObjectMarker().decode(self, stream, tlv)
        return marker.decode(self, stream, tlv)


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

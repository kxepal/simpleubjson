# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2013 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#


from collections import Iterable, Mapping
from decimal import Decimal

from simpleubjson import EOS_A, EOS_O
from simpleubjson.common import Decoder, Encoder
from simpleubjson.markers import DRAFT9_MARKERS
from simpleubjson.compat import (
    basestring, long, unicode, dict_itemsiterator
)


__all__ = ['Draft9Decoder', 'Draft9Encoder']


class Draft9Decoder(Decoder):
    """Decoder of UBJSON data to Python object that follows Draft 9
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
    | ``i``  | int8                       | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``I``  | int16                      | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``l``  | int32                      | int                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``L``  | int64                      | long                       |       |
    +--------+----------------------------+----------------------------+-------+
    | ``d``  | float                      | float                      |       |
    +--------+----------------------------+----------------------------+-------+
    | ``D``  | double                     | float                      |       |
    +--------+----------------------------+----------------------------+-------+
    | ``H``  | hugeint - sized            | decimal.Decimal            |       |
    +--------+----------------------------+----------------------------+-------+
    | ``S``  | string - sized             | unicode                    |       |
    +--------+----------------------------+----------------------------+-------+
    | ``A``  | array - unsized            | generator                  | \(2)  |
    +--------+----------------------------+----------------------------+-------+
    | ``O``  | object - unsized           | generator                  | \(3)  |
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
    _markers = dict((marker.tag, marker) for marker in DRAFT9_MARKERS)


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

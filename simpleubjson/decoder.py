# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
from simpleubjson.markers import (
    DRAFT8_MARKERS, DRAFT9_MARKERS,
    NumericMarker, StreamedArrayMarker, StreamedObjectMarker
)
from simpleubjson.compat import BytesIO, b, bytes, unicode
import sys
version = '.'.join(map(str, sys.version_info[:2]))

__all__ = ['Decoder', 'Draft8Decoder', 'Draft9Decoder', 'streamify']


def streamify(source, markers, allow_noop=False):
    """Wraps source data into stream that emits data as :class:`Marker` instance
    with TLV-tuple description.

    :param source: `.read([size])`-able object or string with ubjson data.

    :param markers: Mapping of supported markers where key is a `tag` byte and
                    value is a related :class:`Marker` instance.
    :type markers: dict

    :param allow_noop: Allow to emit :const:`~simpleubjson.NOOP` values for
                       unsized arrays and objects.
    :type allow_noop: bool

    :yield: :class:`Marker` and (`tag`, `length`, `value`) tuple.
    """
    _NOOP=b('N')
    _isinstance = isinstance
    _size_marker = NumericMarker
    _calc = struct.calcsize
    _unpack = struct.unpack
    if _isinstance(source, unicode):
        source = source.encode('utf-8')
    if _isinstance(source, bytes):
        source = BytesIO(source)
    read = source.read
    while 1:
        tag = read(1)
        if not tag:
            break
        if not allow_noop and tag == _NOOP:
            continue
        marker = markers.get(tag)
        if marker is None:
            raise ValueError('Unknown marker %r' % tag)
        length = marker.length
        value = marker.value
        if length is not None:
            if length is _size_marker:
                stag = read(1)
                if not stag:
                    raise ValueError('Unexpectable end of stream')
                smarker = markers.get(stag)
                if smarker is None:
                    raise ValueError('Unknown marker %r' % stag)
                if not _isinstance(smarker, _size_marker):
                    raise ValueError('Invalid size marker %r' % smarker.tag)
                length = smarker.value
            length = _unpack(length, read(_calc(length)))[0]
        if value is not None:
            if length is not None:
                if length < 0:
                    raise ValueError('Negative size for marker %r' % tag)
                if '%' in value:
                    value = value % length
            value = _unpack(value, read(_calc(value)))[0]
        yield marker, (tag, length, value)


class Decoder(object):

    _markers = None

    def __call__(self, stream):
        for marker, tlv in stream:
            return self.decode_tlv(stream, marker, tlv)
        raise ValueError('nothing to decode')

    def decode_tlv(self, stream, marker, tlv):
        return marker.decode(self, stream, tlv)

    @property
    def markers(self):
        return self._markers


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

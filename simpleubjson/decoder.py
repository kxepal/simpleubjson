# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
from decimal import Decimal
from types import GeneratorType
from simpleubjson import NOOP, EOS
from simpleubjson.compat import BytesIO, bytes, unicode, xrange
import sys
version = '.'.join(map(str, sys.version_info[:2]))

__all__ = ['decode_draft_8', 'decode_tlv_draft_8',
           'MARKERS_DRAFT_8', 'streamify']

#: Dict of valid UBJSON markers and struct format for their length and value.
MARKERS_DRAFT_8 = {
    'N': (None, None),
    'Z': (None, None),
    'E': (None, None),
    'F': (None, None),
    'T': (None, None),
    'B': (None, '>b'),
    'i': (None, '>h'),
    'I': (None, '>i'),
    'L': (None, '>q'),
    'd': (None, '>f'),
    'D': (None, '>d'),
    's': ('>B', '>%ds'),
    'S': ('>I', '>%ds'),
    'h': ('>B', '>%ds'),
    'H': ('>I', '>%ds'),
    'a': ('>B', None),
    'A': ('>I', None),
    'o': ('>B', None),
    'O': ('>I', None),
}

_NUMERIC_MARKERS = {
    'i': (None, '>b'),
    'I': (None, '>h'),
    'l': (None, '>i'),
    'L': (None, '>q'),
}
MARKERS_DRAFT_9 = {
    'N': (None, None),
    'Z': (None, None),
    'E': (None, None),
    'F': (None, None),
    'T': (None, None),
    'i': (None, '>b'),
    'I': (None, '>h'),
    'l': (None, '>i'),
    'L': (None, '>q'),
    'd': (None, '>f'),
    'D': (None, '>d'),
    'S': (_NUMERIC_MARKERS, '>%ds'),
    'H': (_NUMERIC_MARKERS, '>%ds'),
    'A': (None, None),
    'O': (None, None),
}
del _NUMERIC_MARKERS

def streamify(source, markers, default=None, allow_noop=False):
    """Wraps source data into stream that emits data in TLV-format.

    :param source: `.read([size])`-able object or string with ubjson data.
    :param markers: Key-value set of rules for :func:`struck.unpack` function.
    :type markers: dict
    :param default: Callable object that would be used if there is no handlers
                    matched for occurred marker.
                    Takes two arguments: data stream and marker.
                    It should return tuple of three values: marker, size and
                    result value.
    :param allow_noop: Allow to emit :const:`~simpleubjson.NOOP` values for
                       unsized arrays and objects.
    :type allow_noop: bool

    :return: Generator of (type, length, value) data set.
    """
    if isinstance(source, unicode):
        source = source.encode('utf-8')
    if isinstance(source, bytes):
        source = BytesIO(source)
    assert hasattr(source, 'read'), 'data source should be `.read([size])`-able'
    read = source.read
    _unpack = struct.unpack
    _calc = struct.calcsize
    while True:
        marker = read(1)
        if not marker:
            break
        if version >= '3.0':
            marker = marker.decode('utf-8')
        if not allow_noop and marker == 'N':
            continue
        if marker not in markers:
            if default is None:
                raise ValueError('Unknown marker %r' % marker)
            else:
                yield default(marker)
                continue
        size, value = markers[marker]
        if size is not None:
            if isinstance(size, dict):
                smarker = read(1)
                if not smarker:
                    break
                if version >= '3.0':
                    smarker = smarker.decode('utf-8')
                if not smarker in size:
                    raise ValueError('Invalid size marker %s' % smarker)
                size = size[smarker][1]
            size = _unpack(size, read(_calc(size)))[0]
            assert size >= 0, 'Negative size for marker %s' % marker
        if value is not None:
            if size is not None:
                value = value % size
            value = _unpack(value, read(_calc(value)))[0]
        yield marker, size, value


def decode_draft_8(stream):
    """Base decoder of UBJSON data to Python object that follows next rules:

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
    | ``s``  | string - 2 bytes           | str                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``S``  | string - 5 bytes           | str                        |       |
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
    for marker, size, value in stream:
        return decode_tlv_draft_8(stream, marker, size, value)
    raise ValueError('nothing more to decode')

def decode_draft_9(stream):
    """Base decoder of UBJSON data to Python object that follows next rules:

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
    | ``S``  | string - sized             | str                        |       |
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
    for marker, size, value in stream:
        return decode_tlv_draft_9(stream, marker, size, value)
    raise ValueError('nothing more to decode')

def decode_tlv_draft_8(stream, marker, size, value):
    if marker in 'BiILdD':
        return value
    elif marker in 'sShH':
        if marker in 'sS':
            return value.decode('utf-8')
        else:
            return Decimal(value.decode('utf-8'))
    elif marker in 'aA':
        if size == 255:
            return decode_unsized_array(decode_draft_8, stream)
        return list(decode_sized_array(decode_draft_8, stream, size))
    elif marker in 'oO':
        if size == 255:
            return decode_unsized_object(decode_draft_8, stream)
        return dict(decode_sized_object(decode_draft_8, stream, size))
    elif marker in 'F':
        return False
    elif marker == 'T':
        return True
    elif marker == 'Z':
        return None
    elif marker == 'N':
        return NOOP
    elif marker == 'E':
        return EOS
    else:
        raise ValueError('Unknown marker %r' % marker)

def decode_tlv_draft_9(stream, marker, size, value):
    if marker in 'iIlLdD':
        return value
    elif marker in 'SH':
        value = value.decode('utf-8')
        if marker == 'H':
            return Decimal(value)
        return value
    elif marker in 'A':
        return decode_unsized_array(decode_draft_9, stream)
    elif marker in 'O':
        return decode_unsized_object(decode_draft_9, stream)
    elif marker in 'F':
        return False
    elif marker == 'T':
        return True
    elif marker == 'Z':
        return None
    elif marker == 'N':
        return NOOP
    elif marker == 'E':
        return EOS
    else:
        raise ValueError('Unknown marker %r' % marker)

def decode_unsized_array(decode, stream):
    while True:
        item = decode(stream)
        if item is EOS:
            break
        elif isinstance(item, GeneratorType):
            item = list(item)
        yield item

def decode_unsized_object(decode, stream):
    while True:
        while True:
            key = decode(stream)
            if key is not NOOP:
                break
            yield key, key
        if key is EOS:
            break
        if not isinstance(key, unicode):
            raise ValueError('key should be string, not %r' % key)
        while True:
            value = decode(stream)
            if value is not NOOP:
                break
        if value is EOS:
            raise ValueError('unexpectable end of stream marker')
        if isinstance(value, GeneratorType):
            value = list(value)
        yield key, value

def decode_sized_array(decode, stream, size):
    for round in xrange(size):
        while True:
            item = decode(stream)
            if item is not NOOP:
                break
        if item is EOS:
            raise ValueError('unexpectable end of stream marker')
        if isinstance(item, GeneratorType):
            item = list(item)
        yield item

def decode_sized_object(decode, stream, size):
    for round in xrange(size):
        while True:
            key = decode(stream)
            if key is not NOOP:
                break
        if not isinstance(key, unicode):
            raise ValueError('key should be string, not %r' % key)
        while True:
            value = decode(stream)
            if value is not NOOP:
                break
        if value is EOS:
            raise ValueError('unexpectable end of stream marker')
        if isinstance(value, GeneratorType):
            value = list(value)
        yield key, value

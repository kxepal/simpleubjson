# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
import re
from types import GeneratorType
from simpleubjson import NOOP, EOS

__all__ = ['UBJSONDecoder', 'MARKERS', 'streamify']

REX_NUMBER = re.compile('^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$')

def is_number(s):
    return s.isdigit() or REX_NUMBER.match(s) is not None


MARKERS = {
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


def streamify(source, default=None, allow_noop=False,
              _unpack=struct.unpack, _calc=struct.calcsize):
    while True:
        marker = source.read(1)
        if not marker:
            break
        if not allow_noop and marker == 'N':
            continue
        rule = MARKERS.get(marker)
        if rule is None:
            if default is None:
                raise ValueError('Unknown marker %r' % marker)
            else:
                yield default(marker)
        size, value = rule
        if size is None and value is None:
            yield marker, None, None
        elif size is None and value is not None:
            yield marker, None, _unpack(value, source.read(_calc(value)))[0]
        elif size is not None and value is not None:
            length = _unpack(size, source.read(_calc(size)))[0]
            value = value % length
            yield marker, length, _unpack(value, source.read(_calc(value)))[0]
        elif size is not None and value is None:
            yield marker, _unpack(size, source.read(_calc(size)))[0], None


class UBJSONDecoder(object):
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
    | ``h``  | hugeint - 2 bytes          | str                        |       |
    +--------+----------------------------+----------------------------+-------+
    | ``H``  | hugeint - 5 bytes          | str                        |       |
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
        passed as ``True`` to :func:`simpleubjson.decoder.stremify` wrapper.

    (2)
        Nested generators are automatically converted to lists.

    (3)
        Unsized objects are represented as list of 2-element tuples with object
        key and value.
    """

    def decode(self, stream):
        for marker, size, value in stream:
            return self.decode_tlv(stream, marker, size, value)
        raise ValueError('nothing to decode')

    def decode_tlv(self, stream, marker, size, value):
        if marker in 'BiILdD':
            return value
        elif marker in 'sShH':
            if marker in 'sS':
                return value.decode('utf-8')
            elif not is_number(value):
                raise ValueError('Value of huge type should be numeric,'
                                 ' not %r' % value)
            return value
        elif marker == 'a':
            if size == 255:
                return self.decode_unsized_array(stream)
            else:
                return list(self.decode_sized_array(stream, size))
        elif marker == 'A':
            return list(self.decode_sized_array(stream, size))
        elif marker == 'o':
            if size == 255:
                return self.decode_unsized_object(stream)
            else:
                return dict(self.decode_sized_object(stream, size))
        elif marker == 'O':
            return dict(self.decode_sized_object(stream, size))
        elif marker == 'F':
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

    def decode_sized_array(self, stream, size):
        for round in xrange(size):
            while True:
                item = self.decode(stream)
                if item is not NOOP:
                    break
            if item is EOS:
                raise ValueError
            if isinstance(item, GeneratorType):
                item = list(item)
            yield item

    def decode_unsized_array(self, stream):
        while True:
            item = self.decode(stream)
            if item is EOS:
                break
            elif isinstance(item, GeneratorType):
                item = list(item)
            yield item

    def decode_sized_object(self, stream, size):
        for round in xrange(size):
            while True:
                key = self.decode(stream)
                if key is not NOOP:
                    break
            if not isinstance(key, basestring):
                raise ValueError('key should be string, not %r' % key)
            while True:
                value = self.decode(stream)
                if value is not NOOP:
                    break
            if value is EOS:
                raise ValueError
            if isinstance(value, GeneratorType):
                value = list(value)
            yield key, value

    def decode_unsized_object(self, stream):
        while True:
            while True:
                key = self.decode(stream)
                if key is not NOOP:
                    break
                yield key, key
            if key is EOS:
                break
            if not isinstance(key, basestring):
                raise ValueError('key should be string, not %r' % key)
            while True:
                value = self.decode(stream)
                if value is not NOOP:
                    break
            if value is EOS:
                raise ValueError
            if isinstance(value, GeneratorType):
                value = list(value)
            yield key, value

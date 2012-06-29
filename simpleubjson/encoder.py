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
from itertools import chain
from types import GeneratorType
from simpleubjson import NOOP, EOS
from simpleubjson.compat import b, unicode, bytes, basestring, long, \
                                XRangeType, dict_keysiterator, \
                                dict_valuesiterator, dict_itemsiterator

__all__ = ['encode_draft_8']

is_byte = lambda value: (-2 ** 7) <= value <= (2 ** 7 - 1)
is_int16 = lambda value: (-2 ** 15) <= value <= (2 ** 15 - 1)
is_int32 = lambda value: (-2 ** 31) <= value <= (2 ** 31 - 1)
is_int64 = lambda value: (-2 ** 63) <= value <= (2 ** 63 - 1)
is_float = lambda value: 1.18e-38 <= abs(value) <= 3.4e38
is_double = lambda value: 2.23e-308 <= abs(value) < 1.8e308 # 1.8e308 is inf
is_infinity = lambda value: value == float('inf') or value == float('-inf')

MARKER_Z = b('Z')
MARKER_N = b('N')
MARKER_F = b('F')
MARKER_T = b('T')
MARKER_B = b('B')
MARKER_i = b('i')
MARKER_I = b('I')
MARKER_L = b('L')
MARKER_d = b('d')
MARKER_D = b('D')
MARKER_s = b('s')
MARKER_S = b('S')
MARKER_h = b('h')
MARKER_H = b('H')
MARKER_a = b('a')
MARKER_A = b('A')
MARKER_o = b('o')
MARKER_O = b('O')
MARKER_E = b('E')
MARKER_FF = b('\xff')

def encode_draft_8(value, output=None, default=None):
    _pack = struct.pack
    def maybe_one_of(tval, *types):
        if tval in types:
            return True
        for item in types:
            if isinstance(tval, item):
                return True
        return False
    def encode(value, default=None):
        tval = type(value)
        if value is None:
            return MARKER_Z,
        elif maybe_one_of (tval, int, long):
            if is_byte(value):
                return MARKER_B, _pack('>b', value)
            elif is_int16(value):
                return MARKER_i, _pack('>h', value)
            elif is_int32(value):
                return MARKER_I, _pack('>i', value)
            elif is_int64(value):
                return MARKER_L, _pack('>q', value)
            else:
                return encode_huge_number(encode, value)
        elif maybe_one_of(tval, float):
            if is_float(value):
                return MARKER_d, struct.pack('>f', value)
            elif is_double(value):
                return MARKER_D, struct.pack('>d', value)
            elif is_infinity(value):
                return MARKER_Z,
            else:
                return encode_huge_number(encode, value)
        elif maybe_one_of(tval, bytes, unicode):
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            length = len(value)
            if length < 255:
                return (MARKER_s, struct.pack('>B', length),
                        struct.pack('>%ds' % length, value))
            else:
                return (MARKER_S, struct.pack('>I', length),
                        struct.pack('>%ds' % length, value))
        elif maybe_one_of(tval, tuple, list, set, frozenset):
            size = len(value)
            if size < 255:
                header = (MARKER_a, struct.pack('>B', size))
            else:
                header = (MARKER_A, struct.pack('>I', size))
            body = (chunk for item in value for chunk in encode(item))
            return chain(header, body)
        elif maybe_one_of(tval, GeneratorType, XRangeType,
                          dict_keysiterator, dict_valuesiterator):
            header = (MARKER_a, MARKER_FF)
            body = (chunk for item in value for chunk in encode(item))
            tail = (MARKER_E,)
            return chain(header, body, tail)
        elif maybe_one_of(tval, dict):
            size = len(value)
            if size < 255:
                header = (MARKER_o, struct.pack('>B', size))
            else:
                header = (MARKER_O, struct.pack('>I', size))
            body = tuple()
            for key, val in value.items():
                assert isinstance(key, basestring), 'object key should be a string'
                body = chain(body, encode(key), encode(val))
            return chain(header, body)
        elif maybe_one_of(tval, dict_itemsiterator):
            header = (MARKER_o, MARKER_FF)
            body = tuple()
            for key, val in value:
                assert isinstance(key, basestring), 'object key should be a string'
                body = chain(body, encode((key, val)))
            tail = (MARKER_E,)
            return chain(header, body, tail)
        elif maybe_one_of(tval, Decimal):
            return encode_huge_number(encode, value)
        elif maybe_one_of (tval, bool):
            return [MARKER_F, MARKER_T][value],
        elif value is NOOP:
            return MARKER_N,
        elif value is EOS:
            return MARKER_E,
        elif default is not None:
            return encode(default(value))
        else:
            raise TypeError('Unable to encode value %r (%r)' % (value, tval))
    if output is None:
        return bytes().join(encode(value, default))
    for chunk in encode(value, default):
        output.write(chunk)

def encode_huge_number(encode, value):
    value = unicode(value).encode('utf-8')
    size = len(value)
    if size < 255:
        return [MARKER_h, struct.pack('>B', size),
                struct.pack('>%ds' % size, value)]
    else:
        return [MARKER_H, struct.pack('>I', size),
                struct.pack('>%ds' % size, value)]


def encode_draft_9(value, output=None, default=None):
    _pack = struct.pack
    def maybe_one_of(tval, *types):
        if tval in types:
            return True
        for item in types:
            if isinstance(tval, item):
                return True
        return False
    def encode(value, default=None):
        tval = type(value)
        if value is None:
            return MARKER_Z,
        elif maybe_one_of (tval, int, long):
            if is_byte(value):
                return MARKER_B, _pack('>b', value)
            elif is_int16(value):
                return MARKER_i, _pack('>h', value)
            elif is_int32(value):
                return MARKER_I, _pack('>i', value)
            elif is_int64(value):
                return MARKER_L, _pack('>q', value)
            else:
                value = unicode(value).encode('utf-8')
                size = len(value)
                data = struct.pack('>%ds' % size, value)
                return chain((MARKER_H,), encode(size), [data])
        elif maybe_one_of(tval, float):
            if is_float(value):
                return MARKER_d, struct.pack('>f', value)
            elif is_double(value):
                return MARKER_D, struct.pack('>d', value)
            elif is_infinity(value):
                return MARKER_Z,
            else:
                value = unicode(value).encode('utf-8')
                size = len(value)
                data = struct.pack('>%ds' % size, value)
                return chain((MARKER_H,), encode(size), [data])
        elif maybe_one_of(tval, bytes, unicode):
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            size = len(value)
            data = struct.pack('>%ds' % size, value)
            return chain((MARKER_S,), encode(size), [data])
        elif maybe_one_of(tval, tuple, list, set, frozenset,
                          GeneratorType, XRangeType,
                          dict_keysiterator, dict_valuesiterator):
            header = (MARKER_A,)
            body = (chunk for item in value for chunk in encode(item))
            tail = (MARKER_E,)
            return chain(header, body, tail)
        elif maybe_one_of(tval, dict, dict_itemsiterator):
            header = (MARKER_O,)
            body = tuple()
            if isinstance(value, dict):
                items = value.items()
            else:
                items = value
            for key, val in items:
                assert isinstance(key, basestring), 'object key should be a string'
                body = chain(body, encode(key), encode(val))
            tail = (MARKER_E,)
            return chain(header, body, tail)
        elif maybe_one_of(tval, Decimal):
            value = unicode(value).encode('utf-8')
            size = len(value)
            data = struct.pack('>%ds' % size, value)
            return chain((MARKER_H,), encode(size), [data])
        elif maybe_one_of (tval, bool):
            return [MARKER_F, MARKER_T][value],
        elif value is NOOP:
            return MARKER_N,
        elif value is EOS:
            return MARKER_E,
        elif default is not None:
            return encode(default(value))
        else:
            raise TypeError('Unable to encode value %r (%r)' % (value, tval))
    if output is None:
        return bytes().join(encode(value, default))
    for chunk in encode(value, default):
        output.write(chunk)

# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
from types import GeneratorType

NOOP = type('NoopType', (object,), {})()

handlers = {}

def pack_data(pattern, data):
    return struct.pack('>' + pattern, data)

def pytypes(*names):
    def decorator(func):
        for name in names:
            handlers[name] = func
        return func
    return decorator

@pytypes(type(NOOP))
def handle_noop(value):
    return ['N']

@pytypes(type(None))
def handle_none(value):
    return ['Z']

@pytypes(bool)
def handle_bool(value):
    return ['F', 'T'][value]

@pytypes(int, long)
def handle_number(value):
    if -128 <= value <= 127:
        return ['B', pack_data('b', value)]
    elif -32768 <= value <= 32767:
        return ['i', pack_data('h', value)]
    elif -2147483648 <= value <= 2147483648:
        return ['I', pack_data('i', value)]
    elif -9223372036854775808L <= value <= 9223372036854775807L:
        return ['L', pack_data('q', value)]
    else:
        return encode_huge_value(value)

@pytypes(float)
def handle_float(value):
    if 1/1.18e38 <= abs(value) <= 3.4e38:
        return ['d', pack_data('f', value)]
    elif 1/2.23e308 <= abs(value) <= 1.80e308:
        return ['D', pack_data('d', value)]
    else:
        return encode_huge_value(value)

@pytypes(str, unicode)
def handle_str(value):
    if isinstance(value, unicode):
        value = value.encode('utf-8')
    length = len(value)
    if length < 255:
        return ['s', pack_data('B', length),
                     pack_data('%ds' % length, value)]
    else:
        return ['S', pack_data('I', length),
                     pack_data('%ds' % length, value)]

@pytypes(tuple, list)
def handle_array(value):
    size = len(value)
    if size < 255:
        yield 'a'
        yield pack_data('B', size)
    else:
        yield 'A'
        yield pack_data('I', size)
    for item in value:
        yield ''.join(encode(item))

@pytypes(GeneratorType)
def handle_generator(value):
    yield 'a'
    yield '\xff'
    for item in value:
        yield encode(item)
    yield 'E'

@pytypes(dict)
def handle_dict(value):
    size = len(value)
    if size < 255:
        yield 'o'
        yield pack_data('B', size)
    else:
        yield 'O'
        yield pack_data('I', size)
    for key, val in value.items():
        yield encode(key)
        yield encode(val)
        
def encode_huge_value(value):
    value = str(value)
    size = len(value)
    if size < 255:
        return ['h', pack_data('B', size),
                     pack_data('%ds' % size, value)]
    else:
        return ['H', pack_data('I', size),
                     pack_data('%ds' % size, value)]

def encode(value, output=None):
    handler = handlers.get(type(value))
    if handler is None:
        raise TypeError('No handlers for value type %s' % type(value))
    try:
        data = handler(value)
        if output is None:
            return ''.join(data)
        else:
            for chunk in data:
                output.write(chunk)
    except struct.error, err:
        raise ValueError('Unable to encode value %s (first 100 bytes),'
                         ' reason:\n%s' % (repr(value)[:100], err))

# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
from StringIO import StringIO
from types import GeneratorType

handlers = {}

def marked_by(marker):
    def wrapper(func):
        handlers[marker] = func
        return func
    return wrapper

def unpack_data(pattern, data):
    return struct.unpack('>' + pattern, data)[0]

@marked_by('N')
def handle_noop(stream):
    raise ValueError('Noop value was not expected')

@marked_by('E')
def handle_eos(stream):
    raise StopIteration

@marked_by('Z')
def handle_null(stream):
    return None

@marked_by('F')
def handle_false(stream):
    return False

@marked_by('T')
def handle_true(stream):
    return True

@marked_by('B')
def handle_byte(stream):
    return unpack_data('b', stream.read(1))

@marked_by('i')
def handle_int16(stream):
    return unpack_data('h', stream.read(2))

@marked_by('I')
def handle_int32(stream):
    return unpack_data('i', stream.read(4))

@marked_by('L')
def handle_int64(stream):
    return unpack_data('q', stream.read(8))

@marked_by('d')
def handle_float(stream):
    return unpack_data('f', stream.read(4))

@marked_by('D')
def handle_double(stream):
    return unpack_data('d', stream.read(8))

@marked_by('h')
def handle_hugeint(stream):
    size = unpack_data('B', stream.read(1))
    return unpack_data('%ds' % size, stream.read(size))

@marked_by('H')
def handle_hugeint_ex(stream):
    size = unpack_data('I', stream.read(4))
    return unpack_data('%ds' % size, stream.read(size))

@marked_by('s')
def handle_str(stream):
    size = unpack_data('B', stream.read(1))
    return unpack_data('%ds' % size, stream.read(size)).decode('utf-8')

@marked_by('S')
def handle_str_ex(stream):
    size = unpack_data('I', stream.read(4))
    return unpack_data('%ds' % size, stream.read(size)).decode('utf-8')

@marked_by('a')
def handle_array(stream):
    size = unpack_data('B', stream.read(1))
    if size == 255:
        return decode_unsized_array(stream)
    else:
        return list(decode_sized_array(stream, size))

@marked_by('A')
def handle_array_ex(stream):
    size = unpack_data('I', stream.read(4))
    return [decode(stream) for item in xrange(size)]

@marked_by('o')
def handle_object(stream):
    size = unpack_data('B', stream.read(1))
    if size == 255:
        return decode_unsized_object(stream)
    else:
        return dict(decode_sized_object(stream, size))

@marked_by('O')
def handle_object_ex(stream):
    size = unpack_data('I', stream.read(4))
    return dict(decode_sized_object(stream, size))

def decode_sized_array(stream, size):
    for round in xrange(size):
        marker, handler = next_marker(stream)
        if marker in 'E':
            raise ValueError('Unexpected marker %r' % marker)
        item = handler(stream)
        if isinstance(item, GeneratorType):
            yield list(item)
        else:
            yield item

def decode_unsized_array(stream):
    while True:
        marker, handler = skip_noop(stream)
        if not marker:
            raise ValueError('Unexpected stream end')
        item = handler(stream)
        if isinstance(item, GeneratorType):
            yield list(item)
        else:
            yield item

def decode_object_key(stream):
    marker, handler = next_marker(stream)
    if not (marker or handler):
        raise ValueError('Unexpected stream end')
    if marker not in 'sS':
        raise ValueError('Object key must be string typed, got %r' % marker)
    return handler(stream)

def decode_sized_object(stream, size):
    for round in xrange(size):
        key = decode_object_key(stream)
        marker, handler = next_marker(stream)
        try:
            item = handler(stream)
        except StopIteration:
            raise ValueError('Unexpected end of stream event')
        if isinstance(item, GeneratorType):
            yield key, list(item)
        else:
            yield key, item

def decode_unsized_object(stream):
    while True:
        marker, handler = skip_noop(stream)
        if not marker:
            raise ValueError('Unexpected stream end')
        if marker not in 'sSE':
            raise ValueError('Object key must be string typed, got %r' % marker)
        key = handler(stream)
        marker, handler = skip_noop(stream)
        try:
            value = handler(stream)
        except StopIteration:
            raise ValueError('Value for key %r expected, but stream end reached'
                             '' % key)
        if isinstance(value, GeneratorType):
            yield list(value)
        else:
            yield key, value

def skip_noop(stream):
    while True:
        marker, handler = next_marker(stream)
        if marker != 'N':
            return marker, handler

def next_marker(stream):
    marker = stream.read(1)
    if not marker:
        return '', None
    return marker, handlers.get(marker)

def decode(stream):
    """Decodes input stream or source string with Universal Binary JSON data
    to Python object.

    :param stream: `.read([size])`-able object or source string.

    :return: Decoded Python object. See mapping table below.

    +--------+----------------------------+----------------------------+-------+
    | Marker | UBJSON type                | Python type                | Notes |
    +========+============================+============================+=======+
    | ``N``  | noop                       |                            | \(1)  |
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
        Noop values are ignored.

    (2)
        Nested generators are automaticaly converted to lists.

    (3)
        Unsized objects are represented as list of key-value tuples.

    :raises:
        ValueError if:
            * Nothing to decode: empty data source.
            * Unsupported marker: probably it's invalid.
            * Unexpected marker: `noop` value or EOS shouldn't occurs in sized
              arrays or objects.
            * Object key is not string type.
    """
    if isinstance(stream, basestring):
        stream = StringIO(stream)
    marker, handler = skip_noop(stream)
    if not (marker or handler):
        raise ValueError('Nothing to decode')
    if marker and handler is None:
        raise ValueError('Unsupported marker %r' % marker)
    return handler(stream)

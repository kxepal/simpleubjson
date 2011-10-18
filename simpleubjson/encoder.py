# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
from types import GeneratorType, XRangeType

#: Noop sentinel value
NOOP = type('NoopType', (object,), {})()

handlers = {}

is_byte = lambda value: (-2 ** 7) <= value <= (2 ** 7 - 1)
is_int16 = lambda value: (-2 ** 15) <= value <= (2 ** 15 - 1)
is_int32 = lambda value: (-2 ** 31) <= value <= (2 ** 31 - 1)
is_int64 = lambda value: (-2 ** 63) <= value <= (2 ** 63 - 1)
is_float = lambda value: 1.18e-38 <= abs(value) <= 3.4e38
is_double = lambda value: 2.23e-308 <= abs(value) < 1.8e308 # 1.8e308 is inf

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
    if is_byte(value):
        return ['B', pack_data('b', value)]
    elif is_int16(value):
        return ['i', pack_data('h', value)]
    elif is_int32(value):
        return ['I', pack_data('i', value)]
    elif is_int64(value):
        return ['L', pack_data('q', value)]
    else:
        return encode_huge_value(value)

@pytypes(float)
def handle_float(value):
    if is_float(value):
        return ['d', pack_data('f', value)]
    elif is_double(value):
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

@pytypes(GeneratorType, XRangeType)
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
    """Encodes Python object to Universal Binary JSON data.

    :param value: Python object.
    :param output: `.write([data])`-able object.

    :return: Encoded Python object. See mapping table below.
             If `output` param is specified, all data would be written into it
             by chunks and None will be returned.

    :raises:
        * TypeError if no handlers specified for passed value type.
        * ValueError if unable to pack Python value to binary form.

    +----------------------------+----------------------------+-------+
    | Python type                | UBJSON type                | Notes |
    +============================+============================+=======+
    | :const:`NOOP`              | noop                       |       |
    +----------------------------+----------------------------+-------+
    | None                       | null                       |       |
    +----------------------------+----------------------------+-------+
    | False                      | false                      |       |
    +----------------------------+----------------------------+-------+
    | True                       | true                       |       |
    +----------------------------+----------------------------+-------+
    | int                        | byte                       | \(1)  |
    +----------------------------+----------------------------+-------+
    | int                        | int16                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | int or long                | int32                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | int or long                | int64                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | float                      | float                      | \(1)  |
    +----------------------------+----------------------------+-------+
    | float                      | double                     | \(1)  |
    +----------------------------+----------------------------+-------+
    | long                       | hugeint                    | \(2)  |
    +----------------------------+----------------------------+-------+
    | str                        | string                     | \(2)  |
    +----------------------------+----------------------------+-------+
    | unicode                    | string                     | \(2)  |
    +----------------------------+----------------------------+-------+
    | tuple                      | sized array                | \(2)  |
    +----------------------------+----------------------------+-------+
    | list                       | sized array                | \(2)  |
    +----------------------------+----------------------------+-------+
    | generator                  | unsized array              |       |
    +----------------------------+----------------------------+-------+
    | dict                       | sized object               | \(2)  |
    +----------------------------+----------------------------+-------+
    | xrange                     | unsized array              |       |
    +----------------------------+----------------------------+-------+

    Notes:

    (1)
        Depending on value it will be encoded to specified UBJSON type:
            * byte: if -128 <= value <= 127
            * int16: if -32768 <= value <= 32767
            * int32: if -2147483648 <= value <= 2147483647
            * int64: if -9223372036854775808 <= value 9223372036854775807
            * float: if 1.18e-38 <= abs(value) <= 3.4e38
            * double: if 2.23e-308 <= abs(value) < 1.80e308

        Any other values would be encoded as hugeint data.

    (2)
        Depending on value length it would be encoded to short data version
        to long one.
    """
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

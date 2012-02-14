# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import struct
from types import GeneratorType, MethodType
from simpleubjson import NOOP

__all__ = ['UBJSONDecoder']

class UBJSONDecoder(object):
    """Base decoder of UBJSON data to Python object that follows next rules:

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
        Noop values are ignored by default if only `allow_noop` argument wasn't
        passed as ``True``.

    (2)
        Nested generators are automatically converted to lists.

    (3)
        Unsized objects are represented as list of 2-element tuples with object
        key and value.
    """
    def __init__(self, default=None, handlers=None, allow_noop=False):
        self._handlers = {
            'N': self.decode_noop,
            'Z': self.decode_null,
            'F': self.decode_false,
            'T': self.decode_true,
            'B': self.decode_byte,
            'i': self.decode_int16,
            'I': self.decode_int32,
            'L': self.decode_int64,
            'd': self.decode_float,
            'D': self.decode_double,
            'h': self.decode_hugeint,
            'H': self.decode_hugeint_ex,
            's': self.decode_str,
            'S': self.decode_str_ex,
            'a': self.decode_array,
            'A': self.decode_array_ex,
            'o': self.decode_object,
            'O': self.decode_object_ex,
            'E': self.decode_eos,
        }
        self.allow_noop = allow_noop
        if default is not None:
            self.decode_default = MethodType(default, self)
        if handlers is not None:
            for key, handler in handlers.items():
                if handler is not None:
                    handlers[key] = MethodType(handler, self)
            self._handlers.update(handlers)

    def decode(self, stream):
        marker, handler = self.skip_noop(stream)
        if not (marker or handler):
            raise ValueError('Nothing to decode')
        if marker and handler is None:
            raise ValueError('Unsupported marker %r' % marker)
        return handler(stream)

    def get_handler(self, marker):
        handler = self._handlers.get(marker)
        if handler is None:
            return (lambda stream: self.decode_default(marker, stream))
        return handler

    def unpack_data(self, pattern, data):
        return struct.unpack('>' + pattern, data)[0]

    def next_marker(self, stream):
        marker = stream.read(1)
        if not marker:
            return '', None
        return marker, self.get_handler(marker)

    def skip_noop(self, stream):
        while True:
            marker, handler = self.next_marker(stream)
            if marker != 'N':
                return marker, handler

    def decode_default(self, marker, stream):
        raise ValueError('Unable to decode data with marker %r' % marker)

    def decode_noop(self, stream):
        raise ValueError('Noop value was not expected')

    def decode_eos(self, stream):
        raise StopIteration

    def decode_null(self, stream):
        return None

    def decode_false(self, stream):
        return False

    def decode_true(self, stream):
        return True

    def decode_byte(self, stream):
        return self.unpack_data('b', stream.read(1))

    def decode_int16(self, stream):
        return self.unpack_data('h', stream.read(2))

    def decode_int32(self, stream):
        return self.unpack_data('i', stream.read(4))

    def decode_int64(self, stream):
        return self.unpack_data('q', stream.read(8))

    def decode_float(self, stream):
        return self.unpack_data('f', stream.read(4))

    def decode_double(self, stream):
        return self.unpack_data('d', stream.read(8))

    def decode_hugeint(self, stream):
        size = self.unpack_data('B', stream.read(1))
        return self.unpack_data('%ds' % size, stream.read(size))

    def decode_hugeint_ex(self, stream):
        size = self.unpack_data('I', stream.read(4))
        return self.unpack_data('%ds' % size, stream.read(size))

    def decode_str(self, stream):
        size = self.unpack_data('B', stream.read(1))
        return self.unpack_data('%ds' % size, stream.read(size)).decode('utf-8')

    def decode_str_ex(self, stream):
        size = self.unpack_data('I', stream.read(4))
        return self.unpack_data('%ds' % size, stream.read(size)).decode('utf-8')

    def decode_array(self, stream):
        size = self.unpack_data('B', stream.read(1))
        if size == 255:
            return self.decode_unsized_array(stream)
        else:
            return list(self.decode_sized_array(stream, size))

    def decode_array_ex(self, stream):
        size = self.unpack_data('I', stream.read(4))
        return [self.decode(stream) for item in xrange(size)]

    def decode_object(self, stream):
        size = self.unpack_data('B', stream.read(1))
        if size == 255:
            return self.decode_unsized_object(stream)
        else:
            return dict(self.decode_sized_object(stream, size))

    def decode_object_ex(self, stream):
        size = self.unpack_data('I', stream.read(4))
        return dict(self.decode_sized_object(stream, size))

    def decode_sized_array(self, stream, size):
        for round in xrange(size):
            marker, handler = self.skip_noop(stream)
            if marker in 'E':
                raise ValueError('Unexpected marker %r' % marker)
            item = handler(stream)
            if isinstance(item, GeneratorType):
                yield list(item)
            else:
                yield item

    def decode_unsized_array(self, stream):
        while True:
            marker, handler = self.next_marker(stream)
            if marker == 'N':
                if self.allow_noop:
                    yield NOOP
                continue
            if not marker:
                raise ValueError('Unexpected stream end')
            item = handler(stream)
            if isinstance(item, GeneratorType):
                yield list(item)
            else:
                yield item

    def decode_object_key(self, stream):
        marker, handler = self.skip_noop(stream)
        if not (marker or handler):
            raise ValueError('Unexpected stream end')
        if marker not in 'sS':
            raise ValueError('Object key must be string typed, got %r' % marker)
        return handler(stream)

    def decode_sized_object(self, stream, size):
        for round in xrange(size):
            key = self.decode_object_key(stream)
            marker, handler = self.skip_noop(stream)
            try:
                item = handler(stream)
            except StopIteration:
                raise ValueError('Unexpected end of stream event')
            if isinstance(item, GeneratorType):
                yield key, list(item)
            else:
                yield key, item

    def decode_unsized_object(self, stream):
        while True:
            marker, handler = self.next_marker(stream)
            if marker == 'N':
                if self.allow_noop:
                    yield NOOP, NOOP
                continue
            if not marker:
                raise ValueError('Unexpected stream end')
            if marker not in 'sSE':
                raise ValueError('Object key must be string typed,'
                                 ' got %r' % marker)
            key = handler(stream)
            marker, handler = self.skip_noop(stream)
            try:
                value = handler(stream)
            except StopIteration:
                raise ValueError('Value for key %r expected,'
                                 ' but stream end reached'  % key)
            if isinstance(value, GeneratorType):
                yield list(value)
            else:
                yield key, value

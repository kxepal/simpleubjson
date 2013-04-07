# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2013 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

from decimal import Decimal
from struct import pack, unpack
from types import *
from simpleubjson import NOOP as NOOP_SENTINEL
from simpleubjson.exceptions import (
    EncodeError, MarkerError, EarlyEndOfStreamError
)
from simpleubjson.compat import (
    BytesIO, b, bytes, unicode,
    dict_itemsiterator, dict_keysiterator, dict_valuesiterator
)


NOOP = b('N')
NULL = b('Z')
FALSE = b('F')
TRUE = b('T')
INT8 = b('i')
INT16 = b('I')
INT32 = b('l')
INT64 = b('L')
FLOAT = b('d')
DOUBLE = b('D')
STRING = b('S')
HIDEF = b('H')
ARRAY_OPEN = b('[')
ARRAY_CLOSE = b(']')
OBJECT_OPEN = b('{')
OBJECT_CLOSE = b('}')

BOS_A = object()
BOS_O = object()

CONSTANTS = set([NOOP, NULL, FALSE, TRUE])
CONTAINERS = set([ARRAY_OPEN, ARRAY_CLOSE, OBJECT_OPEN, OBJECT_CLOSE])
NUMBERS = set([INT8, INT16, INT32, INT64, FLOAT, DOUBLE])
STRINGS = set([STRING, HIDEF])


__all__ = ['Draft9Decoder', 'Draft9Encoder']


class Draft9Decoder(object):
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
    | ``[``  | array - unsized            | generator                  | \(2)  |
    +--------+----------------------------+----------------------------+-------+
    | ``{``  | object - unsized           | generator                  | \(3)  |
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
    dispatch = {}

    def __init__(self, source, allow_noop=False, stream=False):
        if isinstance(source, unicode):
            source = source.encode('utf-8')
        if isinstance(source, bytes):
            source = BytesIO(source)
        self.index = []
        self.stack = []
        self.read = source.read
        self.emit = self.stack.append
        self.allow_noop = allow_noop
        self.dispatch = self.dispatch.copy()
        self.streaming = stream

    def __iter__(self):
        return self

    def next_tlv(self):
        while 1:
            tag = self.read(1)
            if not tag:
                raise EarlyEndOfStreamError('nothing to decode')
            if tag == NOOP and not self.allow_noop:
                continue
            break
        if tag in NUMBERS:
            if tag == INT8:
                # Trivial operations for trivial cases saves a lot of time
                value = ord(self.read(1))
                if value > 128:
                    value -= 256
                    #value, = unpack('>b', self.read(1))
            elif tag == INT16:
                value, = unpack('>h', self.read(2))
            elif tag == INT32:
                value, = unpack('>i', self.read(4))
            elif tag == INT64:
                value, = unpack('>q', self.read(8))
            elif tag == FLOAT:
                value, = unpack('>f', self.read(4))
            elif tag == DOUBLE:
                value, = unpack('>d', self.read(8))
            else:
                assert False, 'tag %r not in NUMBERS %r' % (tag, NUMBERS)
            return tag, None, value
        elif tag in STRINGS:
            # Don't be recursive for string length calculation to save time
            ltag = self.read(1)
            if ltag == INT8:
                length = ord(self.read(1))
                if length > 128:
                    length -= 256
            elif ltag == INT16:
                length, = unpack('>h', self.read(2))
            elif ltag == INT32:
                length, = unpack('>i', self.read(4))
            elif ltag == INT64:
                length, = unpack('>q', self.read(8))
            elif not ltag:
                raise EarlyEndOfStreamError('string length marker missed')
            else:
                raise MarkerError('invalid string size marker 0x%02X (%r)'
                                  '' % (ord(ltag), ltag))
            return tag, length, self.read(length)
        elif tag in CONSTANTS or tag in CONTAINERS:
            return tag, None, None
        else:
            raise MarkerError('invalid marker 0x%02x (%r)' % (ord(tag), tag))

    def decode_next(self):
        tag, length, value = self.next_tlv()
        value = self.dispatch[tag](self, tag, length, value)
        if self.stack:
            return self.stack.pop()
        return value

    __next__ = next = decode_next

    def stream(self, root_container):
        stash = []
        while 1:
            value = self.decode_next()
            if not (self.stack or self.index):
                pass
            if not value:
                assert len(self.stack) == 1
                value = self.stack.pop()
                if root_container == BOS_O:
                    stash.append(value)
                    if len(stash) == 2:
                        yield tuple(stash)
                        stash = []
                else:
                    yield value
            elif not self.index:
                break

    def decode_noop(self, tag, length, value):
        return NOOP_SENTINEL
    dispatch[NOOP] = decode_noop

    def decode_none(self, tag, length, value):
        return None
    dispatch[NULL] = decode_none

    def decode_false(self, tag, length, value):
        return False
    dispatch[FALSE] = decode_false

    def decode_true(self, tag, length, value):
        return True
    dispatch[TRUE] = decode_true

    def decode_int(self, tag, length, value):
        return value
    dispatch[INT8] = decode_int
    dispatch[INT16] = decode_int
    dispatch[INT32] = decode_int
    dispatch[INT64] = decode_int

    def decode_float(self, tag, length, value):
        return value
    dispatch[FLOAT] = decode_float
    dispatch[DOUBLE] = decode_float

    def decode_string(self, tag, length, value):
        return value.decode('utf-8')
    dispatch[STRING] = decode_string

    def decode_hidef(self, tag, length, value):
        return Decimal(value.decode('utf-8'))
    dispatch[HIDEF] = decode_hidef

    def decode_array_open(self, tag, length, value):
        self.index.append((BOS_A, len(self.stack)))
    dispatch[ARRAY_OPEN] = decode_array_open

    def decode_object_open(self, tag, length, value):
        self.index.append((BOS_O, len(self.stack)))
    dispatch[OBJECT_OPEN] = decode_object_open

    def decode_array(self, tag, length, value):
        if self.streaming and not self.index:
            raise StopIteration
        raise EarlyEndOfStreamError
    dispatch[ARRAY_CLOSE] = decode_array

    def decode_object(self, tag, length, value):
        if self.streaming and not self.index:
            raise StopIteration
        raise EarlyEndOfStreamError
    dispatch[OBJECT_CLOSE] = decode_object

    def decode_array_stream(self, tag, length, value):
        def array_stream():
            while 1:
                tag, length, value = self.next_tlv()
                if tag == ARRAY_CLOSE:
                    break
                elif tag in [ARRAY_OPEN, OBJECT_OPEN]:
                    yield list(self.dispatch[tag](self, tag, length, value))
                else:
                    yield self.dispatch[tag](self, tag, length, value)
        return array_stream()
    dispatch[ARRAY_OPEN] = decode_array_stream

    def decode_object_stream(self, tag, length, value):
        def object_stream():
            key = None
            while 1:
                tag, length, value = self.next_tlv()
                if tag == NOOP and key is None:
                    yield NOOP_SENTINEL, NOOP_SENTINEL
                elif tag == NOOP and key:
                    continue
                elif tag == OBJECT_CLOSE:
                    if key:
                        raise EarlyEndOfStreamError(
                            'value missed for key %r' % key)
                    break
                elif tag != STRING and key is None:
                    raise ValueError('key should be string')
                else:
                    value = self.dispatch[tag](self, tag, length, value)
                    if key is None:
                        key = value
                    elif tag in [ARRAY_OPEN, OBJECT_OPEN]:
                        yield key, list(value)
                        key = None
                    else:
                        yield key, value
                        key = None
        return object_stream()
    dispatch[OBJECT_OPEN] = decode_object_stream


class Draft9Encoder(object):
    """Encoder of Python objects into UBJSON data following Draft 9
    specification rules with next data mapping:

    +-----------------------------+------------------------------------+-------+
    | Python type                 | UBJSON type                        | Notes |
    +=====================================+============================+=======+
    | :const:`~simpleubjson.NOOP` | NoOp                               |       |
    +-----------------------------+------------------------------------+-------+
    | :const:`None`               | null                               |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`bool`               | :const:`False` => false            |       |
    |                             | :const:`True`  => true             |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`int`,               | `integer` or `huge`                | \(1)  |
    | :class:`long`               |                                    |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`float`              | `float`, `null` or `huge`          | \(2)  |
    +-----------------------------+------------------------------------+-------+
    | :class:`str`,               | string                             | \(3)  |
    | :class:`unicode`            |                                    |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`tuple`,             | array                              |       |
    | :class:`list`,              |                                    |       |
    | :class:`generator`,         |                                    |       |
    | :class:`set`,               |                                    |       |
    | :class:`frozenset`,         |                                    |       |
    | :class:`XRange`             |                                    |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`dict`               | object                             |       |
    +-----------------------------+------------------------------------+-------+
    | :class:`decimal.Decimal`    | huge                               |       |
    +-----------------------------+------------------------------------+-------+

    Notes:

    (1)
        Depending on value it may be encoded into various UBJSON types:

            * [-2^7, 2^7): ``int8``
            * [-2^15, 2^15): ``int16``
            * [-2^31, 2^31): ``int32``
            * [-2^63, 2^63): ``int64``
            * everything bigger/smaller: ``huge``

    (2)
        Depending on value it may be encoded into various UBJSON types:

            * 1.18e-38 <= abs(value) <= 3.4e38: ``float``
            * 2.23e-308 <= abs(value) < 1.8e308: ``double``
            * :const:`inf`, :const:`-inf`: ``null``
            * everything bigger/smaller: ``huge``

    (3)
        If string is `unicode` it will be encoded with `utf-8` charset.
    """

    dispatch = {}

    def __init__(self, default=None):
        self._default = default or self.default

    def default(self, obj):
        raise EncodeError('unable to encode %r' % obj)

    def encode_next(self, obj):
        tobj = type(obj)
        if tobj in self.dispatch:
            res = self.dispatch[tobj](self, obj)
        else:
            return self.encode_next(self._default(obj))
        if isinstance(res, GeneratorType):
            return bytes().join(res)
        return res

    def encode_noop(self, obj):
        return NOOP
    dispatch[type(NOOP_SENTINEL)] = encode_noop

    def encode_none(self, obj):
        return NULL
    dispatch[NoneType] = encode_none

    def encode_bool(self, obj):
        return [FALSE, TRUE][obj]
    dispatch[BooleanType] = encode_bool

    def encode_int(self, obj):
        if (-2 ** 7) <= obj <= (2 ** 7 - 1):
            return INT8 + chr(obj % 256)
        elif (-2 ** 15) <= obj <= (2 ** 15 - 1):
            marker = INT16
            token = '>h'
        elif (-2 ** 31) <= obj <= (2 ** 31 - 1):
            marker = INT32
            token = '>i'
        elif (-2 ** 63) <= obj <= (2 ** 63 - 1):
            marker = INT64
            token = '>q'
        else:
            return self.encode_decimal(Decimal(obj))
        return marker + pack(token, obj)
    dispatch[IntType] = encode_int
    dispatch[LongType] = encode_int

    def encode_float(self, obj):
        if 1.18e-38 <= abs(obj) <= 3.4e38:
            marker = FLOAT
            token = '>f'
        elif 2.23e-308 <= abs(obj) < 1.8e308:
            marker = DOUBLE
            token = '>d'
        elif obj == float('inf') or obj == float('-inf'):
            return NULL
        else:
            return self.encode_decimal(Decimal(obj))
        return marker + pack(token, obj)
    dispatch[FloatType] = encode_float

    def encode_str(self, obj):
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        return STRING + self.encode_int(len(obj)) + obj
    dispatch[StringType] = encode_str
    dispatch[UnicodeType] = encode_str

    def encode_decimal(self, obj):
        obj = unicode(obj).encode('utf-8')
        return HIDEF + self.encode_int(len(obj)) + obj
    dispatch[Decimal] = encode_decimal

    def encode_sequence(self, obj):
        yield ARRAY_OPEN
        for item in obj:
            yield self.encode_next(item)
        yield ARRAY_CLOSE
    dispatch[TupleType] = encode_sequence
    dispatch[ListType] = encode_sequence
    dispatch[GeneratorType] = encode_sequence
    dispatch[set] = encode_sequence
    dispatch[frozenset] = encode_sequence
    dispatch[XRangeType] = encode_sequence
    dispatch[dict_keysiterator] = encode_sequence
    dispatch[dict_valuesiterator] = encode_sequence

    def encode_dict(self, obj):
        yield OBJECT_OPEN
        if isinstance(obj, dict):
            items = obj.items()
        else:
            items = obj
        for key, value in items:
            yield self.encode_str(key)
            yield self.encode_next(value)
        yield OBJECT_CLOSE
    dispatch[dict] = encode_dict
    dispatch[dict_itemsiterator] = encode_dict

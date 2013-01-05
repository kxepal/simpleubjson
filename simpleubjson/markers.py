# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

from decimal import Decimal
from itertools import chain
from struct import pack
from types import GeneratorType
from simpleubjson import NOOP, EOS, EOS_A, EOS_O
from simpleubjson.compat import b, basestring, unicode, xrange


class Marker(object):
    """Base marker class."""
    __slots__ = ()

    tag = None
    length = None
    value = None
    eos = None

    def decode(self, decoder, stream, tlv):
        raise NotImplementedError

    def encode(self, encode, obj):
        raise NotImplementedError


class NoopMarker(Marker):

    __slots__ = ()

    tag = b('N')

    def decode(self, decoder, stream, tlv):
        return NOOP

    def encode(self, encode, obj):
        return [self.tag]


class EndOfStreamMarker(Marker):

    __slots__ = ()

    tag = b('E')

    def decode(self, decoder, stream, tlv):
        return EOS

    def encode(self, encode, obj):
        return [self.tag]


class EndOfArrayStreamMarker(EndOfStreamMarker):

    __slots__ = ()

    tag = ']'

    def decode(self, decoder, stream, tlv):
        return EOS_A


class EndOfObjectStreamMarker(EndOfStreamMarker):

    __slots__ = ()

    tag = '}'

    def decode(self, decoder, stream, tlv):
        return EOS_O


class NullMarker(Marker):

    __slots__ = ()

    tag = b('Z')

    def decode(self, decoder, stream, tlv):
        return None

    def encode(self, encode, obj):
        return [self.tag]


class BooleanMarker(Marker):

    __slots__ = ()

    def encode(self, encode, obj):
        return [self.tag]


class FalseMarker(BooleanMarker):

    __slots__ = ()

    tag = b('F')

    def decode(self, decoder, stream, tlv):
        return False


class TrueMarker(BooleanMarker):

    __slots__ = ()

    tag = b('T')

    def decode(self, decoder, stream, tlv):
        return True


class NumericMarker(Marker):

    __slots__ = ()

    def decode(self, decoder, stream, tlv):
        return tlv[2]

    def encode(self, encode, obj):
        return self.tag, pack(self.value, obj)


class IntegerMarker(NumericMarker):

    __slots__ = ()


class ByteMarker(IntegerMarker):

    __slots__ = ()

    tag = b('B')
    value = '>b'


class ShortIntMarker(IntegerMarker):

    __slots__ = ()

    tag = b('i')
    value = '>h'


class IntMarker(IntegerMarker):

    __slots__ = ()

    tag = b('I')
    value = '>i'


class LongIntMarker(IntegerMarker):

    __slots__ = ()

    tag = b('L')
    value = '>q'


class Int8Marker(ByteMarker):

    __slots__ = ()

    tag = b('i')


class Int16Marker(ShortIntMarker):

    __slots__ = ()

    tag = b('I')


class Int32Marker(IntMarker):

    __slots__ = ()

    tag = b('l')


class Int64Marker(LongIntMarker):

    __slots__ = ()

    tag = b('L')


class FloatMarker(NumericMarker):

    __slots__ = ()

    tag = b('d')
    value = '>f'


class DoubleMarker(FloatMarker):

    __slots__ = ()

    tag = b('D')
    value = '>d'


class TextMarker(Marker):

    __slots__ = ()

    def decode(self, decoder, stream, tlv):
        return tlv[2].decode('utf-8')

    def encode(self, encode, obj):
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        size = len(obj)
        length = pack(self.length, size)
        value = pack(self.value % size, obj)
        return self.tag, length, value


class ShortStringMarker(TextMarker):

    __slots__ = ()

    tag = b('s')
    length = '>B'
    value = '>%ds'


class LongStringMarker(TextMarker):

    __slots__ = ()

    tag = b('S')
    length = '>I'
    value = '>%ds'


class StringMarker(TextMarker):

    __slots__ = ()

    tag = b('S')
    length = NumericMarker
    value = '>%ds'

    def encode(self, encode, obj):
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        size = len(obj)
        length = encode(size)
        value = pack(self.value % size, obj)
        return self.tag, length, value


class HugeMarker(Marker):

    __slots__ = ()

    def decode(self, decoder, stream, tlv):
        return Decimal(tlv[2].decode('utf-8'))

    def encode(self, encode, obj):
        if isinstance(obj, Decimal):
            obj = unicode(obj)
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        size = len(obj)
        length = pack(self.length, size)
        value = pack(self.value % size, obj)
        return self.tag, length, value


class ShortHugeMarker(HugeMarker):

    __slots__ = ()

    tag = b('h')
    length = '>B'
    value = '>%ds'


class LongHugeMarker(HugeMarker):

    __slots__ = ()

    tag = b('H')
    length = '>I'
    value = '>%ds'


class HighDefinitionMarker(HugeMarker):

    __slots__ = ()

    tag = b('H')
    length = NumericMarker
    value = '>%ds'

    def encode(self, encode, obj):
        if isinstance(obj, Decimal):
            obj = unicode(obj)
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        size = len(obj)
        length = encode(size)
        value = pack(self.value % size, obj)
        return self.tag, length, value


class ContainerMarker(Marker):

    __slots__ = ()


class UnsizedContainer(object):
    pass


class ArrayMarker(ContainerMarker):

    __slots__ = ()


class SizedArrayMarker(ArrayMarker):

    __slots__ = ()

    def decode(self, decode, stream, tlv):
        obj = []
        _append = obj.append
        eos = (EOS, EOS_A, EOS_O)
        for round in xrange(tlv[1]):
            while True:
                item = decode(stream)
                if item is not NOOP:
                    break
            if item in eos:
                raise ValueError('unexpectable end of stream marker')
            if isinstance(item, GeneratorType):
                item = list(item)
            _append(item)
        return obj

    def encode(self, encode, obj):
        size = len(obj)
        length = pack(self.length, size)
        value = (encode(item) for item in obj)
        return chain([self.tag, length], value)


class ShortArrayMarker(SizedArrayMarker):

    __slots__ = ()

    tag = b('a')
    length = '>B'


class LongArrayMarker(SizedArrayMarker):

    __slots__ = ()

    tag = b('A')
    length = '>I'


class UnsizedArrayMarker(ArrayMarker, UnsizedContainer):

    __slots__ = ()

    eos = EOS

    def decode(self, decode, stream, tlv):
        eos = self.eos
        while True:
            item = decode(stream)
            if item is eos:
                break
            elif isinstance(item, GeneratorType):
                item = list(item)
            yield item


class StreamedArrayMarker(UnsizedArrayMarker):

    __slots__ = ()

    tag = b('a')

    def encode(self, encode, obj):
        value = (encode(item) for item in obj)
        return chain([self.tag, b('\xff')], value, [encode(self.eos)])


class JsonLikeUnsizedArrayMarker(UnsizedArrayMarker):

    __slots__ = ()

    tag = b('[')
    eos = EOS_A

    def encode(self, encode, obj):
        value = (encode(item) for item in obj)
        return chain([self.tag], value, [encode(self.eos)])


class ObjectMarker(ContainerMarker):

    __slots__ = ()

    def encode(self, encode, obj):
        value = ()
        if isinstance(obj, dict):
            items = obj.items()
        else:
            items = obj
        for key, item in items:
            assert isinstance(key, basestring), 'object key must be a string'
            value = chain(value, [encode(key)], [encode(item)])
        return value


class SizedObjectMarker(ObjectMarker):

    __slots__ = ()

    def decode(self, decode, stream, tlv):
        obj = {}
        eos = (EOS, EOS_A, EOS_O)
        for round in xrange(tlv[1]):
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
            if value in eos:
                raise ValueError('unexpectable end of stream marker')
            if isinstance(value, GeneratorType):
                value = list(value)
            obj[key] = value
        return obj

    def encode(self, encode, obj):
        length = pack(self.length, len(obj))
        value = super(SizedObjectMarker, self).encode(encode, obj)
        return chain([self.tag, length], value)


class ShortObjectMarker(SizedObjectMarker):

    __slots__ = ()

    tag = b('o')
    length = '>B'


class LongObjectMarker(SizedObjectMarker):

    __slots__ = ()

    tag = b('O')
    length = '>I'


class UnsizedObjectMarker(ObjectMarker, UnsizedContainer):

    __slots__ = ()

    def decode(self, decode, stream, tlv):
        eos = self.eos
        while True:
            while True:
                key = decode(stream)
                if key is not NOOP:
                    break
                yield key, key
            if key is eos:
                break
            if not isinstance(key, unicode):
                msg = 'key should be string, not %r' % key
                raise ValueError(msg)
            while True:
                value = decode(stream)
                if value is not NOOP:
                    break
            if value is eos:
                msg = 'unexpectable end of stream marker %r' % value
                raise ValueError(msg)
            if isinstance(value, GeneratorType):
                value = list(value)
            yield key, value


class StreamedObjectMarker(UnsizedObjectMarker):

    __slots__ = ()

    tag = b('o')
    eos = EOS

    def encode(self, encode, obj):
        value = super(StreamedObjectMarker, self).encode(encode, obj)
        return chain([self.tag, b('\xff')], value, [encode(self.eos)])


class JsonLikeUnsizedObjectMarker(UnsizedObjectMarker):

    __slots__ = ()

    tag = b('{')
    eos = EOS_O

    def encode(self, encode, obj):
        value = super(JsonLikeUnsizedObjectMarker, self).encode(encode, obj)
        return chain([self.tag], value, [encode(self.eos)])


DRAFT8_MARKERS = [
    NoopMarker(),
    EndOfStreamMarker(),
    NullMarker(),
    FalseMarker(),
    TrueMarker(),
    ByteMarker(),
    ShortIntMarker(),
    IntMarker(),
    LongIntMarker(),
    FloatMarker(),
    DoubleMarker(),
    ShortStringMarker(),
    LongStringMarker(),
    ShortHugeMarker(),
    LongHugeMarker(),
    ShortArrayMarker(),
    LongArrayMarker(),
    # StreamedArrayMarker(), # special case
    ShortObjectMarker(),
    LongObjectMarker(),
    # StreamedObjectMarker() # special case
]

DRAFT9_MARKERS = [
    NoopMarker(),
    EndOfArrayStreamMarker(),
    EndOfObjectStreamMarker(),
    NullMarker(),
    FalseMarker(),
    TrueMarker(),
    Int8Marker(),
    Int16Marker(),
    Int32Marker(),
    Int64Marker(),
    FloatMarker(),
    DoubleMarker(),
    StringMarker(),
    HighDefinitionMarker(),
    JsonLikeUnsizedArrayMarker(),
    JsonLikeUnsizedObjectMarker()
]

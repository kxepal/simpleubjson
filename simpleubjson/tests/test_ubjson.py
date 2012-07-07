# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import datetime
import unittest
import simpleubjson
from types import GeneratorType
from decimal import Decimal
from simpleubjson.compat import BytesIO as StringIO, b, u, long, xrange


class Draft8TestCase(unittest.TestCase):
    def setUp(self):
        self.decode = lambda *a, **k: simpleubjson.decode(spec='draft-8', *a, **k)
        self.encode = lambda *a, **k: simpleubjson.encode(spec='draft-8', *a, **k)


class DecoderTestCase(Draft8TestCase):

    def test_skip_head_noops(self):
        data = self.decode(b('NNNNNNNNNNNNNZ'))
        self.assertTrue(data is None)

    def test_skip_trailing_data(self):
        data = self.decode(b('Zfoobarbaz'))
        self.assertTrue(data is None)

    def test_no_data(self):
        self.assertRaises(ValueError, self.decode, b(''))

    def test_fail_on_unknown_marker(self):
        self.assertRaises(ValueError, self.decode, 'Я')

    def test_custom_default_handler(self):
        def dummy(marker):
            assert marker == '%'
            return 's', 3, b('foo')
        data = self.decode(b('%'), default=dummy)
        self.assertEqual(data, 'foo')


class EncoderTestCase(Draft8TestCase):

    def test_fail_if_no_handler_matches(self):
        self.assertRaises(TypeError, self.encode, object())

    def test_write_encoded_data_to_stream(self):
        stream = StringIO()
        self.encode((i for i in range(5)), stream)
        self.assertEqual(stream.getvalue(),
                         b('a\xffB\x00B\x01B\x02B\x03B\x04E'))

    def test_custom_default_handler(self):
        sentinel = object()
        def dummy(value):
            assert value is sentinel
            return [b('sentinel')]
        data = self.encode(sentinel, default=dummy)
        self.assertEqual(data, b('a\x01s\x08sentinel'))


class NoopTestCase(Draft8TestCase):

    def test_decode(self):
        data = self.decode('N', allow_noop=True)
        self.assertTrue(data is simpleubjson.NOOP)

    def test_encode(self):
        data = self.encode(simpleubjson.NOOP)
        self.assertEqual(data, b('N'))


class NullTestCase(Draft8TestCase):

    def test_decode(self):
        data = self.decode('Z')
        self.assertTrue(data is None)

    def test_encode(self):
        data = self.encode(None)
        self.assertEqual(data, b('Z'))


class BooleanTestCase(Draft8TestCase):

    def test_false_decode(self):
        data = self.decode('F')
        self.assertEqual(data, False)

    def test_false_encode(self):
        data = self.encode(False)
        self.assertEqual(data, b('F'))

    def test_true_decode(self):
        data = self.decode('T')
        self.assertEqual(data, True)

    def test_true_encode(self):
        data = self.encode(True)
        self.assertEqual(data, b('T'))


class ByteTestCase(Draft8TestCase):

    def test_decode(self):
        data = self.decode('B\x2a')
        self.assertEqual(data, 42)

    def test_encode(self):
        data = self.encode(42)
        self.assertEqual(data, b('B\x2a'))

    def test_decode_negative(self):
        data = self.decode(b('B\xd6'))
        self.assertEqual(data, -42)

    def test_encode_negative(self):
        data = self.encode(-42)
        self.assertEqual(data, b('B\xd6'))


class Integer16TestCase(Draft8TestCase):

    def test_decode(self):
        data = self.decode(b('i\x30\x39'))
        self.assertEqual(data, 12345)

    def test_encode(self):
        data = self.encode(12345)
        self.assertEqual(data, b('i\x30\x39'))

    def test_decode_negative(self):
        data = self.decode(b('i\xa0\xff'))
        self.assertEqual(data, -24321)

    def test_encode_negative(self):
        data = self.encode(-24321)
        self.assertEqual(data, b('i\xa0\xff'))


class Integer32TestCase(Draft8TestCase):

    def test_decode(self):
        data = self.decode(b('I\x00\x01\x88\x94'))
        self.assertEqual(data, 100500)

    def test_encode(self):
        data = self.encode(100500)
        self.assertEqual(data, b('I\x00\x01\x88\x94'))

    def test_decode_negative(self):
        data = self.decode(b('I\xff\xfe\x77\x6c'))
        self.assertEqual(data, -100500)

    def test_encode_negative(self):
        data = self.encode(-100500)
        self.assertEqual(data, b('I\xff\xfe\x77\x6c'))


class Integer64TestCase(Draft8TestCase):

    def test_decode(self):
        data = self.decode(b('L\x7f\xff\xff\xff\xff\xff\xff\xff'))
        self.assertEqual(data, long('9223372036854775807'))

    def test_encode(self):
        data = self.encode(long('9223372036854775807'))
        self.assertEqual(data, b('L\x7f\xff\xff\xff\xff\xff\xff\xff'))

    def test_decode_negative(self):
        data = self.decode(b('L\x80\x00\x00\x00\x00\x00\x00\x00'))
        self.assertEqual(data, long('-9223372036854775808'))

    def test_encode_negative(self):
        data = self.encode(long('-9223372036854775808'))
        self.assertEqual(data, b('L\x80\x00\x00\x00\x00\x00\x00\x00'))


class HugeNumberTestCase(Draft8TestCase):

    def test_decode(self):
        source = b('h\x33314159265358979323846264338327950288419716939937510')
        expected = Decimal('314159265358979323846264338327950288419716939937510')
        data = self.decode(source)
        self.assertEqual(data, expected)

    def test_decode_huge_float(self):
        source = b('h\x35-3.14159265358979323846264338327950288419716939937510')
        expected = Decimal('-3.14159265358979323846264338327950288419716939937510')
        data = self.decode(source)
        self.assertEqual(data, expected)

    def test_decode_exp_number(self):
        source = b('h\x052e+10')
        expected = Decimal('2e+10')
        data = self.decode(source)
        self.assertEqual(data, expected)

    def test_encode(self):
        source = 314159265358979323846264338327950288419716939937510
        expected = b('h\x33314159265358979323846264338327950288419716939937510')
        data = self.encode(source)
        self.assertEqual(data, expected)

    def test_encode_decimal(self):
        source = Decimal('3.14')
        expected = b('h\x043.14')
        data = self.encode(source)
        self.assertEqual(data, expected)

    def test_fail_on_invalid_numeric_value(self):
        source = b('h\x33314159 65358979323846264338327950288419716939937510')
        self.assertRaises(ArithmeticError, self.decode, source)

    def test_fail_on_non_numeric_value(self):
        source = b('h\x09foobarbaz')
        self.assertRaises(ArithmeticError, self.decode, source)


class FloatTestCase(Draft8TestCase):

    def test_decode_float(self):
        data = self.decode(b('d\x40\x48\xf5\xc3'))
        self.assertEqual(round(data, 2), 3.14)

    def test_encode_float(self):
        data = self.encode(3.14)
        self.assertEqual(data, b('d\x40\x48\xf5\xc3'))

    def test_decode_double(self):
        data = self.decode(b('D\x71\x8e\xde\x0b\x49\x13\x5b\x25'))
        self.assertEqual(data, 100500e234)

    def test_encode_double(self):
        data = self.encode(100500e234)
        self.assertEqual(data, b('D\x71\x8e\xde\x0b\x49\x13\x5b\x25'))

    def test_encode_min_float(self):
        data = self.encode(-1.18e-38)
        self.assertEqual(data, b('d\x80\x80\x7d\x99'))
        data = self.encode(-3.4e38)
        self.assertEqual(data, b('d\xff\x7f\xc9\x9e'))

    def test_encode_max_float(self):
        data = self.encode(1.18e-38)
        self.assertEqual(data, b('d\x00\x80\x7d\x99'))
        data = self.encode(3.4e38)
        self.assertEqual(data, b('d\x7f\x7f\xc9\x9e'))

    def test_encode_min_double(self):
        data = self.encode(-2.23e-308)
        self.assertEqual(data, b('D\x80\x10\x09\x11\x77\x58\x7f\x83'))
        data = self.encode(-1.79e308)
        self.assertEqual(data, b('D\xff\xef\xdc\xf1\x58\xad\xbb\x99'))

    def test_encode_max_double(self):
        data = self.encode(2.23e-308)
        self.assertEqual(data, b('D\x00\x10\x09\x11\x77\x58\x7f\x83'))
        data = self.encode(1.79e308)
        self.assertEqual(data, b('D\x7f\xef\xdc\xf1\x58\xad\xbb\x99'))

    def test_encode_too_huge_value(self):
        data = self.encode(1.79e308)
        self.assertEqual(data, b('D\x7f\xef\xdc\xf1\x58\xad\xbb\x99'))

    def test_encode_inf_value_as_null(self):
        self.assertEqual(self.encode(float('inf')), b('Z'))
        self.assertEqual(self.encode(float('-inf')), b('Z'))


class StringTestCase(Draft8TestCase):

    def test_decode_ascii(self):
        data = self.decode(b('s\x03foo'))
        self.assertEqual(data, 'foo')

    def test_encode_ascii(self):
        data = self.encode('foo')
        self.assertEqual(data, b('s\x03foo'))

    def test_decode_utf8(self):
        source = b('s\x0c\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82')
        data = self.decode(source)
        self.assertEqual(data, u('привет'))

    def test_encode_utf8(self):
        expected = b('s\x0c\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82')
        data = self.encode('привет')
        self.assertEqual(data, expected)

    def test_encode_unicode(self):
        expected = b('s\x0c\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82')
        data = self.encode(u('привет'))
        self.assertEqual(data, expected)


class ArrayTestCase(Draft8TestCase):

    def test_decode_array(self):
        data = self.decode(b('a\x03B\x01B\x02B\x03'))
        self.assertEqual(data, [1, 2, 3])

    def test_encode_array(self):
        data = self.encode([1, 2, 3])
        self.assertEqual(data, b('a\x03B\x01B\x02B\x03'))

    def test_encode_tuple(self):
        data = self.encode((1, 2, 3))
        self.assertEqual(data, b('a\x03B\x01B\x02B\x03'))

    def test_decode_large_array(self):
        data = self.decode(b('A\x00\x00\x04\x00') + b('B\x01') * 1024)
        self.assertEqual(data, list([1] * 1024))

    def test_encode_range(self):
        data = self.encode(xrange(4))
        self.assertEqual(data, b('a\xffB\x00B\x01B\x02B\x03E'))

    def test_encode_large_array(self):
        data = self.encode(list([1] * 1024))
        self.assertEqual(data, b('A\x00\x00\x04\x00') + b('B\x01') * 1024)

    def test_encode_set(self):
        data = self.encode(set(['foo', 'bar', 'baz', 'foo']))
        self.assertEqual(data, b('a\x03s\x03bazs\x03foos\x03bar'))

    def test_encode_frozenset(self):
        data = self.encode(frozenset(['foo', 'bar', 'baz', 'foo']))
        self.assertEqual(data, b('a\x03s\x03bazs\x03foos\x03bar'))

    def test_fail_decode_if_eos_marker_occurres_in_sized_array(self):
        data = b('a\x03B\x01B\x02EB\x03')
        self.assertRaises(ValueError, self.decode, data)

    def test_should_skip_noop_markers_in_sized_array(self):
        data = self.decode(b('a\x03B\x01B\x02NB\x03N'))
        self.assertEqual(data, [1, 2, 3])


class StreamTestCase(Draft8TestCase):

    def test_decode_unsized_array(self):
        data = self.decode(b('a\xffB\x01B\x02B\x03E'))
        self.assertTrue(isinstance(data, GeneratorType))
        self.assertEqual(list(data), [1, 2, 3])

    def test_encode_generator(self):
        data = self.encode((i for i in range(7)))
        self.assertEqual(data, b('a\xffB\x00B\x01B\x02B\x03B\x04B\x05B\x06E'))

    def test_decode_unsized_object(self):
        data = self.decode(b('o\xffs\x03foos\x03bars\x03bars\x03bazE'))
        self.assertTrue(isinstance(data, GeneratorType))
        self.assertEqual(dict(data), {'foo': 'bar', 'bar': 'baz'})

    def test_decode_unsized_array_with_noops(self):
        data = self.decode(b('a\xffNB\x01NNNB\x02NNNNNNNNNNNNNB\x03E'))
        self.assertTrue(isinstance(data, GeneratorType))
        self.assertEqual(list(data), [1, 2, 3])

    def test_decode_nested_unsized_values(self):
        data = self.decode(b('a\xffa\xffB\x2aEo\xffs\x03fooB\x2aEE'))
        self.assertTrue(isinstance(data, GeneratorType))
        item = data.next()
        self.assertTrue(isinstance(item, list))
        self.assertEqual(item, [42])
        item = data.next()
        self.assertTrue(isinstance(item, list))
        self.assertEqual(item, [(b('foo'), 42)])

    def test_decode_nested_unsized_values(self):
        data = self.decode(b('a\xffa\xffB\x2aEo\xffs\x03fooB\x2aEE'))
        result = list(data)
        self.assertEqual(result, [[42], [('foo', 42)]])

    def test_encode_xrange(self):
        data = self.encode(xrange(4))
        self.assertEqual(data, b('a\xffB\x00B\x01B\x02B\x03E'))

    def test_encode_dict_iterkeys(self):
        data = {'foo': 0, 'bar': 1, 'baz': 2}
        data = self.encode(getattr(data, 'iterkeys', data.keys)())
        self.assertEqual(data, b('a\xffs\x03bazs\x03foos\x03barE'))

    def test_encode_dict_itervalues(self):
        data = {'foo': 0, 'bar': 1, 'baz': 2}
        data = self.encode(getattr(data, 'itervalues', data.values)())
        self.assertEqual(data, b('a\xffB\x02B\x00B\x01E'))

    def test_encode_dict_iteritems(self):
        data = {'foo': 0, 'bar': 1, 'baz': 2}
        data = self.encode(getattr(data, 'iteritems', data.items)())
        self.assertEqual(
            data,
            b('o\xffs\x03bazB\x02s\x03fooB\x00s\x03barB\x01E')
        )

    def test_fail_decode_on_early_array_end(self):
        self.assertRaises(ValueError, list, self.decode(b('a\xff')))

    def test_fail_decode_on_early_object_end(self):
        self.assertRaises(ValueError, list, self.decode(b('o\xff')))

    def test_fail_decode_on_early_eos(self):
        data = self.decode(b('o\xffs\x03fooE'))
        self.assertRaises(ValueError, list, data)

    def test_fail_decode_object_with_nonstring_key(self):
        data = self.decode(b('o\xffB\x03s\x03fooE'))
        self.assertRaises(ValueError, list, data)

    def test_allow_emit_noop_for_arrays(self):
        data = self.decode(b('a\xffB\x00NB\x01NB\x02NB\x03NB\x04E'),
                                   allow_noop=True)
        N = simpleubjson.NOOP
        self.assertEqual(list(data), [0, N, 1, N, 2, N, 3, N, 4])

    def test_allow_emit_noop_for_objects(self):
        data = self.decode(b('o\xffNs\x03fooNs\x03barNE'),
                                   allow_noop=True)
        self.assertTrue(isinstance(data, GeneratorType))
        data = list(data)
        N = simpleubjson.NOOP
        self.assertEqual(data, [(N, N), ('foo', 'bar'), (N, N)])
        self.assertEqual(dict(data), {'foo': 'bar', N: N})

        data = self.decode(b('a\xffB\x00NB\x01NB\x02NB\x03NB\x04E'),
                                   allow_noop=True)
        N = simpleubjson.NOOP
        self.assertEqual(list(data), [0, N, 1, N, 2, N, 3, N, 4])


class ObjectTestCase(Draft8TestCase):

    def test_decode_object(self):
        data = self.decode(b('o\x02s\x03foos\x03bars\x03bars\x03baz'))
        self.assertEqual(data, {'foo': 'bar', 'bar': 'baz'})

    def test_encode_object(self):
        data = self.encode({'foo': 'bar', 'bar': 'baz'})
        self.assertEqual(data, b('o\x02s\x03foos\x03bars\x03bars\x03baz'))

    def test_decode_object_with_nested_unsized_objects(self):
        source = b('o\x02s\x03bara\xffB\x2aEs\x03bazo\xffNNNs\x03fooB\x2aE')
        data = self.decode(source)
        self.assertEqual(data, {'baz': [('foo', 42)], 'bar': [42]})

    def test_fail_decode_if_eos_marker_occurres_in_sized_object(self):
        data = b('o\x02s\x03foos\x03bars\x03barEs\x03baz')
        self.assertRaises(ValueError, self.decode, data)

    def test_should_skip_noop_markers_in_sized_object(self):
        data = self.decode(b('o\x02s\x03foos\x03barNNNs\x03bars\x03baz'))
        self.assertEqual(data, {'foo': 'bar', 'bar': 'baz'})

    def test_fail_decode_non_string_object_keys(self):
        self.assertRaises(ValueError,
                          self.decode,
                          b('o\x01B\x03s\x03bar'))

    def test_fail_decode_on_early_end(self):
        self.assertRaises(ValueError, self.decode, b('o\x01'))


if __name__ == '__main__':
    unittest.main()

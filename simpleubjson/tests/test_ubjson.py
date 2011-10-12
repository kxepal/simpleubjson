# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import unittest
import simpleubjson
from StringIO import StringIO
from types import GeneratorType

class DecoderTestCase(unittest.TestCase):

    def test_skip_head_noops(self):
        data = simpleubjson.decode('NNNNNNNNNNNNNZ')
        self.assertTrue(data is None)

    def test_skip_trailing_data(self):
        data = simpleubjson.decode('Zfoobarbaz')
        self.assertTrue(data is None)

    def test_no_data(self):
        self.assertRaises(ValueError, simpleubjson.decode, '')

    def test_fail_on_unknown_marker(self):
        self.assertRaises(ValueError, simpleubjson.decode, 'Я')


class EncoderTestCase(unittest.TestCase):

    def test_fail_if_no_handler_matches(self):
        self.assertRaises(TypeError, simpleubjson.encode, object())

    def test_write_encoded_data_to_stream(self):
        stream = StringIO()
        simpleubjson.encode((i for i in range(5)), stream)
        self.assertEqual(stream.getvalue(), 'a\xffB\x00B\x01B\x02B\x03B\x04E')


class NullTestCase(unittest.TestCase):

    def test_decode(self):
        data = simpleubjson.decode('Z')
        self.assertTrue(data is None)

    def test_encode(self):
        data = simpleubjson.encode(None)
        self.assertEqual(data, 'Z')


class BooleanTestCase(unittest.TestCase):

    def test_false_decode(self):
        data = simpleubjson.decode('F')
        self.assertEqual(data, False)

    def test_false_encode(self):
        data = simpleubjson.encode(False)
        self.assertEqual(data, 'F')

    def test_true_decode(self):
        data = simpleubjson.decode('T')
        self.assertEqual(data, True)

    def test_true_encode(self):
        data = simpleubjson.encode(True)
        self.assertEqual(data, 'T')

class ByteTestCase(unittest.TestCase):

    def test_decode(self):
        data = simpleubjson.decode('B\x2a')
        self.assertEqual(data, 42)

    def test_encode(self):
        data = simpleubjson.encode(42)
        self.assertEqual(data, 'B\x2a')

    def test_decode_negative(self):
        data = simpleubjson.decode('B\xd6')
        self.assertEqual(data, -42)

    def test_encode_negative(self):
        data = simpleubjson.encode(-42)
        self.assertEqual(data, 'B\xd6')


class Integer16TestCase(unittest.TestCase):

    def test_decode(self):
        data = simpleubjson.decode('i\x30\x39')
        self.assertEqual(data, 12345)

    def test_encode(self):
        data = simpleubjson.encode(12345)
        self.assertEqual(data, 'i\x30\x39')

    def test_decode_negative(self):
        data = simpleubjson.decode('i\xa0\xff')
        self.assertEqual(data, -24321)

    def test_encode_negative(self):
        data = simpleubjson.encode(-24321)
        self.assertEqual(data, 'i\xa0\xff')


class Integer32TestCase(unittest.TestCase):

    def test_decode(self):
        data = simpleubjson.decode('I\x00\x01\x88\x94')
        self.assertEqual(data, 100500)

    def test_encode(self):
        data = simpleubjson.encode(100500)
        self.assertEqual(data, 'I\x00\x01\x88\x94')

    def test_decode_negative(self):
        data = simpleubjson.decode('I\xff\xfe\x77\x6c')
        self.assertEqual(data, -100500)

    def test_encode_negative(self):
        data = simpleubjson.encode(-100500)
        self.assertEqual(data, 'I\xff\xfe\x77\x6c')


class Integer64TestCase(unittest.TestCase):

    def test_decode(self):
        data = simpleubjson.decode('L\x7f\xff\xff\xff\xff\xff\xff\xff')
        self.assertEqual(data, 9223372036854775807L)

    def test_encode(self):
        data = simpleubjson.encode(9223372036854775807L)
        self.assertEqual(data, 'L\x7f\xff\xff\xff\xff\xff\xff\xff')

    def test_decode_negative(self):
        data = simpleubjson.decode('L\x80\x00\x00\x00\x00\x00\x00\x00')
        self.assertEqual(data, -9223372036854775808L)

    def test_encode_negative(self):
        data = simpleubjson.encode(-9223372036854775808L)
        self.assertEqual(data, 'L\x80\x00\x00\x00\x00\x00\x00\x00')


class HugeNumberTestCase(unittest.TestCase):

    def test_decode(self):
        data = simpleubjson.decode('h\x33314159265358979323846264338327950288419716939937510')
        self.assertEqual(data, '314159265358979323846264338327950288419716939937510')

    def test_encode(self):
        data = simpleubjson.encode(314159265358979323846264338327950288419716939937510)
        self.assertEqual(data, 'h\x33314159265358979323846264338327950288419716939937510')


class FloatTestCase(unittest.TestCase):

    def test_decode_float(self):
        data = simpleubjson.decode('d\x40\x48\xf5\xc3')
        self.assertEqual(round(data, 2), 3.14)

    def test_encode_float(self):
        data = simpleubjson.encode(3.14)
        self.assertEqual(data, 'd\x40\x48\xf5\xc3')

    def test_decode_double(self):
        data = simpleubjson.decode('D\x71\x8e\xde\x0b\x49\x13\x5b\x25')
        self.assertEqual(data, 100500e234)

    def test_encode_double(self):
        data = simpleubjson.encode(100500e234)
        self.assertEqual(data, 'D\x71\x8e\xde\x0b\x49\x13\x5b\x25')


class StringTestCase(unittest.TestCase):

    def test_decode_ascii(self):
        data = simpleubjson.decode('s\x03foo')
        self.assertEqual(data, 'foo')

    def test_encode_ascii(self):
        data = simpleubjson.encode('foo')
        self.assertEqual(data, 's\x03foo')

    def test_decode_utf8(self):
        data = simpleubjson.decode('s\x0c\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82')
        self.assertEqual(data, u'привет')

    def test_encode_utf8(self):
        data = simpleubjson.encode('привет')
        self.assertEqual(data, 's\x0c\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82')

    def test_encode_unicode(self):
        data = simpleubjson.encode(u'привет')
        self.assertEqual(data, 's\x0c\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82')


class ArrayTestCase(unittest.TestCase):

    def test_decode_array(self):
        data = simpleubjson.decode('a\x03B\x01B\x02B\x03')
        self.assertEqual(data, [1, 2, 3])

    def test_encode_array(self):
        data = simpleubjson.encode([1, 2, 3])
        self.assertEqual(data, 'a\x03B\x01B\x02B\x03')

    def test_encode_tuple(self):
        data = simpleubjson.encode((1, 2, 3))
        self.assertEqual(data, 'a\x03B\x01B\x02B\x03')

    def test_decode_large_array(self):
        data = simpleubjson.decode('A\x00\x00\x04\x00' + 'B\x01' * 1024)
        self.assertEqual(data, list([1] * 1024))

    def test_encode_large_array(self):
        data = simpleubjson.encode(list([1] * 1024))
        self.assertEqual(data, 'A\x00\x00\x04\x00' + 'B\x01' * 1024)

    def test_fail_decode_if_eos_marker_occurres_in_sized_array(self):
        self.assertRaises(ValueError, simpleubjson.decode, 'a\x03B\x01B\x02EB\x03')

    def test_fail_decode_if_noop_marker_occurres_in_sized_array(self):
        self.assertRaises(ValueError, simpleubjson.decode, 'a\x03B\x01B\x02NB\x03N')


class StreamTestCase(unittest.TestCase):

    def test_decode_unsized_array(self):
        data = simpleubjson.decode('a\xffB\x01B\x02B\x03E')
        self.assertTrue(isinstance(data, GeneratorType))
        self.assertEqual(list(data), [1, 2, 3])

    def test_encode_generator(self):
        data = simpleubjson.encode((i for i in range(7)))
        self.assertEqual(data, 'a\xffB\x00B\x01B\x02B\x03B\x04B\x05B\x06E')

    def test_decode_unsized_object(self):
        data = simpleubjson.decode('o\xffs\x03foos\x03bars\x03bars\x03bazE')
        self.assertTrue(isinstance(data, GeneratorType))
        self.assertEqual(dict(data), {'foo': 'bar', 'bar': 'baz'})

    def test_decode_unsized_array_with_noops(self):
        data = simpleubjson.decode('a\xffNB\x01NNNB\x02NNNNNNNNNNNNNB\x03E')
        self.assertTrue(isinstance(data, GeneratorType))
        self.assertEqual(list(data), [1, 2, 3])

    def test_decode_unsized_array_with_leading_noops(self):
        data = simpleubjson.decode('Na\xffE')
        self.assertTrue(isinstance(data, GeneratorType))
        self.assertEqual(list(data), [])

    def test_decode_nested_unsized_values(self):
        data = simpleubjson.decode('a\xffa\xffB\x2aEo\xffs\x03fooB\x2aEE')
        self.assertTrue(isinstance(data, GeneratorType))
        item = data.next()
        self.assertTrue(isinstance(item, list))
        self.assertEqual(item, [42])
        item = data.next()
        self.assertTrue(isinstance(item, list))
        self.assertEqual(item, [('foo', 42)])

    def test_fail_decode_on_early_array_end(self):
        self.assertRaises(ValueError, list, simpleubjson.decode('a\xff'))

    def test_fail_decode_on_early_object_end(self):
        self.assertRaises(ValueError, list, simpleubjson.decode('o\xff'))

    def test_fail_decode_on_early_eos(self):
        self.assertRaises(ValueError, list,
                          simpleubjson.decode('o\xff\s\x03fooE'))

    def test_fail_decode_object_with_nonstring_key(self):
        self.assertRaises(ValueError, list,
                          simpleubjson.decode('o\xff\B\x03\s\x03fooE'))

class ObjectTestCase(unittest.TestCase):

    def test_decode_object(self):
        data = simpleubjson.decode('o\x02s\x03foos\x03bars\x03bars\x03baz')
        self.assertEqual(data, {'foo': 'bar', 'bar': 'baz'})

    def test_encode_object(self):
        data = simpleubjson.encode({'foo': 'bar', 'bar': 'baz'})
        self.assertEqual(data, 'o\x02s\x03foos\x03bars\x03bars\x03baz')

    def test_decode_object_with_nested_unsized_objects(self):
        data = simpleubjson.decode('o\x02s\x03bara\xffB\x2aEs\x03bazo\xffNNNs\x03fooB\x2aE')
        self.assertEqual(data, {'baz': [('foo', 42)], 'bar': [42]})

    def test_fail_decode_if_eos_marker_occurres_in_sized_object(self):
        self.assertRaises(ValueError, simpleubjson.decode,
                          'o\x02s\x03foos\x03bars\x03barEs\x03baz')

    def test_fail_decode_if_noop_marker_occurres_in_sized_object(self):
        self.assertRaises(ValueError, simpleubjson.decode, 
                          'o\x02s\x03foos\x03barNNNs\x03barEs\x03baz')

    def test_fail_decode_non_string_object_keys(self):
        self.assertRaises(ValueError, simpleubjson.decode, 'o\x01B\x03s\x03bar')

    def test_fail_decode_on_early_end(self):
        self.assertRaises(ValueError, simpleubjson.decode, 'o\x01')


if __name__ == '__main__':
    unittest.main()

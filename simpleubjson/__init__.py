# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

#: Noop sentinel value
NOOP = type('NoOp', (object,), {'__slots__': ()})()
_EOS = type('EndOfStream', (object,), {'__slots__': ()})
#: EOS (end of stream) sentinel value. Draft-8 only.
EOS = _EOS()
EOS_A = type('EndOfArrayStream', (_EOS,), {'__slots__': ()})()
EOS_O = type('EndOfObjectStream', (_EOS,), {'__slots__': ()})()
del _EOS

from simpleubjson.common import streamify
from simpleubjson.draft8 import Draft8Decoder, Draft8Encoder
from simpleubjson.draft9 import Draft9Decoder, Draft9Encoder
from simpleubjson.tools.inspect import pprint

__all__ = ['decode', 'encode', 'pprint', 'NOOP', 'EOS']

_draft8_decoder = Draft8Decoder()
_draft8_encoder = Draft8Encoder()

_draft9_decoder = Draft9Decoder
_draft9_encoder = Draft9Encoder


def decode(data, allow_noop=False, spec='draft8'):
    """Decodes input stream of UBJSON data to Python object.

    :param data: `.read([size])`-able object or source string.
    :param allow_noop: Allow to emit :const:`~simpleubjson.NOOP` values for
                       unsized arrays and objects.
    :type allow_noop: bool
    :param spec: UBJSON specification. Supported Draft-8 and Draft-9
                 specifications by ``draft-8`` or ``draft-9`` keys.
    :type spec: str

    :return: Decoded Python object. See mapping table below.

    :raises:
        ValueError if:
            * Nothing to decode: empty data source.
            * Unsupported marker: probably it's invalid.
            * Unexpected marker: `noop` value or EOS shouldn't occurs in sized
              arrays or objects.
            * Object key is not string type.
    """

    if spec.lower() in ['draft8', 'draft-8']:
        stream = streamify(data, _draft8_decoder.markers, allow_noop)
        return _draft8_decoder(stream)
    elif spec.lower() in ['draft9', 'draft-9']:
        return _draft9_decoder(data, allow_noop).decode_next()
    else:
        raise ValueError('Unknown or unsupported specification %s' % spec)


def encode(data, output=None, default=None, spec='draft-8'):
    """Encodes Python object to Universal Binary JSON data.

    :param data: Python object.
    :param output: `.write([data])`-able object. If omitted result would be
                   returned instead of written into.
    :param default: Callable object that would be used if there is no handlers
                    matched for Python data type.
                    Takes encodable value as single argument and must return
                    valid UBJSON encodable value.
    :param spec: UBJSON specification. Supported Draft-8 and Draft-9
                 specifications by ``draft-8`` or ``draft-9`` keys.
    :type spec: str

    :return: Encoded Python object. See mapping table below.
             If `output` param is specified, all data would be written into it
             by chunks and None will be returned.

    :raises:
        * TypeError if no handlers specified for passed value type.
        * ValueError if unable to pack Python value to binary form.
    """
    if spec.lower() in ['draft8', 'draft-8']:
        return _draft8_encoder(data)
    elif spec.lower() in ['draft9', 'draft-9']:
        res = _draft9_encoder(default).encode_next(data)
        if output:
            output.write(res)
        else:
            return res
    else:
        raise ValueError('Unknown or unsupported specification %s' % spec)


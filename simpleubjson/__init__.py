# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

#: Noop sentinel value
NOOP = type('NoopType', (object,), {'__slots__': ()})()
#: EOS (end of stream) sentinel value
EOS = type('EndOfStreamType', (object,), {'__slots__': ()})()

from simpleubjson.decoder import UBJSONDecoder, streamify, MARKERS
from simpleubjson.encoder import UBJSONEncoder
from simpleubjson.tools.inspect import pprint

_default_decoder = UBJSONDecoder()
_default_encoder = UBJSONEncoder()

def decode(data, default=None, allow_noop=False):
    """Decodes input stream of UBJSON data to Python object.

    :param data: `.read([size])`-able object or source string.
    :param default: Callable object that would be used if there is no handlers
                    matched for occurred marker.
                    Takes two arguments: data stream and marker.
                    It should return tuple of three values: marker, size and
                    result value.
    :param allow_noop: Allow to emit :const:`~simpleubjson.NOOP` values for
                       unsized arrays and objects.
    :type allow_noop: bool

    :return: Decoded Python object. See mapping table below.

    :raises:
        ValueError if:
            * Nothing to decode: empty data source.
            * Unsupported marker: probably it's invalid.
            * Unexpected marker: `noop` value or EOS shouldn't occurs in sized
              arrays or objects.
            * Object key is not string type.
    """
    stream = streamify(data, MARKERS, default, allow_noop)
    return _default_decoder.decode(stream)

def encode(data, output=None, default=None, handlers=None):
    """Encodes Python object to Universal Binary JSON data.

    :param data: Python object.
    :param output: `.write([data])`-able object. If omitted result would be
                   returned instead of written into.
    :param default: Callable object that would be used if there is no handlers
                    matched for Python data type.
                    Takes 2 arguments of encoder instance and encodable value.
    :param handlers: Custom set of handlers where key is Python type and
                     value is any callable that takes encoder instance and
                     encodable value.

    :return: Encoded Python object. See mapping table below.
             If `output` param is specified, all data would be written into it
             by chunks and None will be returned.

    :raises:
        * TypeError if no handlers specified for passed value type.
        * ValueError if unable to pack Python value to binary form.
    """
    if default is None and handlers is None:
        return _default_encoder.encode(data, output)
    kwargs = {
        'default': default,
        'handlers': handlers
    }
    return UBJSONEncoder(**kwargs).encode(data, output)

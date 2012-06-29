# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import sys
import simpleubjson.decoder as decoder


def pprint(data, output=sys.stdout, allow_noop=True,
           indent='    ', max_level=None, spec='draft-8'):
    """Pretty prints ubjson data using the handy [ ]-notation to represent it in
    readable form. Example::

        [o] [2]
            [s] [2] [id]
            [I] [1234567890]
            [s] [4] [name]
            [s] [3] [bob]

    :param data: `.read([size])`-able object or source string with ubjson data.
    :param output: `.write([data])`-able object.
    :param allow_noop: Allow emit :const:`~simpleubjson.NOOP` or not.
    :param indent: Indention string.
    :param max_level: Max level of inspection nested containers. By default
                      there is no limit, but you may hit system recursion limit.
    :param spec: UBJSON specification. Supported Draft-8 and Draft-9
                 specifications by ``draft-8`` or ``draft-9`` keys.
    :type spec: str
    """
    def maybe_write(data, level):
        if max_level is None or level <= max_level:
            output.write('%s' % (indent * level))
            output.write(data)
    def inspect(stream, level, size):
        for type, length, value in stream:
            if length is None and value is None:
                if spec == 'draft8':
                    if type == 'E' and size == 255:
                        level -= 1
                    maybe_write('[%s]\n' % (type,), level)
                    return
                elif spec == 'draft9':
                    if type in 'AO':
                        maybe_write('[%s]\n' % (type,), level)
                        return inspect(stream, level + 1, 255)
                    elif type == 'E':
                        level -= 1
                        maybe_write('[%s]\n' % (type,), level)
                    else:
                        maybe_write('[%s]\n' % (type,), level)
            elif length is not None and value is None:
                maybe_write('[%s] [%s]\n' % (type, length), level)
                if type in 'oO':
                    length = length == 255 and length or length * 2
                    inspect(stream, level + 1, length)
                else:
                    inspect(stream, level + 1, length)
            elif length is None and value is not None:
                value = decode_tlv(None, type, length, value)
                maybe_write('[%s] [%s]\n' % (type, value), level)
            else:
                value = decode_tlv(None, type, length, value)
                maybe_write('[%s] [%s] [%s]\n' % (type, length, value), level)
            if size != 255:
                size -= 1
                if not size:
                    return
    if spec.lower() in ['draft8', 'draft-8']:
        spec = 'draft8'
        stream = decoder.streamify(data, decoder.MARKERS_DRAFT_8, allow_noop=allow_noop)
        decode_tlv = decoder.decode_tlv_draft_8
    elif spec.lower() in ['draft9', 'draft-9']:
        spec = 'draft9'
        stream = decoder.streamify(data, decoder.MARKERS_DRAFT_9, allow_noop=allow_noop)
        decode_tlv = decoder.decode_tlv_draft_9
    else:
        raise ValueError('Unknown or unsupported specification %s' % spec)
    inspect(stream, 0, 255)
    output.flush()

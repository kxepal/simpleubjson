# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import sys
from simpleubjson.decoder import streamify, MARKERS_DRAFT_8, decode_tlv_draft_8


def pprint(data, output=sys.stdout, allow_noop=True,
           indent='    ', max_level=None):
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
    """
    def maybe_write(data, level):
        if max_level is None or level <= max_level:
            output.write('%s' % (indent * level))
            output.write(data)
    def inspect(stream, level, size):
        for type, length, value in stream:
            if length is None and value is None:
                if type == 'E' and size == 255:
                    level -= 1
                maybe_write('[%s]\n' % (type,), level)
                return
            elif length is not None and value is None:
                maybe_write('[%s] [%s]\n' % (type, length), level)
                if type in 'oO':
                    length = length == 255 and length or length * 2
                    inspect(stream, level + 1, length)
                else:
                    inspect(stream, level + 1, length)
            elif length is None and value is not None:
                value = decode_tlv_draft_8(None, type, length, value)
                maybe_write('[%s] [%s]\n' % (type, value), level)
            else:
                value = decode_tlv_draft_8(None, type, length, value)
                maybe_write('[%s] [%s] [%s]\n' % (type, length, value), level)
            if size != 255:
                size -= 1
                if not size:
                    return
    stream = streamify(data, MARKERS_DRAFT_8, allow_noop)
    inspect(stream, 0, 255)
    output.flush()

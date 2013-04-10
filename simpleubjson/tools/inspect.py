# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import sys
import simpleubjson
from simpleubjson.draft8 import Draft8Decoder
from simpleubjson.draft9 import Draft9Decoder


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
            output.flush()

    def inspect_draft8(stream, level, container_size):
        for marker, tlv in stream:
            tag, length, value = tlv
            # standalone markers
            if length is None and value is None:
                if tag == 'E':
                    maybe_write('[%s]\n' % (tag,), level - 1)
                    return
                else:
                    maybe_write('[%s]\n' % (tag,), level)

            # sized containers
            elif length is not None and value is None:
                maybe_write('[%s] [%s]\n' % (tag, length), level)
                if tag in 'oO':
                    length = length == 255 and length or length * 2
                inspect_draft8(stream, level + 1, length)

            # plane values
            elif length is None and value is not None:
                value = marker.decode(None, stream, tlv)
                maybe_write('[%s] [%s]\n' % (tag, value), level)

            # sized values
            else:
                value = marker.decode(None, stream, tlv)
                maybe_write('[%s] [%s] [%s]\n' % (tag, length, value), level)

            if container_size != 255:
                container_size -= 1
                if not container_size:
                    return

    def inspect_draft9(stream, level, *args):
        for marker, tlv in stream:
            tag, length, value = tlv
            # standalone markers
            if length is None and value is None:
                if tag in ']}':
                    level -= 1
                maybe_write('[%s]\n' % (tag,), level)
                if tag in '{[':
                    level += 1

            # plane values
            elif length is None and value is not None:
                value = marker.decode(None, stream, tlv)
                maybe_write('[%s] [%s]\n' % (tag, value), level)

            # sized values
            else:
                value = marker.decode(None, stream, tlv)
                pattern = '[%s] [%s] [%s] [%s]\n'
                # very dirty hack to show size as marker and value
                _stream = streamify(simpleubjson.encode(length, spec=spec), markers)
                for marker, stlv in _stream:
                    args = tuple([tag, stlv[0], stlv[2], value])
                maybe_write(pattern % args, level)

    if spec.lower() in ['draft8', 'draft-8']:
        markers = Draft8Decoder().markers
        inspect = inspect_draft8
    elif spec.lower() in ['draft9', 'draft-9']:
        markers = Draft9Decoder().markers
        inspect = inspect_draft9
    else:
        raise ValueError('Unknown or unsupported specification %s' % spec)

    inspect(streamify(data, markers=markers, allow_noop=allow_noop), 0, 255)

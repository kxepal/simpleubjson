# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import sys
from functools import partial
import simpleubjson
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
            output.flush()

    def inspect_draft8(stream, level, container_size):
        for marker, size, value in stream:
            # standalone markers
            if size is None and value is None:
                maybe_write('[%s]\n' % (marker,), level)
                if marker == 'E':
                    return

            # sized containers
            elif size is not None and value is None:
                maybe_write('[%s] [%s]\n' % (marker, size), level)
                if marker in 'oO':
                    size = size == 255 and size or size * 2
                inspect_draft8(stream, level + 1, size)

            # plane values
            elif size is None and value is not None:
                value = decode_tlv(None, marker, size, value)
                maybe_write('[%s] [%s]\n' % (marker, value), level)

            # sized values
            else:
                value = decode_tlv(None, marker, size, value)
                maybe_write('[%s] [%s] [%s]\n' % (marker, size, value), level)

            if container_size != 255:
                container_size -= 1
                if not container_size:
                    return

    def inspect_draft9(stream, level, *args):
        for marker, size, value in stream:
            # standalone markers
            if size is None and value is None:
                if marker == 'E':
                    level -= 1
                maybe_write('[%s]\n' % (marker,), level)
                if marker in 'AO':
                    level += 1

            # plane values
            elif size is None and value is not None:
                value = decode_tlv(None, marker, size, value)
                maybe_write('[%s] [%s]\n' % (marker, value), level)

            # sized values
            else:
                value = decode_tlv(None, marker, size, value)
                pattern = '[%s] [%s] [%s] [%s]\n'
                # very dirty hack to show size as marker and value
                _stream = streamify(simpleubjson.encode(size, spec=spec))
                for smarker, _, size in _stream:
                    args = (marker, smarker, size, value)
                maybe_write(pattern % args, level)

    if spec.lower() in ['draft8', 'draft-8']:
        streamify = partial(decoder.streamify, markers=decoder.MARKERS_DRAFT_8)
        decode_tlv = decoder.decode_tlv_draft_8
        inspect = inspect_draft8
    elif spec.lower() in ['draft9', 'draft-9']:
        streamify = partial(decoder.streamify, markers=decoder.MARKERS_DRAFT_9)
        decode_tlv = decoder.decode_tlv_draft_9
        inspect = inspect_draft9
    else:
        raise ValueError('Unknown or unsupported specification %s' % spec)

    inspect(streamify(data, allow_noop=allow_noop), 0, 255)

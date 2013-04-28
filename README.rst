Simple UBJSON in Python
=======================

`UBJSON`_ is the universally compatible format specification for binary `JSON`_.
It's pretty and simple data format and `simpleubjson`_ aims to be also the same.

.. code-block:: python

  >>> import simpleubjson
  >>> ubjdata = simpleubjson.encode({'hello': 'world', 'тест': [1, 2, 3]})
  >>> ubjdata
  b'o\x02s\x05hellos\x05worlds\x08\xd1\x82\xd0\xb5\xd1\x81\xd1\x82a\x03B\x01B\x02B\x03'

:func:`simpleubjson.encode` function transforms Python objects into UBJSON
`binary` string data. To decode it back to Python objects use
:func:`simpleubjson.decode` function:

.. code-block:: python

  >>> simpleubjson.decode(ubjdata)
  {'hello': 'world', 'тест': [1, 2, 3]}

Moreover, you may also introspect UBJSON data via :func:`simpleubjson.pprint`
function:

.. code-block:: python

  >>> simpleubjson.pprint(ubjdata)
  [o] [2]
    [s] [5] [hello]
    [s] [5] [world]
    [s] [8] [тест]
    [a] [3]
        [B] [1]
        [B] [2]
        [B] [3]

This representation is a bit more human friendly than traditional hexview and
designed specially for UBJSON format.

Currently `simpleubjson` follows Draft-8 specification by default, but you
already may use Draft-9 version by passing ``spec="draft-9"`` argument for
:func:`~simpleubjson.decode`, :func:`~simpleubjson.encode` and
:func:`~simpleubjson.pprint` functions. Please check `breaking changes`_ before
switching to it.

.. _UBJSON: http://ubjson.org/
.. _JSON: http://json.org/
.. _simpleubjson: http://code.google.com/p/simpleubjson/
.. _breaking changes: http://ubjson.org/#latest

Simple UBJSON in Python
=======================

`UBJSON`_ is the universally compatible format specification for binary `JSON`_.
It's pretty and simple data format and `simpleubjson`_ aims to be also the same.

.. code-block:: python

  >>> import simpleubjson
  >>> ubjdata = simpleubjson.encode({'hello': 'world', 'тест': [1, 2, 3]})
  >>> ubjdata
  b'{Si\x08\xd1\x82\xd0\xb5\xd1\x81\xd1\x82[i\x01i\x02i\x03]SU\x05helloSi\x05world}'

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
  [{]
      [S] [i] [5] [hello]
      [S] [i] [5] [world]
      [S] [i] [8] [тест]
      [[]
          [i] [1]
          [i] [2]
          [i] [3]
      []]
  [}]

This representation is a bit more human friendly than traditional hexview and
designed specially for UBJSON format.

Currently `simpleubjson` follows Draft-9 specification by default, but you
may change specification version by passing ``spec="draft-N"`` argument for
:func:`~simpleubjson.decode`, :func:`~simpleubjson.encode` and
:func:`~simpleubjson.pprint` functions.

.. _UBJSON: http://ubjson.org/
.. _JSON: http://json.org/
.. _simpleubjson: http://code.google.com/p/simpleubjson/

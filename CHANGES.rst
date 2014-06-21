0.7.0 (2014-06-21)
------------------

- Add support of UINT8 type for Draft-9 spec;
- Add support of CHAR type for Draft-9 spec;
- Optimize strings encoding with new types;
- Switch to BSD 2 clause license;

0.6.1 (2013-04-29)
------------------

- Fix compatibility with Python 3.x;
- Force binary strings have utf-8 charset on encoding;
- Improve UBJSON decoding performance;

0.6.0 (2013-04-10)
------------------

- Project refactoring and code cleanup;
- Raise overall performance for 100-400% times depending on test case;
- Update Draft-9 support to RC state: handle new containers markers;

0.5.0 (2012-07-07)
------------------

- Fix encoding of unsized objects;
- Fix pprinting containers with NoOp markers;
- Fix markers of integers values for Draft-9 spec;

0.4.0 (2012-06-29)
------------------

- Encode `set` and `frozenset` types;
- Experimental implementation of Draft-9 specification;
- Fix encoding of `dict` iterators;
- Support Python 3.x;

0.3.0 (2012-03-03)
------------------

- Add `simpleubjson.pprint` function to dump UBJSON data using ``[ ]``-notation;
- Allow decode standalone NoOp values;
- Encode `inf` and `-inf` values as `null`;
- Remove support of custom markers and handlers;
- Wrap `HUGE` values with `Decimal` class and encode `Decimal` instances back
  to `HUGE`;

0.2.0 (2011-11-30)
------------------

- Allow decoder produce NoOp values;
- Allow to specify custom decoding/encoding handlers;
- Fix float/double values handling;

0.1.0 (2011-10-13)
------------------

- First version with support Draft-8 specification.

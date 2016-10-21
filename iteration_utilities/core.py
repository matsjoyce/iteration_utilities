"""
API: Chainable iteration_utilities
----------------------------------
"""
# Built-ins
from __future__ import absolute_import, division, print_function
from collections import Counter, OrderedDict
from functools import reduce
from heapq import nlargest, nsmallest
from itertools import (chain, combinations, combinations_with_replacement,
                       compress, count, cycle,
                       dropwhile,
                       islice,
                       permutations, product,
                       repeat,
                       starmap,
                       takewhile)
from math import fsum

# This module
from iteration_utilities import PY2, PY34, _default
# - generators
from iteration_utilities import (accumulate, append, applyfunc,
                                 clamp, cutout,
                                 deepflatten,
                                 flatten,
                                 grouper,
                                 intersperse, itersubclasses, iter_except,
                                 ncycles,
                                 pad, powerset, prepend,
                                 repeatfunc, replicate,
                                 split, successive,
                                 tabulate, tail,
                                 unique_everseen, unique_justseen, unpack)
# - folds
from iteration_utilities import (all_distinct, all_equal, argmax, argmin,
                                 count_items, first, groupedby, last,
                                 minmax, nth, one, partition, second,
                                 take, third)
# - multiple_iterables
from iteration_utilities import merge, roundrobin
# - helper
from iteration_utilities import all_isinstance, any_isinstance


# Conditional imports
if PY2:
    from itertools import (ifilter as filter,
                           imap as map,
                           ifilterfalse as filterfalse,
                           izip as zip,
                           izip_longest as zip_longest)
else:
    from itertools import filterfalse, zip_longest

if PY34:
    import statistics


__all__ = ['Iterable', 'InfiniteIterable', 'ManyIterables']


def filterkwargs(**kwargs):
    return {k: kwargs[k] for k in kwargs if kwargs[k] is not _default}


class _Base(object):
    """Base class for method definitions that are shared by `Iterable` and
    `InfiniteIterable`.
    """
    __slots__ = ('_iterable')

    def __init__(self, iterable):
        self._iterable = iterable

    def __iter__(self):
        return iter(self._iterable)

    def __repr__(self):
        return '<{0.__class__.__name__}: {0._iterable!r}>'.format(self)

    def _call(self, *args, **kwargs):
        fn = args[0]
        pos = args[1]
        args = list(islice(args, 2, None))
        args.insert(pos, self)
        kwargs = filterkwargs(**kwargs)
        return self.__class__(fn(*args, **kwargs))

    def _call_finite(self, *args, **kwargs):
        res = self._call(*args, **kwargs)
        if isinstance(res, Iterable):
            return res
        return Iterable(self._call(*args, **kwargs)._iterable)

    def _call_infinite(self, *args, **kwargs):
        res = self._call(*args, **kwargs)
        if isinstance(res, InfiniteIterable):
            # There is no use-case to wrap an already infinite iterable with
            # something that newly creates an infinite iterable.
            # For example cycle(count()) makes no sense because we never end
            # with count so cycle never triggers.
            # That may change but I found no useful combination so there is
            # this Exception.
            raise TypeError('impossible to wrap an infinite iterable with '
                            'another infinite iterable.')
        return InfiniteIterable(self._call(*args, **kwargs)._iterable)

    @staticmethod
    def from_count(start=_default, step=_default):
        """See :py:func:`itertools.count`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable.from_count().islice(10).as_list()
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> Iterable.from_count(4, 3).islice(10).as_list()
        [4, 7, 10, 13, 16, 19, 22, 25, 28, 31]

        >>> Iterable.from_count(start=4, step=3).islice(10).as_list()
        [4, 7, 10, 13, 16, 19, 22, 25, 28, 31]

        .. warning::
           This returns an `InfiniteIterable`.
        """
        return InfiniteIterable(count(**filterkwargs(start=start, step=step)))

    @staticmethod
    def from_repeat(object, times=_default):
        """See :py:func:`itertools.repeat`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable.from_repeat(5).islice(10).as_list()
        [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]

        >>> Iterable.from_repeat(5, 5).as_list()
        [5, 5, 5, 5, 5]

        >>> Iterable.from_repeat(object=5, times=5).as_list()
        [5, 5, 5, 5, 5]

        .. warning::
           This returns an `InfiniteIterable` if `times` is not given.
        """
        if times is not _default:
            return Iterable(repeat(object, times))
        else:
            return InfiniteIterable(repeat(object))

    @staticmethod
    def from_itersubclasses(object):
        """See
        :py:func:`~iteration_utilities._recipes._additional.itersubclasses`.

        Examples
        --------
        >>> from iteration_utilities import Iterable

        >>> class A(object): pass
        >>> class B(A): pass
        >>> class C(A): pass
        >>> class D(C): pass

        >>> Iterable.from_itersubclasses(A).as_list()
        [<class 'iteration_utilities.core.B'>, \
<class 'iteration_utilities.core.C'>, \
<class 'iteration_utilities.core.D'>]

        >>> Iterable.from_itersubclasses(C).as_list()
        [<class 'iteration_utilities.core.D'>]
        """
        return Iterable(itersubclasses(object))

    @staticmethod
    def from_applyfunc(func, initial):
        """See :py:func:`~iteration_utilities.applyfunc`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable.from_applyfunc(lambda x: x*2, 10).islice(5).as_list()
        [20, 40, 80, 160, 320]

        >>> Iterable.from_applyfunc(func=lambda x: x*2,
        ...                         initial=10).islice(5).as_list()
        [20, 40, 80, 160, 320]

        .. warning::
           This returns an `InfiniteIterable`.
        """
        return InfiniteIterable(applyfunc(func=func, initial=initial))

    @staticmethod
    def from_iterfunc_sentinel(func, sentinel):
        """See :py:func:`python:iter`.

        Examples
        --------
        >>> from iteration_utilities import Iterable

        >>> class Func:
        ...     def __init__(self):
        ...         self.val = 0
        ...     def __call__(self):
        ...         self.val += 1
        ...         return 4 if self.val < 8 else 10

        >>> Iterable.from_iterfunc_sentinel(Func(), 10).as_list()
        [4, 4, 4, 4, 4, 4, 4]
        """
        # TODO: Update example to something useful
        return Iterable(iter(func, sentinel))

    @staticmethod
    def from_iterfunc_exception(func, exception, first=_default):
        """See :py:func:`~iteration_utilities.iter_except`.

        Examples
        --------
        >>> from iteration_utilities import Iterable

        >>> class Func:
        ...     def __init__(self):
        ...         self.val = 0
        ...     def __call__(self):
        ...         self.val += 1
        ...         if self.val < 8:
        ...             return 3
        ...         raise ValueError()

        >>> Iterable.from_iterfunc_exception(Func(), ValueError).as_list()
        [3, 3, 3, 3, 3, 3, 3]
        """
        return Iterable(iter_except(func, exception,
                                    **filterkwargs(first=first)))

    @staticmethod
    def from_repeatfunc(func, *args, **times):
        """See :py:func:`~iteration_utilities._recipes._core.repeatfunc`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable.from_repeatfunc(int).islice(10).as_list()
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        >>> Iterable.from_repeatfunc(int, times=10).as_list()
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        >>> import random  # doctest: +SKIP
        >>> # Something more useful: Creating 10 random integer
        >>> Iterable.from_repeatfunc(random.randint, 0, 5,
        ...                          times=10).as_list()  # doctest: +SKIP
        [1, 3, 1, 3, 5, 2, 4, 1, 0, 1]

        .. warning::
           This returns an `InfiniteIterable` if `times` is not given.
        """
        if times:
            return Iterable(repeatfunc(func, *args, **times))
        else:
            return InfiniteIterable(repeatfunc(func, *args))

    @staticmethod
    def from_tabulate(func, start=_default):
        """See :py:func:`~iteration_utilities._recipes._core.tabulate`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> import operator
        >>> Iterable.from_tabulate(operator.neg).islice(8).as_list()
        [0, -1, -2, -3, -4, -5, -6, -7]

        >>> from math import gamma
        >>> Iterable.from_tabulate(gamma, 1).islice(8).as_tuple()
        (1.0, 1.0, 2.0, 6.0, 24.0, 120.0, 720.0, 5040.0)

        >>> Iterable.from_tabulate(func=gamma, start=2).islice(7).as_tuple()
        (1.0, 2.0, 6.0, 24.0, 120.0, 720.0, 5040.0)

        .. warning::
           This returns an `InfiniteIterable`.
        """
        return InfiniteIterable(tabulate(func, **filterkwargs(start=start)))

    def accumulate(self, func=_default, start=_default):
        """See :py:func:`~iteration_utilities.accumulate`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).accumulate().as_list()
        [1, 3, 6, 10, 15, 21, 28, 36, 45]

        >>> from operator import mul
        >>> Iterable(range(1, 10)).accumulate(mul, 2).as_list()
        [2, 4, 12, 48, 240, 1440, 10080, 80640, 725760]

        >>> Iterable(range(1, 10)).accumulate(func=mul, start=3).as_list()
        [3, 6, 18, 72, 360, 2160, 15120, 120960, 1088640]
        """
        return self._call(accumulate, 0, func=func, start=start)

    def append(self, element):
        """See :py:func:`~iteration_utilities._recipes._additional.append`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).append(10).as_list()
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        >>> Iterable(range(1, 10)).append(element=10).as_list()
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        """
        return self._call(append, 1, element)

    def clamp(self, low=_default, high=_default, inclusive=_default):
        """See :py:func:`~iteration_utilities.clamp`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).clamp(2, 7, True).as_list()
        [3, 4, 5, 6]

        >>> Iterable(range(10)).clamp(low=2, high=7, inclusive=True).as_list()
        [3, 4, 5, 6]
        """
        return self._call(clamp, 0, low=low, high=high, inclusive=inclusive)

    def combinations(self, r):
        """See :py:func:`itertools.combinations`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 4)).combinations(2).as_list()
        [(1, 2), (1, 3), (2, 3)]

        >>> Iterable(range(1, 4)).combinations(r=2).as_list()
        [(1, 2), (1, 3), (2, 3)]
        """
        return self._call(combinations, 0, r=r)

    def combinations_with_replacement(self, r):
        """See :py:func:`itertools.combinations_with_replacement`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 4)).combinations_with_replacement(2).as_list()
        [(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)]

        >>> Iterable(range(1, 4)).combinations_with_replacement(r=2).as_list()
        [(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)]
        """
        return self._call(combinations_with_replacement, 0, r=r)

    def compress(self, selectors):
        """See :py:func:`itertools.compress`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> sel = [0, 1, 0, 1, 0, 1, 1, 1, 0]
        >>> Iterable(range(1, 10)).compress(sel).as_list()
        [2, 4, 6, 7, 8]

        >>> Iterable(range(1, 10)).compress(selectors=sel).as_list()
        [2, 4, 6, 7, 8]
        """
        return self._call(compress, 0, selectors=selectors)

    def cutout(self, start, stop):
        """See :py:func:`iteration_utilities._recipes._additional.cutout`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).cutout(2, 5).as_list()
        [0, 1, 5, 6, 7, 8, 9]

        >>> Iterable(range(10)).cutout(start=2, stop=5).as_list()
        [0, 1, 5, 6, 7, 8, 9]
        """
        return self._call(cutout, 0, start=start, stop=stop)

    def cycle(self):
        """See :py:func:`itertools.cycle`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> it = Iterable([1, 2]).cycle()
        >>> for item in it.islice(5):
        ...     print(item)
        1
        2
        1
        2
        1
        """
        return self._call_infinite(cycle, 0)

    def deepflatten(self, depth=_default, types=_default, ignore=_default):
        """See
        :py:func:`~iteration_utilities.deepflatten`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> lst = [1, 2, 3, [1, 2, 3, [1, 2, 3]]]
        >>> Iterable(lst).deepflatten().as_list()
        [1, 2, 3, 1, 2, 3, 1, 2, 3]

        >>> Iterable(lst).deepflatten(1, (list), (str)).as_list()
        [1, 2, 3, 1, 2, 3, [1, 2, 3]]

        >>> Iterable(lst).deepflatten(depth=1,
        ...                           types=(list), ignore=(str)).as_list()
        [1, 2, 3, 1, 2, 3, [1, 2, 3]]
        """
        return self._call(deepflatten, 0, depth=depth, types=types,
                          ignore=ignore)

    def dropwhile(self, predicate):
        """See :py:func:`itertools.dropwhile`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).dropwhile(lambda x: x < 5).as_list()
        [5, 6, 7, 8, 9]

        >>> Iterable(range(1, 10)).dropwhile(
        ...     predicate=lambda x: x < 3).as_list()
        [3, 4, 5, 6, 7, 8, 9]
        """
        return self._call(dropwhile, 1, predicate)

    def enumerate(self, start=_default):
        """See :py:func:`python:enumerate`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 8)).enumerate().as_list()
        [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7)]

        >>> Iterable(range(1, 8)).enumerate(4).as_list()
        [(4, 1), (5, 2), (6, 3), (7, 4), (8, 5), (9, 6), (10, 7)]

        >>> Iterable(range(1, 8)).enumerate(start=2).as_list()
        [(2, 1), (3, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7)]
        """
        return self._call(enumerate, 0, start=start)

    def filter(self, function):
        """See :py:func:`python:filter`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).filter(None).as_list()
        [1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> from iteration_utilities import is_even
        >>> Iterable(range(1, 10)).filter(is_even).as_list()
        [2, 4, 6, 8]

        >>> Iterable(range(1, 10)).filter(function=is_even).as_list()
        [2, 4, 6, 8]
        """
        return self._call(filter, 1, function)

    def filterfalse(self, predicate):
        """See :py:func:`itertools.filterfalse`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).filterfalse(None).as_list()
        []

        >>> from iteration_utilities import is_odd
        >>> Iterable(range(1, 10)).filterfalse(is_odd).as_list()
        [2, 4, 6, 8]

        >>> Iterable(range(1, 10)).filterfalse(predicate=is_odd).as_list()
        [2, 4, 6, 8]
        """
        return self._call(filterfalse, 1, predicate)

    def flatten(self):
        """See :py:func:`~iteration_utilities._recipes._core.flatten`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([(1, 2, 3), [3, 2, 1]]).flatten().as_list()
        [1, 2, 3, 3, 2, 1]
        """
        return self._call(flatten, 0)

    def grouper(self, n, fillvalue=_default, truncate=_default):
        """See :py:func:`~iteration_utilities.grouper`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).grouper(2).as_list()
        [(1, 2), (3, 4), (5, 6), (7, 8), (9,)]

        >>> Iterable(range(1, 10)).grouper(2, None).as_list()
        [(1, 2), (3, 4), (5, 6), (7, 8), (9, None)]

        >>> Iterable(range(1, 10)).grouper(n=2, fillvalue=None).as_list()
        [(1, 2), (3, 4), (5, 6), (7, 8), (9, None)]

        >>> Iterable(range(1, 10)).grouper(n=2, truncate=True).as_list()
        [(1, 2), (3, 4), (5, 6), (7, 8)]
        """
        return self._call(grouper, 0, n=n, fillvalue=fillvalue,
                          truncate=truncate)

    def islice(self, *args):
        """See :py:func:`itertools.islice`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).islice(2).as_list()
        [1, 2]

        >>> Iterable(range(1, 10)).islice(2, 6).as_list()
        [3, 4, 5, 6]

        >>> Iterable(range(1, 10)).islice(2, 6, 2).as_list()
        [3, 5]

        .. note::
           This method converts an `InfiniteIterable` to a normal `Iterable` if
           a `stop` is given.
        """
        nargs = len(args)
        meth = self._call
        if nargs == 1:
            if args[0] is not None:
                meth = self._call_finite
        else:
            if args[1] is not None:
                meth = self._call_finite
        return meth(islice, 0, *args)

    def intersperse(self, e):
        """See :py:func:`~iteration_utilities.intersperse`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).intersperse(0).as_list()
        [1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7, 0, 8, 0, 9]

        >>> Iterable(range(1, 10)).intersperse(e=0).as_list()
        [1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7, 0, 8, 0, 9]
        """
        return self._call(intersperse, 0, e=e)

    def map(self, function):
        """See :py:func:`python:map`.

        Examples
        --------
        >>> from iteration_utilities import Iterable, square
        >>> Iterable(range(1, 10)).map(square).as_list()
        {0}

        >>> Iterable(range(1, 10)).map(function=square).as_list()
        {0}
        """
        return self._call(map, 1, function)
    map.__doc__ = map.__doc__.format(
        '[1L, 4L, 9L, 16L, 25L, 36L, 49L, 64L, 81L]' if PY2 else
        '[1, 4, 9, 16, 25, 36, 49, 64, 81]')

    def ncycles(self, n):
        """See :py:func:`~iteration_utilities._recipes._core.ncycles`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 4)).ncycles(3).as_list()
        [1, 2, 3, 1, 2, 3, 1, 2, 3]

        >>> Iterable(range(1, 4)).ncycles(n=3).as_list()
        [1, 2, 3, 1, 2, 3, 1, 2, 3]
        """
        return self._call(ncycles, 0, n=n)

    def pad(self, fillvalue=_default, nlead=_default, ntail=_default):
        """See :py:func:`~iteration_utilities._recipes._additional.pad`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([2]).pad(None, ntail=None).islice(10).as_list()
        [2, None, None, None, None, None, None, None, None, None]

        >>> Iterable([2]).pad(nlead=9).as_list()
        [None, None, None, None, None, None, None, None, None, 2]

        >>> Iterable([2]).pad(0, ntail=9).as_list()
        [2, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        >>> Iterable([2]).pad(0, 1, 2).as_list()
        [0, 2, 0, 0]

        .. warning::
           This returns an `InfiniteIterable` if ``ntail=None``.
        """
        if ntail is None:
            meth = self._call_infinite
        else:
            meth = self._call
        return meth(pad, 0, fillvalue=fillvalue, nlead=nlead, ntail=ntail)

    def permutations(self, r=_default):
        """See :py:func:`itertools.permutations`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 4)).permutations().as_list()
        [(1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)]

        >>> Iterable(range(1, 4)).permutations(2).as_list()
        [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]

        >>> Iterable(range(1, 4)).permutations(r=2).as_list()
        [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]
        """
        return self._call(permutations, 0, r=r)

    def powerset(self):
        """See :py:func:`~iteration_utilities._recipes._core.powerset`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 4)).powerset().as_list()
        [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]
        """
        return self._call(powerset, 0)

    def prepend(self, element):
        """See :py:func:`~iteration_utilities._recipes._additional.prepend`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).prepend(100).as_list()
        [100, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> Iterable(range(1, 10)).prepend(element=100).as_list()
        [100, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        """
        return self._call(prepend, 1, element)

    def replicate(self, times):
        """See :py:func:`~iteration_utilities._recipes._additional.replicate`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 4)).replicate(3).as_list()
        [1, 1, 1, 2, 2, 2, 3, 3, 3]

        >>> Iterable(range(1, 4)).replicate(times=4).as_list()
        [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]
        """
        return self._call(replicate, 0, times=times)

    def split(self, key, maxsplit=_default, keep=_default, eq=_default):
        """See :py:func:`~iteration_utilities.split`.

        Examples
        --------
        >>> from iteration_utilities import Iterable, is_even, is_odd
        >>> Iterable(range(1, 10)).split(is_even).as_list()
        [[1], [3], [5], [7], [9]]

        >>> Iterable(range(1, 10)).split(is_even, 2).as_list()
        [[1], [3], [5, 6, 7, 8, 9]]

        >>> Iterable(range(1, 10)).split(3, 1, True, True).as_list()
        [[1, 2], [3], [4, 5, 6, 7, 8, 9]]

        >>> Iterable(range(1, 10)).split(key=2, maxsplit=1,
        ...                              keep=True, eq=True).as_list()
        [[1], [2], [3, 4, 5, 6, 7, 8, 9]]
        """
        return self._call(split, 0, key=key, maxsplit=maxsplit, keep=keep,
                          eq=eq)

    def starmap(self, function):
        """See :py:func:`itertools.starmap`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).enumerate().starmap(pow).as_list()
        [0, 1, 8, 81, 1024, 15625, 279936, 5764801, 134217728]
        """
        return self._call(starmap, 1, function)

    def successive(self, times):
        """See :py:func:`~iteration_utilities.successive`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).successive(2).as_list()
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9)]

        >>> Iterable(range(1, 10)).successive(times=2).as_list()
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9)]
        """
        return self._call(successive, 0, times=times)

    def tail(self, n):
        """See :py:func:`~iteration_utilities._recipes._core.tail`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).tail(2).as_list()
        [8, 9]

        >>> Iterable(range(1, 10)).tail(n=3).as_list()
        [7, 8, 9]
        """
        return self._call(tail, 0, n=n)

    def takewhile(self, predicate):
        """See :py:func:`itertools.takewhile`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).takewhile(lambda x: x < 4).as_list()
        [1, 2, 3]

        >>> Iterable(range(1, 10)).takewhile(
        ...     predicate=lambda x: x < 5).as_list()
        [1, 2, 3, 4]

        .. warning::
           This method converts an `InfiniteIterable` to a normal `Iterable`.
        """
        return self._call_finite(takewhile, 1, predicate)

    def unique_everseen(self, key=_default):
        """See :py:func:`~iteration_utilities.unique_everseen`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(1, 10)).unique_everseen().as_list()
        [1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> Iterable(range(1, 10)).unique_everseen(lambda x: x // 3).as_list()
        [1, 3, 6, 9]

        >>> from iteration_utilities import is_even
        >>> Iterable(range(1, 10)).unique_everseen(key=is_even).as_list()
        [1, 2]
        """
        return self._call(unique_everseen, 0, key=key)

    def unique_justseen(self, key=_default):
        """See :py:func:`~iteration_utilities.unique_justseen`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable('aaAAbbBcCcddDDDEEEee').unique_justseen().as_list()
        ['a', 'A', 'b', 'B', 'c', 'C', 'c', 'd', 'D', 'E', 'e']

        >>> from operator import methodcaller
        >>> Iterable('aaAAbbBcCcddDDDEEEee').unique_justseen(
        ...     methodcaller('upper')).as_list()
        ['a', 'b', 'c', 'd', 'E']

        >>> Iterable('aaAAbbBcCcddDDDEEEee').unique_justseen(
        ...     key=methodcaller('lower')).as_list()
        ['a', 'b', 'c', 'd', 'E']
        """
        return self._call(unique_justseen, 0, key=key)

    def unpack(self, iterable, idx):
        """See :py:func:`iteration_utilities._recipes._additional.unpack`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).unpack(range(3), 3).as_list()
        [0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> Iterable(range(10)).unpack(iterable=range(3), idx=3).as_list()
        [0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        """
        if isinstance(iterable, InfiniteIterable):
            meth = self._call_infinite
        else:
            meth = self._call
        return meth(unpack, 1, iterable, idx=idx)


class Iterable(_Base):
    """A convenience class that allows chaining the `iteration_utilities`
    functions.

    Parameters
    ----------
    iterable : iterable
        Any kind of `iterable`.

    Notes
    -----

    .. warning::
       If the `iterable` is infinite you should **not** create the `Iterable`
       instance directly (i.e. ``Iterable(count())``. You could use the
       ``Iterable.from_count()`` or create an :py:class:`InfiniteIterable`:
       ``InfiniteIterable(count())``.

    Examples
    --------
    You can create an instance from any object that implements the iteration
    protocol. For example the Python types `list`, `tuple`, `set`,
    `frozenset`, `str`, `dict`, `dict.values()`, `dict.items()`, `range` just
    to name a few::

        >>> from iteration_utilities import Iterable
        >>> Iterable([1,2,3,4])
        <Iterable: [1, 2, 3, 4]>

        >>> Iterable('abcdefghijklmnopqrstuvwxyz')
        <Iterable: 'abcdefghijklmnopqrstuvwxyz'>

    The primary use of `Iterable` is because it allows easy chaining of
    several functional programming functions implemented in Python (`map`,
    `filter`, ...), `itertools` and `iteration_utilities`::

        >>> Iterable([1,2,3,4]).islice(1,3).map(float).as_list()
        [2.0, 3.0]

    The methods `islice` and `map` are only evaluated when `as_list` is called.
    The class can also be used in `for` loops::

        >>> from iteration_utilities import is_even
        >>> for item in Iterable(range(100, 120)).filter(is_even).accumulate():
        ...     print(item)
        100
        202
        306
        412
        520
        630
        742
        856
        972
        1090

    Using some methods (:py:meth:`Iterable.cycle`) create an
    :py:class:`InfiniteIterable`::

        >>> Iterable(range(10)).cycle()  # doctest: +ELLIPSIS
        <InfiniteIterable: <itertools.cycle object at ...>>

        >>> Iterable(range(10)).unpack(Iterable.from_count(), idx=3)  \
# doctest: +ELLIPSIS
        <InfiniteIterable: <itertools.chain object at ...>>

    Also some of the staticmethods (``from_x``)::

        >>> Iterable.from_count()
        <InfiniteIterable: count(0)>

        >>> Iterable.from_repeat(10)
        <InfiniteIterable: repeat(10)>

        >>> Iterable.from_repeat(10, times=2)  # but not always!
        <Iterable: repeat(10, 2)>

    This logic allows to be aware if the iterable is infinitly long or not.
    Some methods can also convert an :py:class:`InfiniteIterable` to a normal
    :py:class:`Iterable` again::

        >>> Iterable.from_count().islice(2, 5)  # doctest: +ELLIPSIS
        <Iterable: <itertools.islice object at ...>>

        >>> Iterable.from_count().takewhile(lambda x: x < 100)  \
# doctest: +ELLIPSIS
        <Iterable: <itertools.takewhile object at ...>>

    :py:class:`Iterable` implements some constructors for Python types as
    methods::

        >>> Iterable(range(10)).as_list()
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> # But also some less common ones, like OrderedDict
        >>> Iterable(range(6)).enumerate(4).as_ordered_dict()
        OrderedDict([(4, 0), (5, 1), (6, 2), (7, 3), (8, 4), (9, 5)])

    .. warning::
       These methods are (obviously) not avaiable for `InfiniteIterable`!
    """
    __slots__ = ('_iterable')

    def as_(self, cls):
        """Convert `Iterable` to other class.

        Parameters
        ----------
        cls : type
            Convert the content of `Iterable` to this class.

        Returns
        -------
        iterable : cls
            The `Iterable` as `cls`.

        Notes
        -----
        Be careful if you use this method because the `Iterable` may be
        infinite.
        """
        return cls(self._iterable)

    def as_list(self):
        """See :py:meth:`as_`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(5)).as_list()
        [0, 1, 2, 3, 4]
        """
        return self.as_(list)

    def as_tuple(self):
        """See :py:meth:`as_`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(5)).as_tuple()
        (0, 1, 2, 3, 4)
        """
        return self.as_(tuple)

    def as_set(self):
        """See :py:meth:`as_`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([1]).as_set()
        {0}
        """
        return self.as_(set)
    as_set.__doc__ = as_set.__doc__.format('set([1])' if PY2 else '{1}')

    def as_frozen_set(self):
        """See :py:meth:`as_`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([5]).as_frozen_set()
        frozenset({0})
        """
        return self.as_(frozenset)
    as_frozen_set.__doc__ = as_frozen_set.__doc__.format('[5]' if PY2 else
                                                         '{5}')

    def as_dict(self):
        """See :py:meth:`as_`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([1]).enumerate().as_dict()
        {0: 1}
        """
        return self.as_(dict)

    def as_ordered_dict(self):
        """See :py:meth:`as_`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(3, 6)).enumerate().as_ordered_dict()
        OrderedDict([(0, 3), (1, 4), (2, 5)])
        """
        return self.as_(OrderedDict)

    def as_counter(self):
        """See :py:meth:`as_`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable('supercalifragilisticexpialidocious').as_counter()  \
# doctest: +SKIP
        Counter({'i': 7, 's': 3, 'l': 3, 'c': 3, 'a': 3, 'e': 2, 'o': 2, \
'p': 2, 'r': 2, 'u': 2, 'd': 1, 'g': 1, 'f': 1, 'x': 1, 't': 1})

        >>> Iterable([1, 1, 1]).as_counter()
        Counter({1: 3})
        """
        return self.as_(Counter)

    def reversed(self):
        """See :py:func:`python:reversed`.

        .. warning::
           This method requires that the wrapped iterable is a `Sequence` or
           implements the `reversed` iterator protocol. Generally this does not
           work with generators!

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([1, 2, 3]).reversed().as_list()
        [3, 2, 1]
        """
        return self.__class__(reversed(self._iterable))

    def _get(self, *args, **kwargs):
        fn = args[0]
        pos = args[1]
        args = list(islice(args, 2, None))
        args.insert(pos, self)
        kwargs = filterkwargs(**kwargs)
        return fn(*args, **kwargs)

    def _get_iter(self, *args, **kwargs):
        fn = args[0]
        pos = args[1]
        args = list(islice(args, 2, None))
        args.insert(pos, iter(self))
        kwargs = filterkwargs(**kwargs)
        return fn(*args, **kwargs)

    def get_all(self):
        """See :py:func:`python:all`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).map(lambda x: x > 2).get_all()
        False

        >>> Iterable(range(10)).map(lambda x: x >= 0).get_all()
        True
        """
        return self._get(all, 0)

    def get_all_distinct(self):
        """See :py:func:`~iteration_utilities._cfuncs.all_distinct`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_all_distinct()
        True

        >>> Iterable([1, 2, 3, 4, 5, 6, 7, 1]).get_all_distinct()
        False
        """
        return self._get(all_distinct, 0)

    def get_all_equal(self):
        """See :py:func:`~iteration_utilities._cfuncs.all_equal`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_all_equal()
        False

        >>> Iterable([1]*100).get_all_equal()
        True
        """
        return self._get(all_equal, 0)

    def get_any(self):
        """See :py:func:`python:any`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).map(lambda x: x > 2).get_any()
        True

        >>> Iterable(range(10)).map(lambda x: x >= 10).get_any()
        False
        """
        return self._get(any, 0)

    def get_argmax(self, key=_default, default=_default):
        """See :py:func:`~iteration_utilities._cfuncs.argmax`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([1, 2, -5, 3, 4]).get_argmax()
        4{0}

        >>> Iterable([1, 2, -5, 3, 4]).get_argmax(abs)
        2{0}

        >>> Iterable([1, 2, -5, 3, 4]).get_argmax(key=abs)
        2{0}

        >>> Iterable([]).get_argmax(key=abs, default=-1)
        -1{0}
        """
        return self._get(argmax, 0, key=key, default=default)
    get_argmax.__doc__ = get_argmax.__doc__.format('L' if PY2 else '')

    def get_argmin(self, key=_default, default=_default):
        """See :py:func:`~iteration_utilities._cfuncs.argmin`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([1, 2, -5, 3, 4]).get_argmin()
        2{0}

        >>> Iterable([1, 2, -5, 3, 4]).get_argmin(abs)
        0{0}

        >>> Iterable([1, 2, -5, 3, 4]).get_argmin(key=abs)
        0{0}

        >>> Iterable([]).get_argmin(key=abs, default=-1)
        -1{0}
        """
        return self._get(argmin, 0, key=key, default=default)
    get_argmin.__doc__ = get_argmin.__doc__.format('L' if PY2 else '')

    def get_count_items(self, pred=_default, eq=_default):
        """See :py:func:`~iteration_utilities._cfuncs.count_items`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable((i for i in range(10))).get_count_items()
        10{0}

        >>> Iterable([1, 2, 3, 2, 1]).get_count_items(2, True)
        2{0}

        >>> Iterable([1, 2, 3, 2, 1]).get_count_items(pred=2, eq=True)
        2{0}
        """
        return self._get(count_items, 0, pred=pred, eq=eq)
    get_count_items.__doc__ = get_count_items.__doc__.format(
        'L' if PY2 else '')

    def get_first(self, default=_default, pred=_default, truthy=_default,
                  retpred=_default, retidx=_default):
        """See :py:func:`~iteration_utilities.nth`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_first()
        0

        >>> Iterable(range(1, 10, 2)).get_first(pred=lambda x: x > 5)
        7
        """
        return self._get(first, 0, default=default, pred=pred, truthy=truthy,
                         retpred=retpred, retidx=retidx)

    def get_fsum(self):
        """See :py:func:`math.fsum`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_fsum()
        45.0
        """
        return self._get(fsum, 0)

    def get_groupedby(self, key, keep=_default, reduce=_default,
                      reducestart=_default):
        """See :py:func:`~iteration_utilities._cfuncs.groupedby`.

        Examples
        --------
        >>> from iteration_utilities import Iterable, is_even
        >>> grp = Iterable(range(10)).get_groupedby(is_even)
        >>> grp[True]
        [0, 2, 4, 6, 8]
        >>> grp[False]
        [1, 3, 5, 7, 9]
        """
        return self._get(groupedby, 0, key, keep=keep, reduce=reduce,
                         reducestart=reducestart)

    def get_last(self, default=_default, pred=_default, truthy=_default,
                 retpred=_default, retidx=_default):
        """See :py:func:`~iteration_utilities.nth`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_last()
        9

        >>> Iterable(range(1, 10, 2)).get_last(pred=lambda x: x > 5)
        9
        """
        return self._get(last, 0, default=default, pred=pred, truthy=truthy,
                         retpred=retpred, retidx=retidx)

    # min and max had no default parameter before python 3.4
    if PY2 or not PY34:
        def get_max(self, key=_default):
            """See :py:func:`max`.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1, 2, -5, 3, 4]).get_max()
            4

            >>> Iterable([1, 2, -5, 3, 4]).get_max(abs)
            -5

            >>> Iterable([1, 2, -5, 3, 4]).get_max(key=abs)
            -5
            """
            return self._get(max, 0, key=key)

        def get_min(self, key=_default):
            """See :py:func:`min`.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1, 2, -5, 3, 4]).get_min()
            -5

            >>> Iterable([1, 2, -5, 3, 4]).get_min(abs)
            1

            >>> Iterable([1, 2, -5, 3, 4]).get_min(key=abs)
            1
            """
            return self._get(min, 0, key=key)
    else:
        def get_max(self, key=_default, default=_default):
            """See :py:func:`python:max`.

            .. note::
               The `default`-parameter is not avaiable at Python 3.3

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1, 2, -5, 3, 4]).get_max()
            4

            >>> Iterable([1, 2, -5, 3, 4]).get_max(abs)
            -5

            >>> Iterable([1, 2, -5, 3, 4]).get_max(key=abs)
            -5

            >>> Iterable([]).get_max(key=abs, default=-1)
            -1
            """
            return self._get(max, 0, key=key, default=default)

        def get_min(self, key=_default, default=_default):
            """See :py:func:`python:min`.

            .. note::
               The `default`-parameter is not avaiable at Python 3.3

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1, 2, -5, 3, 4]).get_min()
            -5

            >>> Iterable([1, 2, -5, 3, 4]).get_min(abs)
            1

            >>> Iterable([1, 2, -5, 3, 4]).get_min(key=abs)
            1

            >>> Iterable([]).get_min(key=abs, default=-1)
            -1
            """
            return self._get(min, 0, key=key, default=default)

    def get_minmax(self, key=_default, default=_default):
        """See :py:func:`~iteration_utilities._cfuncs.minmax`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([1, 2, -5, 3, 4]).get_minmax()
        (-5, 4)

        >>> Iterable([1, 2, -5, 3, 4]).get_minmax(abs)
        (1, -5)

        >>> Iterable([1, 2, -5, 3, 4]).get_minmax(key=abs)
        (1, -5)

        >>> Iterable([]).get_minmax(key=abs, default=-1)
        (-1, -1)
        """
        return self._get(minmax, 0, key=key, default=default)

    def get_nth(self, n, default=_default, pred=_default, truthy=_default,
                retpred=_default, retidx=_default):
        """See :py:func:`~iteration_utilities.nth`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_nth(6)
        6

        >>> Iterable(range(1, 10, 2)).get_nth(0, pred=lambda x: x > 5)
        7
        """
        return self._get(nth(n), 0, default=default, pred=pred, truthy=truthy,
                         retpred=retpred, retidx=retidx)

    def get_nlargest(self, n, key=_default):
        """See :py:func:`heapq.nlargest`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([4,1,2,3,1,5,8,2,-10]).get_nlargest(3)
        [8, 5, 4]

        >>> Iterable([4,1,2,3,1,5,8,2,-10]).get_nlargest(3, key=abs)
        [-10, 8, 5]
        """
        return self._get(nlargest, 1, n, key=key)

    def get_nsmallest(self, n, key=_default):
        """See :py:func:`heapq.nsmallest`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([4,1,2,3,1,5,8,2]).get_nsmallest(3)
        [1, 1, 2]
        """
        return self._get(nsmallest, 1, n, key=key)

    def get_one(self):
        """See :py:func:`~iteration_utilities._cfuncs.one`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([1]).get_one()
        1
        """
        return self._get(one, 0)

    def get_partition(self, func=_default):
        """See :py:func:`~iteration_utilities._cfuncs.partition`.

        Examples
        --------
        >>> from iteration_utilities import Iterable, is_even
        >>> Iterable(range(5)).get_partition(is_even)
        ([1, 3], [0, 2, 4])
        """
        return self._get(partition, 0, func=func)

    def get_reduce(self, *args):
        """See :py:func:`functools.reduce`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> from operator import add
        >>> Iterable(range(5)).get_reduce(add)
        10
        """
        return self._get(reduce, 1, *args)

    def get_second(self, default=_default, pred=_default, truthy=_default,
                   retpred=_default, retidx=_default):
        """See :py:func:`~iteration_utilities.nth`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_second()
        1

        >>> Iterable(range(1, 10, 2)).get_second(pred=lambda x: x > 5)
        9
        """
        return self._get(second, 0, default=default, pred=pred, truthy=truthy,
                         retpred=retpred, retidx=retidx)

    def get_sorted(self, key=_default, reverse=_default):
        """See :py:func:`python:sorted`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([3, 1, 5, 12, 7]).get_sorted()
        [1, 3, 5, 7, 12]
        """
        return self._get(sorted, 0, key=key, reverse=reverse)

    def get_sum(self, start=_default):
        """See :py:func:`python:sum`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable([3, 1, 5, 12, 7]).get_sum()
        28

        >>> Iterable([3, 1, 5, 12, 7]).get_sum(10)
        38
        """
        if start is _default:
            return self._get(sum, 0)
        return self._get(sum, 0, start)

    def get_take(self, n):
        """See :py:func:`~iteration_utilities._recipes._core.take`.

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(100)).get_take(3)
        [0, 1, 2]
        """
        return self._get(take, 0, n)

    def get_third(self, default=_default, pred=_default, truthy=_default,
                  retpred=_default, retidx=_default):
        """See :py:func:`~iteration_utilities.nth`.

        Examples
        --------
        >>> from iteration_utilities import Iterable

        Examples
        --------
        >>> from iteration_utilities import Iterable
        >>> Iterable(range(10)).get_third()
        2

        >>> Iterable(range(1, 10, 2)).get_third(default=-1,
        ...                                     pred=lambda x: x > 5)
        -1
        """
        return self._get(third, 0, default=default, pred=pred, truthy=truthy,
                         retpred=retpred, retidx=retidx)

    # Statistics module is only avaiable since Python 3.4
    if PY34:
        def get_mean(self):
            """See :py:func:`statistics.mean`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable(range(10)).get_mean()
            4.5
            """
            return self._get_iter(statistics.mean, 0)

        def get_median(self):
            """See :py:func:`statistics.median`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable(range(11)).get_median()
            5
            """
            return self._get_iter(statistics.median, 0)

        def get_median_low(self):
            """See :py:func:`statistics.median_low`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable(range(10)).get_median_low()
            4
            """
            return self._get_iter(statistics.median_low, 0)

        def get_median_high(self):
            """See :py:func:`statistics.median_high`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable(range(10)).get_median_high()
            5
            """
            return self._get_iter(statistics.median_high, 0)

        def get_median_grouped(self, interval=_default):
            """See :py:func:`statistics.median_grouped`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable(range(10)).get_median_grouped(interval=4)
            3.0
            """
            return self._get_iter(statistics.median_grouped, 0,
                                  interval=interval)

        def get_mode(self):
            """See :py:func:`statistics.mode`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1,1,1,2,2,3,4,5,6,7,7,8,8]).get_mode()
            1
            """
            return self._get_iter(statistics.mode, 0)

        def get_pstdev(self, mu=_default):
            """See :py:func:`statistics.pstdev`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1,1,1,2,2,3,4,5,6,7,7,8,8]).get_pstdev()
            2.635667953694125
            """
            return self._get_iter(statistics.pstdev, 0, mu=mu)

        def get_pvariance(self, mu=_default):
            """See :py:func:`statistics.pvariance`.

            .. note::
               Python >= 3.4 is required for this function.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1,1,1,2,2,3,4,5,6,7,7,8,8]).get_pvariance()  \
# doctest: +ELLIPSIS
            6.94674556...
            """
            return self._get_iter(statistics.pvariance, 0, mu=mu)

        def get_stdev(self, xbar=_default):
            """See :py:func:`statistics.stdev`.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1,1,1,2,2,3,4,5,6,7,7,8,8]).get_stdev()
            2.743290182543769
            """
            return self._get_iter(statistics.stdev, 0, xbar=xbar)

        def get_variance(self, mu=_default):
            """See :py:func:`statistics.variance`.

            Examples
            --------
            >>> from iteration_utilities import Iterable
            >>> Iterable([1,1,1,2,2,3,4,5,6,7,7,8,8]).get_variance()
            7.5256410256410255
            """
            return self._get_iter(statistics.variance, 0, mu=mu)


class InfiniteIterable(_Base):
    """Like :py:class:`Iterable` but indicates that the wrapped iterable is
    infinitly long.

    .. warning::
       The ``Iterable.as_*`` methods are not avaiable for `InfiniteIterable`
       because it would be impossible to create these types. Use
       :py:meth:`Iterable.islice` or :py:meth:`Iterable.takewhile` to convert
       an infinite iterable to a finite iterable. It is still possible to
       iterate over the iterable with ``for item in ...`` or using the Python
       constructors like ``list`` directly. This may fail fatally!

    Mostly it is not necessary to use `InfiniteIterable` directly because the
    corresponding methods on `Iterable` return an `InfiniteIterable` when
    appropriate. However using ``isinstance(some_iterable, InfiniteIterable)``
    could be used to determine if the :py:class:`Iterable` is infinite!
    """
    __slots__ = ('_iterable')


class ManyIterables(object):
    __slots__ = ('_iterables')

    def __init__(self, *iterables):
        """`ManyIterables` stores several `Iterables` and implements methods to
        convert these to one `Iterable`.

        .. warning::
           `ManyIterables` itself does not implement iteration!

        Parameters
        ----------
        *iterables : any amount of iterables
            The `iterables` to store.

        Notes
        -----
        This is just a convenience class to seperate the expressions dealing
        with multiple iterables from those applying on one.

        Examples
        --------
        Depending on the function and the types of the `iterables` the returned
        class may be different. For example :py:meth:`map` returns an infinite
        iterable if **all** `iterables` are infinite::

            >>> from iteration_utilities import ManyIterables
            >>> ManyIterables(Iterable.from_count(10), range(10)).map(pow)  \
# doctest: +ELLIPSIS
            <Iterable: <{0} object at ...>>

            >>> ManyIterables(Iterable.from_count(10),
            ...               Iterable.from_count(10)).map(pow)  \
# doctest: +ELLIPSIS
            <InfiniteIterable: <{0} object at ...>>

        While other methods also return an infinite iterable if **any** of the
        `iterables` is infinite::

            >>> ManyIterables(range(10), Iterable.from_count(10)).merge()  \
# doctest: +ELLIPSIS
            <InfiniteIterable: <iteration_utilities.merge object at ...>>

            >>> ManyIterables(range(10), range(10)).merge()  \
# doctest: +ELLIPSIS
            <Iterable: <iteration_utilities.merge object at ...>>

        Each method has a note explicitly stating to which of these categories
        it belongs.
        """
        self._iterables = iterables

    __init__.__doc__ = __init__.__doc__.format('itertools.imap' if PY2
                                               else 'map')

    def _call(self, fn, infinitecheck, *args, **kwargs):
        iterables = self._iterables
        if infinitecheck and any_isinstance(iterables, InfiniteIterable):
            cls = InfiniteIterable
        elif not infinitecheck and all_isinstance(iterables, InfiniteIterable):
            cls = InfiniteIterable
        else:
            cls = Iterable
        if args:
            iterables = args + iterables
        return cls(fn(*iterables, **filterkwargs(**kwargs)))

    def chain(self):
        """See :py:func:`itertools.chain`.

        .. note::
           If any of the `Iterables` is infinite then this will also return
           an `InfiniteIterable`.

        Examples
        --------
        >>> from iteration_utilities import ManyIterables
        >>> ManyIterables([1,3,5,7,9], [0,2,4,6,8]).chain().as_list()
        [1, 3, 5, 7, 9, 0, 2, 4, 6, 8]
        """
        return self._call(chain, True)

    def map(self, function):
        """See :py:func:`python:map`.

        .. note::
           If **all** of the `Iterables` is infinite then this will also return
           an `InfiniteIterable`.

        Examples
        --------
        >>> from iteration_utilities import ManyIterables
        >>> ManyIterables([1,3,5,7,9], [0,2,4,6,8]).map(pow).as_list()
        [1, 9, 625, 117649, 43046721]
        """
        return self._call(map, False, function)

    def merge(self, key=_default, reverse=_default):
        """See :py:func:`~iteration_utilities.merge`.

        .. note::
           If any of the `Iterables` is infinite then this will also return
           an `InfiniteIterable`.

        Examples
        --------
        >>> from iteration_utilities import ManyIterables
        >>> ManyIterables([1,3,5,7,9], [0,2,4,6,8]).merge().as_list()
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> from operator import neg
        >>> ManyIterables([1,3,5,7,9], [0,2,4,6,8]).merge(neg, True).as_list()
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        >>> ManyIterables([1,3,5,7,9], [0,2,4,6,8]).merge(
        ...     key=neg, reverse=True).as_list()
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        """
        return self._call(merge, True, key=key, reverse=reverse)

    def product(self, repeat=_default):
        """See :py:func:`itertools.product`.

        .. note::
           If any of the `Iterables` is infinite then this will also return
           an `InfiniteIterable`.

        Examples
        --------
        >>> from iteration_utilities import ManyIterables
        >>> ManyIterables([1,2], [10, 11, 12]).product().as_list()
        [(1, 10), (1, 11), (1, 12), (2, 10), (2, 11), (2, 12)]

        >>> ManyIterables([1], [10, 11]).product(2).as_list()
        [(1, 10, 1, 10), (1, 10, 1, 11), (1, 11, 1, 10), (1, 11, 1, 11)]

        >>> ManyIterables([1], [10, 11]).product(repeat=2).as_list()
        [(1, 10, 1, 10), (1, 10, 1, 11), (1, 11, 1, 10), (1, 11, 1, 11)]
        """
        return self._call(product, True, repeat=repeat)

    def roundrobin(self):
        """See :py:func:`~iteration_utilities.roundrobin`.

        .. note::
           If any of the `Iterables` is infinite then this will also return
           an `InfiniteIterable`.

        Examples
        --------
        >>> from iteration_utilities import ManyIterables
        >>> ManyIterables([1,2,3,4], [10, 11, 12]).roundrobin().as_list()
        [1, 10, 2, 11, 3, 12, 4]
        """
        return self._call(roundrobin, True)

    def zip(self):
        """See :py:func:`python:zip`.

        .. note::
           If **all** of the `Iterables` is infinite then this will also return
           an `InfiniteIterable`.

        Examples
        --------
        >>> from iteration_utilities import ManyIterables
        >>> ManyIterables([1,2,3,4], [2,3,4,5]).zip().as_list()
        [(1, 2), (2, 3), (3, 4), (4, 5)]
        """
        return self._call(zip, False)

    def zip_longest(self, fillvalue=_default):
        """See :py:func:`itertools.zip_longest`.

        .. note::
           If any of the `Iterables` is infinite then this will also return
           an `InfiniteIterable`.

        Examples
        --------
        >>> from iteration_utilities import ManyIterables
        >>> ManyIterables([1,2,3,4], [2,3,4]).zip_longest().as_list()
        [(1, 2), (2, 3), (3, 4), (4, None)]

        >>> ManyIterables([1,2,3,4], [2,3,4]).zip_longest('x').as_list()
        [(1, 2), (2, 3), (3, 4), (4, 'x')]

        >>> ManyIterables([1,2,3,4], [2,3,4]).zip_longest(
        ...     fillvalue='x').as_list()
        [(1, 2), (2, 3), (3, 4), (4, 'x')]
        """
        return self._call(zip_longest, True, fillvalue=fillvalue)
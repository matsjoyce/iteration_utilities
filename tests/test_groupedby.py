# Built-ins
from __future__ import absolute_import, division, print_function
import operator
import pickle

# 3rd party
import pytest

# This module
import iteration_utilities

# Test helper
from helper_leak import memory_leak
from helper_pytest_monkeypatch import pytest_raises


groupedby = iteration_utilities.groupedby


class T(object):
    def __init__(self, value):
        self.value = value

    def __getitem__(self, item):
        return self.__class__(self.value[item])

    def __len__(self):
        return len(self.value)

    def __add__(self, other):
        return self.__class__(self.value + other.value)

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


def test_groupedby_empty1():
    assert groupedby([], key=lambda x: x) == {}

    def test():
        groupedby([], key=lambda x: x)
    assert not memory_leak(test)


def test_groupedby_normal1():
    assert groupedby(['a', 'ab', 'abc'],
                     key=operator.itemgetter(0)) == {'a': ['a', 'ab', 'abc']}

    def test():
        groupedby([T('a'), T('ab'), T('abc')],
                  key=operator.itemgetter(0))
    assert not memory_leak(test)


def test_groupedby_normal2():
    assert groupedby(['a', 'ba', 'ab', 'abc', 'b'],
                     key=operator.itemgetter(0)) == {'a': ['a', 'ab', 'abc'],
                                                     'b': ['ba', 'b']}

    def test():
        groupedby([T('a'), T('ba'), T('ab'), T('abc'), T('b')],
                  key=operator.itemgetter(0))
    assert not memory_leak(test)


def test_groupedby_keep1():
    assert groupedby(['a', 'ba', 'ab', 'abc', 'b'],
                     key=operator.itemgetter(0),
                     keep=len) == {'a': [1, 2, 3], 'b': [2, 1]}

    def test():
        groupedby([T('a'), T('ba'), T('ab'), T('abc'), T('b')],
                  key=operator.itemgetter(0),
                  keep=len)
    assert not memory_leak(test)


def test_groupedby_reduce1():
    assert groupedby([('a', 1), ('a', 2), ('b', 5)],
                     key=operator.itemgetter(0),
                     keep=operator.itemgetter(1),
                     reduce=operator.add) == {'a': 3, 'b': 5}

    def test():
        groupedby([(T('a'), T(1)), (T('a'), T(2)), (T('b'), T(5))],
                  key=operator.itemgetter(0),
                  keep=operator.itemgetter(1),
                  reduce=operator.add)
    assert not memory_leak(test)


def test_groupedby_reduce2():
    assert groupedby([('a', 1), ('a', 2), ('b', 5)],
                     key=operator.itemgetter(0),
                     reduce=lambda x, y: x + y[1],
                     reducestart=0) == {'a': 3, 'b': 5}

    def test():
        groupedby([(T('a'), T(1)), (T('a'), T(2)), (T('b'), T(5))],
                  key=operator.itemgetter(0),
                  reduce=lambda x, y: x + y[1],
                  reducestart=T(0))
    assert not memory_leak(test)


def test_groupedby_failure1():
    # not iterable
    with pytest.raises(TypeError):
        groupedby(1, key=len)

    def test():
        with pytest_raises(TypeError):
            groupedby(T(1), key=len)
    assert not memory_leak(test)


def test_groupedby_failure2():
    # key func fails
    with pytest.raises(TypeError):
        groupedby([1, 2, 3], key=lambda x: x + 'a')

    def test():
        with pytest_raises(TypeError):
            groupedby([T(1), T(2), T(3)], key=lambda x: T(x.value + 'a'))
    assert not memory_leak(test)


def test_groupedby_failure3():
    # keep func fails
    with pytest.raises(TypeError):
        groupedby([1, 2, 3], key=lambda x: x, keep=lambda x: x + 'a')

    def test():
        with pytest_raises(TypeError):
            groupedby([T(1), T(2), T(3)],
                      key=lambda x: x, keep=lambda x: T(x.value + 'a'))
    assert not memory_leak(test)


def test_groupedby_failure4():
    # unhashable
    with pytest.raises(TypeError):
        groupedby([{'a': 10}], key=lambda x: x)

    def test():
        with pytest_raises(TypeError):
            groupedby([{T('a'): T(10)}], key=lambda x: x)
    assert not memory_leak(test)


def test_groupedby_failure5():
    # no reduce but reducestart
    with pytest.raises(TypeError):
        groupedby(range(10), lambda x: x, reducestart=0)

    def test():
        with pytest_raises(TypeError):
            groupedby(map(T, range(10)), lambda x: x, reducestart=T(0))
    assert not memory_leak(test)


def test_groupedby_failure6():
    # reduce function fails with reducestart
    with pytest.raises(TypeError):
        groupedby(range(10), iteration_utilities.is_even,
                  reduce=operator.add, reducestart='a')

    def test():
        with pytest_raises(TypeError):
            groupedby(map(T, range(10)), lambda x: x.value % 2 == 0,
                      reduce=operator.add, reducestart=T('a'))
    assert not memory_leak(test)


def test_groupedby_failure7():
    # reduce function fails
    with pytest.raises(TypeError):
        groupedby([1, 2, 3, 4, 'a'], lambda x: True, reduce=operator.add)

    def test():
        with pytest_raises(TypeError):
            groupedby(map(T, [1, 2, 3, 4, 'a']), lambda x: True,
                      reduce=operator.add)
    assert not memory_leak(test)

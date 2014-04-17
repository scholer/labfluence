#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2013 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##
# pylint: disable=C0103,W0212



import logging
logger = logging.getLogger(__name__)


#### SUT ####
from model.decorators.cache_decorator import cached_property



class TestClass(object):
    def __init__(self):
        self.numchanges = 0
    @cached_property()
    def MyProp(self):
        self.numchanges += 1
        return self.numchanges
    @cached_property(-1)
    def AlwaysExpired(self):
        self.numchanges += 1
        return self.numchanges


def test_basics():
    obj = TestClass()
    assert obj.numchanges == 0
    assert obj.MyProp == 1
    assert obj.numchanges == 1
    assert obj.MyProp == 1
    assert obj.MyProp == 1
    obj.MyProp = 5
    assert obj._cache['MyProp'][0] == 5
    assert obj.numchanges == 1
    assert obj.MyProp == 5


def test_setfirst():
    obj = TestClass()
    assert obj.numchanges == 0
    obj.MyProp = 5
    assert obj.numchanges == 0
    assert obj.MyProp == 5
    assert obj.MyProp == 5

def test_deleter():
    obj = TestClass()
    assert obj.numchanges == 0
    assert obj.MyProp == 1
    assert obj.numchanges == 1
    del obj.MyProp
    assert obj.numchanges == 1
    obj.numchanges = 4
    assert obj.MyProp == 5
    assert obj.numchanges == 5
    del obj.MyProp
    obj.MyProp = 10
    assert obj.MyProp == 10
    assert obj.numchanges == 5

def test_expired():
    obj = TestClass()
    assert obj.numchanges == 0
    assert obj.MyProp == 1
    assert obj.MyProp == 1
    assert obj.numchanges == 1
    assert obj.AlwaysExpired == 2
    assert obj.MyProp == 1
    assert obj.numchanges == 2
    assert obj.AlwaysExpired == 3
    assert obj.AlwaysExpired == 4
    assert obj.MyProp == 1
    assert obj.numchanges == 4

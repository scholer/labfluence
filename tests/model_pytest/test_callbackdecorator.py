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


import os
import sys
import pytest
import logging
logger = logging.getLogger(__name__)

from pathutils import walkup

approotdir = os.path.join(walkup(os.path.realpath(__file__), 3))
modeldir = os.path.join(approotdir, 'model')
testsdir = os.path.join(approotdir, 'tests')
testdatadir = os.path.join(testsdir, 'test_data')
sys.path.append(approotdir)
sys.path.append(modeldir)


#### SUT ####
from model.decorators.callback_decorator import callback_property, hashunhashable, gethash



class TestClass(object):
    def __init__(self):
        self.numchanges = 0

    @callback_property()
    def ReadOnlyProp(self):
        self.numchanges += 1
        return self.numchanges
    @callback_property()
    def MyProp(self):
        self.numchanges += 1
        return self.numchanges
    @MyProp.setter
    def MyProp(self, value):
        self.numchanges = value



def test_hashunhashable():
    val = "mystring"
    assert hashunhashable(val) == hash(val)
    assert gethash(val) == hash(val)
    val = ['str1', 'str2', 'str3']
    expected = sum(hash(st) for st in val)
    assert hashunhashable(val) == expected
    assert gethash(val) == expected


def test_basics():
    obj = TestClass()
    assert obj.numchanges == 0
    assert obj.MyProp == 1
    assert obj.numchanges == 1
    obj.MyProp = 4
    assert obj.MyProp == 5

@pytest.mark.skipif(True, reason="Callback property decorator attempt is cancelled.")
def test_registercallback():
    obj = TestClass()
    assert obj.numchanges == 0
    myvar = 0
    def mycallback():
        myvar += 2
    obj.MyProp.registercallback(mycallback)

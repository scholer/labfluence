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
# pylint: disable=C0111,C0103,W0212


import os
import sys
#import pytest
import logging
logger = logging.getLogger(__name__)

from pathutils import walkup

approotdir = os.path.join(walkup(os.path.realpath(__file__), 3))
modeldir = os.path.join(approotdir, 'model')
testsdir = os.path.join(approotdir, 'tests')
testdatadir = os.path.join(testsdir, 'test_data')
sys.path.append(approotdir) # Uh... if you really do this for all test_* modules, the sys.path will be super long...
#sys.path.append(modeldir)


#### SUT ####
from model.mixin.simplecallbacksystem import SimpleCallbackSystem



class TestClass(SimpleCallbackSystem):
    def __init__(self):
        SimpleCallbackSystem.__init__(self)
        self.numchanges = 0

    @property
    def ReadOnlyProp(self):
        self.numchanges += 1
        return self.numchanges
    @property
    def MyProp(self):
        self.numchanges += 1
        return self.numchanges
    @MyProp.setter
    def MyProp(self, value):
        if value != self.numchanges:
            self.numchanges = value
            self.invokePropertyCallbacks('MyProp', value)

    def resetCount(self):
        self.numchanges = 0
        self.invokePropertyCallbacks('MyProp', self.numchanges)


def test_basics():
    obj = TestClass()
    assert obj.numchanges == 0
    assert obj.MyProp == 1
    assert obj.numchanges == 1
    obj.MyProp = 4
    assert obj.MyProp == 5


def test_registercallback():
    obj = TestClass()
    assert obj.numchanges == 0
    myvar = [0]
    lastnewvalue = [None]
    # need a closure: ? - no, you just need to consume the variables *indirectly*, e.g. as a list.
    def mycallback(newvalue):
        myvar[0] += 2 ## Why is this 'undefined'? Ah, it must be a list...
        lastnewvalue[0] = newvalue

    obj.registerPropertyCallback('MyProp', mycallback)
    obj.MyProp = 4
    assert obj.numchanges == 4
    assert lastnewvalue == [4]
    assert myvar == [2]

    obj.resetCount()
    assert obj.numchanges == 0
    assert lastnewvalue == [0]
    assert myvar == [4]

    assert obj.ReadOnlyProp == 1
    assert lastnewvalue == [0]
    obj.unregisterPropertyCallback('MyProp', mycallback)
    obj.MyProp = 5
    assert obj.numchanges == 5
    assert lastnewvalue == [0]  # should not have changed, since the callback was not invoked.
    assert myvar == [4]



def test_unregistercallback():
    obj = TestClass()
    assert obj.numchanges == 0
    myvar = [0]
    lastnewvalue = [None]
    # need a closure: ? - no, you just need to consume the variables *indirectly*, e.g. as a list.
    def mycallback(newvalue):
        myvar[0] += 2 ## Why is this 'undefined'? Ah, it must be a list...
        lastnewvalue[0] = newvalue
    obj.registerPropertyCallback('MyProp', mycallback)
    obj.MyProp = 4


def test_invokecallback():
    obj = TestClass()
    assert obj.numchanges == 0
    myvar = [0]
    lastnewvalue = [None]
    # need a closure: ? - no, you just need to consume the variables *indirectly*, e.g. as a list.
    def mycallback(newvalue):
        myvar[0] += 2 ## Why is this 'undefined'? Ah, it must be a list...
        lastnewvalue[0] = newvalue

    obj.registerPropertyCallback('MyProp', mycallback)
    obj.numchanges = 4
    assert obj.numchanges == 4
    obj.invokePropertyCallbacks('Nonexistingkey', 5)
    assert lastnewvalue == [None]
    assert myvar == [0]

    obj.invokePropertyCallbacks('MyProp', 6)
    assert obj.numchanges == 4
    assert lastnewvalue == [6]
    assert myvar == [2]

    obj.invokePropertyCallbacks(None, 13)
    assert obj.numchanges == 4
    assert lastnewvalue == [6]
    assert myvar == [2]

    obj.flagPropertyChanged('MyProp')
    # If propkey is None, then newvalue is NOT used (wouldn't make sense)
    # instead, the newvalue is obtained by querying the corresponding property, e.g. 'MyProp'.
    obj.invokePropertyCallbacks(None, 99) # 'MyProp' is
    assert obj.numchanges == 5 # Calling MyProp increments it by 1, from 4 to 5.
    assert lastnewvalue == [5] # newvalue same as MyProp.
    assert myvar == [4]

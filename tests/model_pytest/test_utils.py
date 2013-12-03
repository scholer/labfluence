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
# pylint: disable-msg=C0111

import os
import logging
logger = logging.getLogger(__name__)
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)


##################
### SUT ##########
##################
from model.utils import increment_idx, idx_generator, random_string, getmimetype, getnearestfile, magic_available




def test_increment_idx():
    idxs = ['a', 'RS123a', 1, 'RS123', 'A', 'RS123A', 'RS123a1', 'RS123A1']
    incremented = [increment_idx(i) for i in idxs]
    expected = ['b', 'RS123b', 2, 'RS124', 'B', 'RS123B', 'RS123a2', 'RS123A2']
    assert incremented == expected
    #print "  ".join( "( {}->{} )".format(*pair) for pair in zip(idxs, incremented) )

def test_idx_generator():
    idxs = ['d', 'RS123d', 4, 'RS123', 'D', 'RS123D', 'RS123a4', 'RS123A4']
    expected = [['a', 'b', 'c', 'd'],
                ['RS123a', 'RS123b', 'RS123c', 'RS123d'],
                [1, 2, 3, 4],
                ['RS121', 'RS122', 'RS123'],
                ['A', 'B', 'C', 'D'],
                ['RS123A', 'RS123B', 'RS123C', 'RS123D'],
                ['RS123a1', 'RS123a2', 'RS123a3', 'RS123a4'],
                ['RS123A1', 'RS123A2', 'RS123A3', 'RS123A4']]
    assert [list(idx_generator(idx)) for idx in idxs] == expected

def test_random_string():
    st = random_string(16)
    print "Random string: {}".format(st)
    assert len(st) == 16

def test_getarandomfile():
    fp = getnearestfile()
    print "Random file in/near current directory: {}".format(fp)
    assert fp in os.listdir('.')

def test_getmimetype():
    print "Magic_available: {}".format(magic_available)
    #f = getnearestfile()
    f = 'FUNCTIONALITY.txt'
    t = getmimetype(f)
    print "filepath: {} -- MIMETYPE: {}".format(f, t)
    assert t == 'text/plain'

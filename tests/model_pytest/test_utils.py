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



import logging
logger = logging.getLogger(__name__)
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)






def test_increment_idx():
    idxs = ['a', 'RS123a', 1, 'RS123', 'A', 'RS123A', 'RS123a1', 'RS123A1']
    incremented = [increment_idx(i) for i in idxs]
    print "  ".join( "( {}->{} )".format(*pair) for pair in zip(idxs, incremented) )

def test_idx_generator():
    idxs = ['d', 'RS123d', 4, 'RS123', 'D', 'RS123D', 'RS123a4', 'RS123A4']
    print "\n".join( "{}: {}".format(idx, list(idx_generator(idx))) for idx in idxs )

def test_random_string():
    print "Random string: {}".format(random_string(16))

def test_getarandomfile():
    print "Random file in/near current directory: {}".format(getnearestfile())

def test_getmimetype():
    print "Magic_available: {}".format(magic_available)
    f = getnearestfile()
    print "filepath: {}".format(f)
    print "filetype: {}".format(getmimetype(f))


#test_increment_idx()
#test_idx_generator()
#test_random_string()
#test_getarandomfile()
#test_getmimetype()
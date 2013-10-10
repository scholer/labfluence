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

import os
import yaml
import re
import random
import string
try:
    import magic
    magic_available = True
    if hasattr(magic, 'MAGIC_MIME_TYPE'):
        magic_is_old = True
    else:
        magic_is_old = False
except ImportError:
    magic_available = False
    magicmime = None
    print "Notice: magic module is not available; mimetypes will be based on file extensions. See http://pypi.python.org/pypi/python-magic/ for info on installing the filemagic python module."
    import mimetypes


def getmimetype(filepath):
    if magic_available:
        if magic_is_old:
            with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
                mimetype = m.id_filename(filepath)
        else:
            with magic.Magic(mime=True) as m:
                mimetype = m.from_file(filepath)
    else:
        mimetype = mimetypes.guess_type(filepath)
    return mimetype

def increment_idx(idx):
    if isinstance(idx, int):
        return idx+1
    if isinstance(idx, basestring):
        return idx[:-1]+chr(ord(idx[-1])+1)

def idx_generator(start, idx=None, maxruns=100):
    """
    Returns a generator, very similar to if you could do xrange('a','d')
    One important difference against range, though:
    1) index starts at 'a' or optionally 1.
    2) range INCLUDES the final index, e.g. idx_generator('d') -> ['a','b','c','d']
    """
    if idx is None:
        idx = start
        if isinstance(idx, basestring):
            if ord(idx[-1]) >= ord('a'):
                start = 'a'
            elif ord(idx[-1]) >= ord('A'):
                start = 'A'
            else:
                start = '1'
            i = idx[:-1]+start
        elif isinstance(idx, int):
            start = 1
            i = start
        else:
            print "idx_generator() :: Fatal error, could not determine start; aborting..."
            raise StopIteration
    for run in xrange(maxruns):
        yield i
        if i == idx:
            break
        i = increment_idx(i)


def random_string(length, uppercase=True, lowercase=True, digits=True, punctuation=False, whitespace=False, ascii=True, allprintable=False, custom=None):
    chars = ""
    if allprintable:
        chars += string.printable
    else:
        if uppercase:
            chars += string.ascii_uppercase if ascii else string.uppercase
        if lowercase:
            chars += string.lowercase if ascii else string.lowercase
        if digits:
            chars += string.digits
        if punctuation:
            chars += string.punctuation
        if whitespace:
            chars += string.whitespace
    if custom:
        chars += custom
    return "".join( random.sample(chars, length) )

def getnearestfile(startpath=None):
    if startpath is None:
        startpath = os.getcwd()
    if os.path.isfile(startpath):
        return startpath
    for dirpath, dirnames, filenames in os.walk(startpath):
        if filenames:
            return os.path.join(dirpath, filenames[0])
    def walkup(startpath):
        parpath = os.path.dirname(startpath)
        print "walkup:\n--startpath: {}\n--parpath:{}".format(startpath, parpath)
        if parpath == startpath:
            print "startpath '{}' == parpath '{}'".format(startpath, parpath)
            return None
        for f in os.listdir(parpath):
            if os.path.isfile(os.path.join(parpath, f)):
                print "'{}' is file, returning it...".format(f)
                return f
            else:
                print "'{}' is not a file...".format(f)
        return walkup(parpath)
    return walkup(startpath)



if __name__ == '__main__':
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


    test_increment_idx()
    test_idx_generator()
    test_random_string()
    test_getarandomfile()
    test_getmimetype()

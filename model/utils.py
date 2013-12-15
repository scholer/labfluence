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

from __future__ import print_function
import os
import sys
import random
import string
import logging

# Uh, this makes "from utils import *" a bit dangerous:
# it will override any 'logger' variables in the calling modules.
logger = logging.getLogger(__name__)

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
    logger.info("Notice: magic module is not available; mimetypes will be based on file extensions. See http://pypi.python.org/pypi/python-magic/ for info on installing the filemagic python module.")
    import mimetypes


def getmimetype(filepath):
    """
    Returns the mime type of a file, using the best
    methods available on the current installation.
    """
    if magic_available:
        if magic_is_old:
            with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
                mimetype = m.id_filename(filepath)
        else:
            with magic.Magic(mime=True) as m:
                mimetype = m.from_file(filepath)
    else:
        # mimetypes.guess_type returns
        mimetype, encoding = mimetypes.guess_type(filepath, strict=False)
    return mimetype

def increment_idx(idx):
    """
    Take an index, e.g. 1 or 'a' and increment it to the
    next logical value, e.g. 2 or 'b'.
    """
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
    USAGE:
        idx_generator('d') -> generator('a', 'b', 'c', 'd')
        idx_generator('b', 'f') -> generator('b', 'c', 'd', 'e', 'f')
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
            logger.error("idx_generator() :: Fatal error, could not determine start; aborting...")
            raise StopIteration
    for run in xrange(maxruns):
        yield i
        if i == idx:
            break
        i = increment_idx(i)


def random_string(length, uppercase=True, lowercase=True, digits=True, punctuation=False, whitespace=False, ascii=True, allprintable=False, custom=None):
    """
    Returns a random string of length <length> consisting of
    the specified character types:
        uppercase, lowercase, digits,
        punctuation,
        whitespace.
    ascii flag ensures that only ASCII characters are included.
    (i.e. using string.ascii_uppercase rather than string.uppercase)
    allprintable = string.printable.
    if custom is defined, then the values in custom are appended
    to the list of used characters.
    Note: Currently just uses the default random library, but
    could be easily adjusted to use a better library, e.g. the
    one from the crypto library.
    """
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
    """
    Given a start path, return a random file close to that starting point.
    """
    if startpath is None:
        startpath = os.getcwd()
    if os.path.isfile(startpath):
        return startpath
    for dirpath, dirnames, filenames in os.walk(startpath):
        if filenames:
            return os.path.join(dirpath, filenames[0])
    def walkup(startpath):
        parpath = os.path.dirname(startpath)
        logger.debug("walkup:\n--startpath: {}\n--parpath:{}".format(startpath, parpath))
        if parpath == startpath:
            logger.debug("startpath '{}' == parpath '{}'".format(startpath, parpath))
            return None
        for f in os.listdir(parpath):
            if os.path.isfile(os.path.join(parpath, f)):
                logger.debug("'{}' is file, returning it...".format(f))
                return f
            else:
                logger.debug("'{}' is not a file...".format(f))
        return walkup(parpath)
    return walkup(startpath)


def login_prompt(username=None, msg="", options=None ):
    """
    The third keyword argument, options, can be modified in-place by the login handler,
    changing e.g. persistance options ("save in memory").
    """
    import getpass
    if options is None:
        options = dict()
    if username is None:
        username = getpass.getuser() # returns the currently logged-on user on the system. Nice.
    print("\n{}\nPlease enter credentials:".format(msg), file=sys.stderr)
    username = raw_input('Username (enter={}):'.format(username)) or username # use 'username' if input is empty.
    password = getpass.getpass()
    logger.debug("login_prompt returning username '%s' and password of length {}".format(username, "0" if len(password) < 1 else ">0"))
    return username, password

def display_message(message):
    """Simply prints a message to the user, making sure to properly format it."""
    print( "\n".join("\n\n", "-"*80, message, "-"*80, "\n\n") )




if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

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
# pylint: disable-msg=W0612
"""
Module with various utility functions.
"""


from __future__ import print_function
import os
import sys
import random
import xmlrpclib
import string
import logging

# Uh, this makes "from utils import *" a bit dangerous:
# it will override any 'logger' variables in the calling modules.
# Thus, never do "from utils import *" !
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
    for _ in xrange(maxruns):
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



def findFieldByHint(candidates, hints):
    """
    Takes a list of candidates, e.g.
        ['Pos', 'Sequence', 'Volume']
    and a hint, e.g. 'seq' or a (prioritized!) list of hints, e.g.
        ('sequence', 'seq', 'nucleotide code')
    and returns the best candidate matching the (case-insensitive)
    hint(s) e.g. for the above arguments, returns 'Sequence'.
    If more than one hint is given, the first hint that yields a
    resonable score will be used. In other words, this function will
    NOT screen ALL hints and use the best hint, but only use the next
    hint in the sequence if the present hint does not yield a resonable
    match for any of the candidates.
    Thus, the hints can be provided with decreasing level of specificity,
    e.g. start with very explicit hints and end with the last acceptable
    hint, e.g. the sequence: ('Well position', 'Rack position', 'Position', 'Well Pos', 'Well', 'Pos')
    If no candidates are suited, returns None.

    """
    if not isinstance(hints, (list, tuple)):
        hints = (hints,)
    def calculate_score(candidate, hint):
        """
        Compares a candidate and hint and returns a score.
        This is not intended to be "align" based, but should return
        a "probability like" value for the change that the candidate
        is the right choice for the hint.
        """
        score = 0
        if candidate in hint:
            # candidate is 'seq' and hint is 'sequence'
            # However, we do not want the hint 'Rack position' to yield
            # high score for the candidate e.g. 'Rack name', nor do we want
            # 'sequence' to yield a high score for the field 'sequence name'
            score += 0.1 + float(len(candidate))/len(hint)
        if hint in candidate:
            score += 1 + float(len(hint))/len(candidate)
        return score
    for hint in hints:
        scores = [ calculate_score(candidate.lower(), hint.lower()) for candidate in candidates ]
        #print "="
        scores_list = ["{} ({:.3f})".format(cand, score) for cand, score in zip(candidates, scores)]
        #print scores_list
        scores_str = ", ".join( scores_list )
        #print scores_str
        #print "--------"
        # do NOT attempt to use u"string" here, doesn't work?
        logger.debug("Candidate scores for hint '%s': %s" , hint, scores_str)
        if max(scores) > 0.2:
            return candidates[scores.index(max(scores))]
        #for candidate in candidates:
        #    if hint in candidate.lower():
        #        return candidate
    # None of the hints were found in either of the options.
    return None


def attachmentTupFromFilepath(filepath):
    """
    Creates attachment struct and binary data object
    for use with addAttachment method via the confluence2 xmlrpc API.
    Used in e.g. server, experiment, page and limspage.
    """
    filename = os.path.basename(filepath)
    mimetype = getmimetype(filepath)
    # Note: comment not required, I believe.
    attInfo = dict(fileName=filename, contentType=mimetype)
    with open(filepath, 'rb') as fd:
        #attData = base64.b64encode(fd.read('rb'))
        # xmlrpclib.Binary also does base64.encode, but adds xml tag before and after.
        attData = xmlrpclib.Binary(fd.read())
    logging.debug("Read data for attachment '%s' with byte-length %s.", attInfo, len(str(attData)))
    return attInfo, attData


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

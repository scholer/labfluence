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
# pylint: disable-msg=W0612,C0103
"""
Module with various utility functions.
"""


from __future__ import print_function
import os
import sys
import random
import string
import hashlib
import re
import logging
from datetime import datetime
try:
    import xmlrpc.client as xmlrpclib
except ImportError:
    import xmlrpclib


# Uh, this makes "from utils import *" a bit dangerous:
# it will override any 'logger' variables in the calling modules.
# Thus, never do "from utils import *" !
logging.addLevelName(4, 'SPAM') # Will convert LEVEL to 'SPAM' when printing logs for lvl 4, logger.log(4, msg, *args)
logger = logging.getLogger(__name__)

try:
    import magic        # pylint: disable=F0401
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.info("Notice: magic module is not available; mimetypes will be based on file extensions. See http://pypi.python.org/pypi/python-magic/ for info on installing the filemagic python module.")
    import mimetypes

try:
    # ASCII large-font print driver:
    import pyfiglet
    from pyfiglet import Figlet
except ImportError:
    Figlet = None


def print_figlet(text, **kwargs):
    """
    Print text with figlet font.
    There is also
    """
    if Figlet is None:
        logger.warning("pyfiglet module not available.")
        print(text)
        return
    pyfiglet.print_figlet(text) # This will print and not actually return anything.

def figlet_header(text, font='colossal', smushMode=None):
    """
    Prints text with ascii print driver.
    See available fonts with Figlet().getFonts()
    or pyfiglet.FigletFont.getFonts()
    Easy-to-read fonts include:
    * Doh       (very big)
    * Banner3   (Exclusively using '#')
    * Block     (rather subtil)
    * Colossal  (Easy to read, but set smushMode to 64 or lower for headers)
    * Georgia11 (Very elegant)
    * Roman
    * Univers
    """
    if Figlet is None:
        logger.warning("pyfiglet module not available.")
        return
    ## TODO: Add labfluence settings option to change font, etc.
    f = Figlet(font=font)
    if smushMode is not None:
        # pyfiglet default smushMode is calculated by pyfiglet.FigletFont.loadFont()
        # For some, e.g. colossal, the resulting smushMode of 128 smushes the characters a bit too much.
        # I've made a fork of pyfiglet where you can adjust smushMode directly
        # when instantiating a Figlet via argument fontkwargs.
        f.Font.smushMode = smushMode
    return f.renderText(text)






def getmimetype(filepath):
    """
    Returns the mime type of a file, using the best
    methods available on the current installation.
    """
    if MAGIC_AVAILABLE:
        if hasattr(magic, 'MAGIC_MIME_TYPE'):
            # Old magic module:
            with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as mimeprober:
                mimetype = mimeprober.id_filename(filepath)
        else:
            with magic.Magic(mime=True) as mimeprober:
                mimetype = mimeprober.from_file(filepath)
    else:
        # mimetypes.guess_type returns
        mimetype, encoding = mimetypes.guess_type(filepath, strict=False)
    return mimetype

def asciize(s):
    """ Return string s with all non-ascii chars removed """
    proper_letters = string.ascii_letters+string.digits+"().-_"
    return "".join(c for c in s if c in proper_letters)


def filehexdigest(filepath, digesttype='md5'):
    """
    Reference implementation. Returns hex digest of file in filepath.
    """
    with open(filepath, 'rb') as fd:
        m = hashlib.new(digesttype) # generic; can also be e.g. hashlib.md5()
        # md5 sum default is 128 = 2**7-bytes digest block. However, file read is faster for e.g. 8 kb blocks.
        # http://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
        for chunk in iter(lambda: fd.read(128*m.block_size), b''):
            m.update(chunk)
    return m.hexdigest()



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


def isvalidfilename(fileName):
    """
    Checks whether fileName is valid.
    Returns True if ok and false otherwise.
    """
    validchars = string.letters + string.digits + "_ .-"
    return all(c in validchars for c in fileName)

def getvalidfilename(fileName):
    """
    Checks whether fileName is valid.
    Returns True if ok and false otherwise.
    """
    validchars = string.letters + string.digits + "_ .-"
    replacement = "_"
    return "".join(c if c in validchars else replacement for c in fileName)


def random_string(length, uppercase=True, lowercase=True, digits=True, punctuation=False,   # pylint: disable=R0913
                  whitespace=False, ascii=True, allprintable=False, custom=None):
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
    return "".join(random.sample(chars, length))

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
        """ Recursively walk up the file hierarchy until a file is found. """
        parpath = os.path.dirname(startpath)
        logger.debug("startpath: %s, parpath: %s", startpath, parpath)
        if parpath == startpath:
            logger.debug("startpath '%s' == parpath '%s'", startpath, parpath)
            return None
        for f in os.listdir(parpath):
            if os.path.isfile(os.path.join(parpath, f)):
                logger.debug("'%s' is file, returning it...", f)
                return f
            else:
                logger.debug("'%s' is not a file...", f)
        return walkup(parpath)
    return walkup(startpath)


def login_prompt(username=None, msg="", options=None):
    """
    The third keyword argument, options, can be modified in-place by the login handler,
    changing e.g. persistance options ("save in memory").
    """
    import getpass
    if options is None:
        options = dict()
    if username is None:
        username = getpass.getuser() # returns the currently logged-on user on the system. Nice.
    print(u"\n{}\nPlease enter credentials:".format(msg), file=sys.stderr)
    username = raw_input('Username (enter={}):'.format(username)) or username # use 'username' if input is empty.
    password = getpass.getpass()
    logger.debug("login_prompt returning username '%s' and password of %s length.", username, "non-zero" if len(password) > 0 else "zero")
    return username, password

def display_message(message):
    """Simply prints a message to the user, making sure to properly format it."""
    print("\n".join("\n\n", "-"*80, message, "-"*80, "\n\n"))



def findFieldByHint(candidates, hints, regex=False):
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
    if regex:
        regexs = {hint: re.compile(hint, re.IGNORECASE) for hint in hints}
    def calculate_score(candidate, hint):
        """
        Compares a candidate and hint and returns a score.
        This is not intended to be "align" based, but should return
        a "probability like" value for the change that the candidate
        is the right choice for the hint.
        """
        score = 0
        if regex:
            match = regexs[hint].match(candidate)
            if match:
                return len(candidate)
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
        scores = [calculate_score(candidate.lower(), hint.lower()) for candidate in candidates]
        #print "="
        scores_list = [u"{} ({:.3f})".format(cand, score) for cand, score in zip(candidates, scores)]
        #print scores_list
        scores_str = ", ".join(scores_list)
        #print scores_str
        #print "--------"
        # do NOT attempt to use u"string" here, doesn't work?
        logger.log(4, "Candidate scores for hint '%s': %s", hint, scores_str)
        if max(scores) > 0.2:
            return candidates[scores.index(max(scores))]
        #for candidate in candidates:
        #    if hint in candidate.lower():
        #        return candidate
    # None of the hints were found in either of the options.
    return None

def getNewFilename(basename, used_filenames, caseinsensitive=False,
                   fnfmt=u"{fname}{num:0{p}}{ext}", powerrange=(2,)):
    """
    Returns a new filename based on basename that is not in used_filenames.
    If caseinsensitive is set to True (e.g. for windows filesystems),
    filename candidates are matched against used_filenames in a case-insensitive manner.
    the powerrange specifies the ranges to use for making new file names,
    will be used in a manner of "for p in powerrange for i in xrange(1,10**p)".
    Note that specifying more than one value in power-range only makes sense if
    the fnfmt has a p-dependent number specifier.
    If several p values are given in powerrange and p is in the fnfmt, you can generate
    different filename patterns, e.g. for powerrange=(1,2):
        filename1, filename2, ... filename9, filename01, filename02, .., filename10, filename11, .., filename99
    The fnfmt argument can be used to change the output filename format:
    Example: getNewFilename('newfile.txt', fnfmt="{fname}_{num:0{p}}.{ext}"):
        fname is 'newfile', ext is 'txt', num is the number being tried,
        the second fnfmt.format candidate is something like: newfile_02.txt
    If you do not want to use a fix-width number format, just alter fnfmt to something like:
        fnfmt="{fname}{num}.{ext}"  # Notice how ':0{p}' was removed.

    """
    if caseinsensitive:
        used_filenames = {fn.lower() for fn in used_filenames}
        if basename.lower() not in used_filenames:
            return basename
    else:
        if basename not in used_filenames:
            return basename
    def fmt(fn, num, p=2):
        """
        For making a new filename based on fnfmt and input vars, where:
        fn=filename, i=index, p=power 10 (default: 2)
        """
        fname, ext = os.path.splitext(fn)
        return fnfmt.format(fname=fname, ext=ext, num=num, p=p)

    # for windows style, do:
    # use for p in xrange(1,9) for i in range(1,10^p)
    # and pass p to fmt as the length.
    # and make sure to cast to lower when checking.
    for p in powerrange:
        fngen = (fmt(basename, i) for i in xrange(1, 10**p))
        if caseinsensitive:
            newfn = next((fn for fn in fngen if fn.lower() not in used_filenames), None)
        else:
            newfn = next((fn for fn in fngen if fn not in used_filenames), None)
        if newfn:
            return newfn


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
        # Remember to open file in binary mode, otherwise you'll get padding errors (and wrong data).
        # xmlrpclib.Binary also does base64.encode, but adds xml tag before and after.
        attData = xmlrpclib.Binary(fd.read())
    logger.debug("Read data for attachment '%s' with byte-length %s.", attInfo, len(str(attData)))
    return attInfo, attData

def yaml_xmlrpcdate_representer(dumper, data):
    """
    Used to represent (/serialize/dump) xmlrpclib.DateTime objects;
    by storing them as datetime.datetime objects.
    Based on dice_representer example from http://pyyaml.org/wiki/PyYAMLDocumentation
    Example dumper object can be generated with: dumper = yaml.Dumper(sys.stdout)
    Example xmlrpclib.DateTime objects may be generated with:
        data = xdt = xmlrpclib.DateTime(time.localtime())
    use as:
        yaml.add_representer(xmlrpclib.DateTime, yaml_xmlrpcdate_representer)
    """
    # convert xmlrpclib.DateTime object to datetime object:
    dt = datetime(*data.timetuple()[:6])
    logger.debug("%s (%s object) was converted to %s (%s object)",
                 repr(data), data.__class__, repr(dt), dt.__class__)
    # alternatively:
    # dt = datetime.fromtimestamp(mktime(v.timetuple() ))
    # return the dumper's standard datetime representation:
    return dumper.represent_datetime(dt)



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

#!/usr/bin/env python3
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
# pylint: disable-msg=W0612,C0103,C0301

from __future__ import print_function
import sys

import logging
logger = logging.getLogger(__name__)
try:
    # Python 2 compatability:
    input = raw_input # pylint: disable=W0622,E0602
except NameError:
    pass

def display_message(message):
    """Simply prints a message to the user, making sure to properly format it."""
    print("\n".join("\n\n", "-"*80, message, "-"*80, "\n\n"))

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
    username = input('Username (enter={}):'.format(username)) or username # use 'username' if input is empty.
    password = getpass.getpass()
    logger.debug("login_prompt returning username '%s' and password of %s length.", username, "non-zero" if len(password) > 0 else "zero")
    return username, password

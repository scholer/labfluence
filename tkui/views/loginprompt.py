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
# pylint: disable-msg=R0924

"""
Created by Rasmus S. Sorensen <rasmusscholer@gmail.com>



"""


# python 3.x:
#from tkinter import ttk
# python 2.7:
import Tkinter as tk

from collections import OrderedDict
import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

from dialogs import Dialog


class LoginPrompt(Dialog):
    """

    fieldvars is an OrderedDict of <key> = <speclist> items,
    and <speclist> is a 2-4 item list of:
        [tk-variable, label-text, widget-kwargs, widget]

    """

    def __init__(self, parent, title = None, fieldvars = None, username='', msg=None):
        self.Initial_username = username # super's __init__ calls body, which depends on this.
        Dialog.__init__(self, parent, title, fieldvars, msg=msg)

    def body(self, master):
        if not self.Fieldvars:
            logger.debug("Creating username and password tk StringVars Fieldvars. Initial username is: %s", self.Initial_username)
            # Notice: you should specify the variables' master; otherwise, if you instantiate
            # multiple tk.Tk() instances during e.g. testing, these will
            # mess up the variable logic (apparently...)
            self.Fieldvars = OrderedDict(
                username = [tk.StringVar(self.parent, value=self.Initial_username), 'Username', dict()],
                password = [tk.StringVar(self.parent), 'Password', dict(show="*")]
                )
        # Call to super:
        Dialog.body(self, master)
        logger.debug("login prompt created, self.Fieldvars is: %s, with values: %s",
                     self.Fieldvars,
                     "; ".join(u"{}: {}".format(k, bool(v[0].get())) for k, v in self.Fieldvars.items()))
        logger.debug("self.EntryWidgets have values: %s",
                     "; ".join(u"{}: {}".format(k, bool(v.get())) for k, v in self.EntryWidgets.items()))

    def validate(self):
        """
        Validate the values of the entry widgets.
        Should be overridden by subclasses.
        """
        if all( self.Fieldvars[key][0].get() for key in ('username', 'password') ):
            logger.debug("All fields are ok.")
            return 1
        else:
            logger.info("Input error, empty field: %s", "username" if not self.Fieldvars['username'][0].get() else "password")
            return 0

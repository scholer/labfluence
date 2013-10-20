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

# Tkinter import:
import Tkinter as tk
import ttk

# Other standard lib modules:
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

from Tkinter import *
import os

class Dialog(tk.Toplevel):
    """
    From http://effbot.org/tkinterbook/tkinter-dialog-windows.htm
    Base-class for advanced dialogs.
    Modified to make it easier to inject variables into the dialog
    which allows automatic widget/layout creation.
    The fieldsvar is a an ordered dict of two-item lists
    (could also have been a list of 3-item lists).
    #items are: variable, description, entry widget, kwargs for widget
    edit, just: variable, description, kwargs for widget, widget
    -- widget is currently not used but determined automatically by value.
    Alternatively, the validate/apply methods will also store results
    in self.result.
    The default is that the vars provided in fieldvars OrderedDict,
    while the result is strings data.

    This baseclass is purposedly designed for maximal versatility.
    You'll probably want to subclass this and reduce functionality.

    """
    def __init__(self, parent, title = None, fieldvars = None):
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        if title:
            self.title(title)
        self.parent = parent
        self.Fieldvars = fieldvars
        self.result = None

        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        #body.pack(padx=5, pady=5)
        body.grid(row=1, column=0, sticky="news")
        self.buttonbox()
        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50))
        self.initial_focus.focus_set()
        self.wait_window(self)

    #
    # construction hooks
    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        if not self.Fieldvars:
            return
        focusentry = None
        r = 1
        c = 0
        # speclist: var, desc, kwargs
        for key,speclist in self.Fieldvars.items():
            if isinstance(speclist[0], (tk.BooleanVar, )):
                if c > 1: c = 0; r += 1
                e = ttk.Checkbutton(master, variable=speclist[0], text=speclist[1], **speclist[2])
                e.grid(row=r, column=c)
                c += 1
            else:
                if c > 0: r += 1
                c = 0
                l = tk.Label(master, text=speclist[1])
                l.grid(row=r, column=c, sticky="w")
                e = ttk.Entry(master, textvariable=speclist[0], **speclist[2])
                e.grid(row=r, column=c+1, sticky="nesw")
                r += 1
            if focusentry is None:
                focusentry = e
        return focusentry

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons
        box = tk.Frame(self)
        w = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        box.grid(row=2, column=0, sticky="news")
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    #
    # standard button semantics
    def ok(self, event=None):
        if not self.validate(): # validate is in charge of displaying message to the user
            self.initial_focus.focus_set() # put focus back
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()

    def cancel(self, event=None):
        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks
    def validate(self):
        return 1 # override

    def apply(self):
        self.result = dict( (key, speclist[0].get()) for key,speclist in self.Fieldvars.items() )

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
# pylint: disable-msg=R0924,C0321
## pylint messages: C0321="Multiple statements per line"

"""
Contains basic tkinter dialogs.

"""


# Tkinter import:
import Tkinter as tk
import ttk

# Other standard lib modules:
import logging
logger = logging.getLogger(__name__)


class Dialog(tk.Toplevel):
    """
    Base-class for advanced dialogs.
    Based on example from:
        http://effbot.org/tkinterbook/tkinter-dialog-windows.htm
    But modified to make it easier to inject variables into the dialog
    which allows automatic widget/layout creation.

    Use as:
        dia = Dialog(tk_parent, title, fieldvars)
    where:
        fieldvars is an OrderedDict of <key> = <speclist> items,
    and <speclist> is a 2-4 item list of:
        [tk-variable, label-text, widget-kwargs, widget]
    (since the items of speclist are mutable, do not try to pass a tuple...)
    Note: The widget parameter is currently not used but determined
    automatically by the type/value of the variable.

    When the user presses 'ok', the validate() is invoked and then,
    if that suceeds, apply(). apply() stores the values of the Fieldvars widgets
    in dia.result (as strings).

    Note that if the caller stores a reference to the fieldvars OrderedDict
    then the user input can also be obtained directly from the tk Variables
    passed in the fieldvars argument.

    This base class is purposedly designed for maximal versatility.
    You'll probably want to subclass this and reduce the dialog complexity
    for better readability.

    """
    def __init__(self, parent, title = None, fieldvars = None, msg = None):
        if isinstance(msg, basestring):
            self.Message = tk.StringVar(value=msg)
        else:
            self.Message = msg
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        if title:
            self.title(title)
        self.parent = parent
        self.Fieldvars = fieldvars
        self.EntryWidgets = dict() # key = widget dict.
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
        self.wait_window(self) # Will wait other things until the window is destroyed.

    #
    # construction hooks
    def body(self, master):
        """
        create dialog body.  return widget that should have
        initial focus.
        This method can/should be overridden by children deriving from this class.
        Uses self.Fieldvars attribute, a <key> = <speclist> ordered dict,
        where <speclist> = (tk-variable, label-text, widget-kwargs, widget)
        """
        if self.Message is not None:
            l = tk.Label(master, textvariable=self.Message)
            l.grid(row=0, column=0, sticky="news")
        if not self.Fieldvars:
            logging.info("No self.Fieldvars, aborting")
            return
        focusentry = None
        r, c = 1, 0
        # speclist: var, desc, kwargs
        for key, speclist in self.Fieldvars.items():
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
                e = self.EntryWidgets[key] = ttk.Entry(master, textvariable=speclist[0], **speclist[2])
                logging.debug("Created ttk.Entry widget with textvariable.get()='%s' and entry.get()='%s'",
                              speclist[0].get(), e.get())
                e.grid(row=r, column=c+1, sticky="nesw")
                r += 1
            if focusentry is None:
                focusentry = e
        return focusentry

    def buttonbox(self):
        """
        Add standard button box.
        Override if you don't want the standard buttons
        """
        box = tk.Frame(self)
        w = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        box.grid(row=2, column=0, sticky="news")
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    #
    # standard button semantics
    def ok(self, event=None):
        """invoked when the users presses the 'ok' button."""
        if not self.validate(): # validate is in charge of displaying message to the user
            self.initial_focus.focus_set() # put focus back
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()

    def cancel(self, event=None):
        """invoked when the users presses the 'cancel' button."""
        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks
    def validate(self):
        """
        Validate the values of the entry widgets.
        Should be overridden by subclasses.
        """
        return 1

    def apply(self):
        """
        Stores the values of all tk Vars in self.Fieldvars in self.result.
        Can be overridden by subclasses.
        """
        self.result = dict( (key, speclist[0].get()) for key, speclist in self.Fieldvars.items() )

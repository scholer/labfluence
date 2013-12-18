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
import ttk

from collections import OrderedDict
#import os
#from datetime import datetime

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

#from views.dialogs import Dialog
from views.loginprompt import LoginPrompt
#from model.utils import findFieldByHint


class LimsTkRoot(tk.Tk):
    """
    LIMS app tk root.
    """

    def __init__(self, app, confighandler, fields=None):
        """
        Uh, boot strapping issue:
        - I need the initialized UI in order to have a login prompt available.
        - I need the server to obtain LIMS table info to initialize fields.
        - I need a login prompt to connect to server. :-\
        """
        tk.Tk.__init__(self)
        self.App = app
        self.Message = tk.StringVar(value='') # use None to not create a message label.
        self.Confighandler = confighandler
        self.Confighandler.Singletons.setdefault('ui', self)
        self.EntryWidgets = dict() # key = widget dict.
        # fields: key=header
        self.Fields = fields
        self.init_ui()


    def init_ui(self, ):
        """
        Initialize the UI widgets. Refactored to separate method,
        since the tkroot UI might be required before
        information on the widgets are available.
        """
        if self.Fields:
            logger.debug("init_ui -> calling init_fieldvars...")
            raw_input("en prompt for at stoppe...(A)")
            self.init_fieldvars()
            #self.iconify() # makes the window an icon. http://effbot.org/tkinterbook/wm.htm
            #self.withdraw() # removes window from screen.
            # Note that these are for the whole app, not just a single toplevel window
            logger.debug("init_ui -> calling init_widgets...")
            raw_input("en prompt for at stoppe...(B)")
            self.init_widgets() # This is the call that makes the form collapse.
        #self.init_layout()
        #self.init_bindings()
        else:
            logger.debug("init_ui -> no self.Fields, so just calling grid and update...")
            #self.grid()
            #self.update()
        logger.debug("init_ui complete, asking for user input.\n")
        #input("her er lige en prompt for at stoppe...")
        raw_input("en prompt for at stoppe...")
        # the first time this is called, self.Fields is false, and the tk form appears blank at this point.
        # the next time this method is called, the form has collapsed.


    def init_fieldvars(self, fields=None):
        """
        Fieldvars, similar to those used by dialog.Dialog class.
        is a key = speclist ordered dict, where speclist is:
        [tk-variable, label-text, widget-kwargs, widget]
        If widget is None, a tk.Entry widget is used (except if tk-variable is BooleanVar)
        If label-text is None, key is used (capitalized first letter).
        **widget-kwargs is passed to the widget. If this is none, it defaults to

        Note: The fieldvars should probably be provided by the confighandler.
        """
        if fields is None:
            fields = self.Fields

        self.Fieldvars = OrderedDict(
            ( key, [tk.StringVar(value=value), key, dict(), None] )
                for key, value in fields.items()
            )


    #def lims_dialog_single(self, ):
    #    """
    #    opens a dialog to the user to obtain lims information on a single entry.
    #    """
    #    dia = Dialog(self, fieldvars=self.Fieldvars)
    #    try:
    #        logger.info("dia.results: %s", dia.result)
    #    except AttributeError:
    #        logger.info("dialog returned without result.")


    def init_widgets(self, ):
        """ Initialize widgets """
        # Make top message.
        if self.Message is not None:
            logger.debug("Creating message...")
            # Argh, this was the cullpit: adding something without having a frame.
            #l = tk.Label(self, textvariable=self.Message)
            #l.grid(row=0, column=0, sticky="news")

        raw_input("en prompt for at stoppe...(9)") # allerede her er den kollapset.
        body = tk.Frame(self)
        raw_input("en prompt for at stoppe...(10)")
        self.initial_focus = self.body(body) # body returns the entry widget that should have initial focus.
        raw_input("en prompt for at stoppe...(C)") # her er den kollapset.
        #body.pack(padx=5, pady=5)
        body.grid(row=1, column=0, sticky="news")
        raw_input("en prompt for at stoppe...(D)")
        self.buttonbox()
        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.initial_focus.focus_set()
        raw_input("en prompt for at stoppe...(E)")


    def body(self, master):
        """
        create dialog body using master (frame).
        return widget that should have initial focus.
        This method can/should be overridden by children deriving from this class.
        Uses self.Fieldvars attribute, a <key> = <speclist> ordered dict,
        where <speclist> = [tk-variable, label-text, widget-kwargs, widget]
        Note: speclist is mutable and therefore not a tuple.
        """

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
            if focusentry is None and not speclist[0].get():
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
        self.App.add_entry()
        #self.cancel()

    def cancel(self, event=None):
        """invoked when the users presses the 'cancel' button."""
        # put focus back to the parent window
        #self.parent.focus_set()
        #self.destroy()
        self.App.next_entry()

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
        self.result = self.get_result()
        #self.Resultslist.append(self.result)


    def get_result(self, ):
        """
        Returns the current fieldvars values.
        """
        return dict( (key, speclist[0].get()) for key, speclist in self.Fieldvars.items() )



    def login_prompt(self, username=None, msg=None, options=None):
        """
        Creates a login prompt asking for username and password, which are returned.
        """
        dia = LoginPrompt(self, "Please enter credentials",
                          username=username, msg=msg)
        #return dia.result
        if dia.result:
            logger.info("Dialog has result, returning username and password.")
            return dia.result['username'], dia.result['password']
        else:
            logger.info("dia.result is: %s", dia.result)
            return None, None

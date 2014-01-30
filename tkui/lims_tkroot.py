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
# pylint: disable-msg=R0924,C0321,W0613
"""
Created by Rasmus S. Sorensen <rasmusscholer@gmail.com>



"""


# python 3.x:
#from tkinter import ttk
# python 2.7:
import Tkinter as tk
import tkMessageBox
import ttk

from collections import OrderedDict
#import os
#from datetime import datetime

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)

#from views.dialogs import Dialog
from views.loginprompt import LoginPrompt
from fontmanager import FontManager # Instantiating this will also create a couple of named fonts.
from views.shared_ui_utils import HyperLink
#from model.utils import findFieldByHint


class LimsTkRoot(tk.Tk):
    """
    LIMS app tk root.
    """

    def __init__(self, app, confighandler, fields=None, title=None):
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
        self.Fontmanager = FontManager()
        # fields: key=header
        self.Fields = fields
        persisted_windowgeometry = self.Confighandler.get('limsapp_tk_window_geometry', None)
        if persisted_windowgeometry and False:
            logger.debug("Setting window geomerty: %s", persisted_windowgeometry)
            try:
                self.geometry(persisted_windowgeometry)
            except tk.TclError as e:
                logger.info("Error setting window geomerty: %s", e)
        self.init_ui()
        if title:
            self.title(title)


    def init_ui(self, ):
        """
        Initialize the UI widgets. Refactored to separate method,
        since the tkroot UI might be required before
        information on the widgets are available.
        """
        if self.Fields:
            logger.debug("init_ui -> calling init_fieldvars...")
            self.init_fieldvars()
            logger.debug("init_ui -> calling init_widgets...")
            self.init_widgets()
            logger.debug("init_ui complete, asking for user input.")
        else:
            logger.debug("init_ui -> no self.Fields, you have to call init_ui again when these are available...")


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
        """
        Initialize widgets:
         ------------------------------------
        |                                    |
        |                                    |
        |                                    |
        |                                    | << body frame
        |                                    |
        |                                    |
        |                                    |
        |                                    |
         ------------------------------------
        |  _________   __________   ______   |
        | |OK (Keep)| |OK (Clear)| |Cancel|  | << buttonbox frame
        |  ¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨¨¨¨¨   ¨¨¨¨¨¨   |
         ------------------------------------
        |  Enter=OK, Shift-enter=OK (keep),  |
        |  Added entry: "<product name>"     | << Info frame
        |  View page in browser              |
         ------------------------------------
        """
        ## BODY FRAME: ##
        body = tk.Frame(self)
        self.initial_focus = self.body(body) # body returns the entry widget that should have initial focus.
        body.grid(sticky="news") # row=1, column=0, - now implicit...

        ## BUTTON FRAME: ##
        self.buttonbox()
        if not self.initial_focus:
            logger.info("No initial_focus widget; setting initial focus widget to self.")
            self.initial_focus = self

        ## INFO FRAME: ##
        # Adding the label directly to root without having a frame caused
        # "collapse" issue, so always using a frame from now on.
        self.Infoframe = f = tk.Frame(self)
        f.grid(sticky="news") # row=4, column=0
        l = tk.Label(f, text="( Shift-enter=OK (keep), Enter=OK (clear), Escape=Abort )")
        l.grid(sticky="news")
        if self.Message is not None:
            logger.debug("Creating message...")
            # rows: 1=body, 2=buttonbox,
            self.message_label = l = tk.Label(f, textvariable=self.Message, font="emphasis")
            l.grid(sticky="news")
        viewpageurl = self.App.WikiLimsPage.getViewPageUrl()
        l = HyperLink(self, uri=viewpageurl, text="View page in browser")
        l.grid() # row=2, column=0        self.columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.cancel) # If the window manager requests the window to be closed (deleted).
        self.grab_set() # Makes sure no mouse/keyboard events are sent to the wrong Tk window.
        self.initial_focus.focus_set()


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
            logger.info("No self.Fieldvars, aborting")
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
                logger.debug("Created ttk.Entry widget with textvariable.get()='%s' and entry.get()='%s'",
                              speclist[0].get(), e.get())
                e.grid(row=r, column=c+1, sticky="nesw")
                r += 1
            if focusentry is None and not speclist[0].get():
                focusentry = e
        # Make top message.
        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=5, minsize=170)
        return focusentry


    def buttonbox(self):
        """
        Add standard button box.
        Override if you don't want the standard buttons
        """
        box = tk.Frame(self)
        self.ok_keep_button = w = tk.Button(box, text="OK (keep)", width=10, command=self.ok_keep)
        w.grid(row=1, column=0, sticky="news")
        self.ok_clear_button = w = tk.Button(box, text="OK (clear)", width=10, command=self.ok, default=tk.ACTIVE)
        w.grid(row=1, column=1, sticky="news")
        self.cancel_button = w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.grid(row=1, column=2, sticky="news")
        box.columnconfigure((0, 1, 2), weight=1) # make column expand.
        box.rowconfigure(1, weight=1)
        box.rowconfigure(2, weight=0)
        box.grid(row=2, column=0, sticky="news", padx=5, pady=10)
        self.bind("<Shift-Return>", self.ok_keep)
        self.bind("<Return>", self.ok_clear) # ok_clear
        self.bind("<Escape>", self.cancel)


    # standard button semantics
    def ok_keep(self, event=None):
        """invoked when the users presses the 'ok' button."""
        logger.debug("ok_keep invoked...")
        if not self.validate(): # validate is in charge of displaying message to the user
            self.initial_focus.focus_set() # put focus back
            return
        #self.withdraw() # ahh...
        self.update_idletasks()
        self.apply()
        self.App.add_entry(addNewEntryWithSameFile=True)
        #self.cancel() # add_entry() determines whether to invoke next_entry()

    def ok(self, event=None):
        """ Alias for ok_clear """
        self.ok_clear()

    # standard button semantics
    def ok_clear(self, event=None):
        """invoked when the users presses the 'ok' button."""
        logger.debug("ok_clear invoked...")
        if not self.validate(): # validate is in charge of displaying message to the user
            self.initial_focus.focus_set() # put focus back
            return
        #self.withdraw() # ahh...
        self.update_idletasks()
        self.apply()
        self.App.add_entry()
        #self.cancel() # add_entry() invokes next_entry()

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
        existingname = self.App.attachmentNameExists()
        if existingname:
            msg = "An attachment with the name {} already exists on the LIMS page. \
If you press 'ok', the entry will link to the existing attachment on the page. \
If you want to upload the file as a new attachment, you must provide a name that is not used. \
If you want to override the old attachment, you should open the page and upload the file manually.".format(existingname)
            linktoexisting = tkMessageBox.askokcancel("Attachment name exists", msg)
            if not linktoexisting:
                return 0
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
        Options dict can be used to modify login prompt settings, e.g.
        whether to store the password in memory.
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

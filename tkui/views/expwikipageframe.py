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
# pylint: disable-msg=R0901,R0924
"""
Module with a simple frame with a JournalViewer frame and controls (buttons) to update it.
"""


try:
    #import tkinter as tk
    from tkinter import ttk
except ImportError:
    #import Tkinter as tk
    import ttk

#import htmllib, formatter
import logging
logger = logging.getLogger(__name__)

#from subentrieslistbox import SubentriesListbox
#from explistboxes import SubentriesListbox, FilelistListbox, LocalFilelistListbox, WikiFilelistListbox

from shared_ui_utils import ExpFrame
#from rspysol.rstkhtml import tkHTMLParser, tkHTMLWriter
from journalviewerframe import JournalViewer


class ExpWikipageFrame(ExpFrame):
    """
    A simple frame with a JournalViewer frame and controls (buttons) to update it.
    """
    #def __init__(self, parent, experiment, confighandler):
    #    ttk.Frame.__init__(self, parent)
    #    self.Parent = parent
    #    self.Experiment = experiment
    #    self.Confighandler = confighandler
    #    self.init_widgets()
    #    self.init_layout()
    #    self.init_bindings()

    def init_widgets(self, ):
        self.pageview = JournalViewer(self, self.Experiment)
        self.controlframe = ttk.Frame(self)
        self.xhtmlbtn = ttk.Button(self.controlframe, text="View xhtml code", command=self.update_wiki_xhtml)
        self.htmlbtn = ttk.Button(self.controlframe, text="View parsed html", command=self.update_and_parse_wiki_html)
        self.getupdatedstructbtn  = ttk.Button(self.controlframe, text="Reload page from server", command=self.reload_pagestruct)
        self.LastView = None


    def init_layout(self, ):
        self.controlframe.grid(row=1, column=1, sticky="news")
        self.xhtmlbtn.grid(row=1, column=2, sticky="news")
        self.htmlbtn.grid(row=1, column=1, sticky="news")
        self.getupdatedstructbtn.grid(row=1, column=3, sticky="news")

        self.pageview.grid(row=2, column=1, sticky="news")

        self.rowconfigure(2, weight=1)
        self.columnconfigure(1, weight=1)

    def init_bindings(self, ):
        pass

    def update_and_parse_wiki_html(self):
        """
        Loads the page view with parsed/formatted html.
        """
        self.pageview.set_and_parse_xhtml()
        self.LastView = 'parsed_html'

    def update_wiki_xhtml(self):
        """
        Loads the page view with raw xhtml code.
        """
        self.pageview.update_wiki_xhtml()
        self.LastView = 'xhtml_code'

    def reload_pagestruct(self):
        """
        Re-loads the experiment's wiki page and updates the page view.
        """
        self.Experiment.reloadWikipage()
        if self.LastView == 'parsed_html':
            self.pageview.set_and_parse_xhtml()
        else:
            self.pageview.update_wiki_xhtml()

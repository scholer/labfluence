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

# python 2.7:
import Tkinter as tk
import ttk
import Tix # Lots of widgets, but tix is not being developed anymore, so only use if you really must.

import htmllib, formatter

#from subentrieslistbox import SubentriesListbox
#from explistboxes import SubentriesListbox, FilelistListbox, LocalFilelistListbox, WikiFilelistListbox

from shared_ui_utils import HyperLink, ExpFrame
from rspysol.rstkhtml import tkHTMLParser, tkHTMLWriter
from expjournalframe import JournalViewer


class ExpWikipageFrame(ExpFrame):
    """
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
        self.xhtmlbtn = ttk.Button(self.controlframe, text="View xhtml", command=self.update_wiki_xhtml)
        self.htmlbtn = ttk.Button(self.controlframe, text="View HTML")


    def init_layout(self, ):
        self.controlframe.grid(row=1, column=1, sticky="news")
        self.xhtmlbtn.grid(row=1, column=2, sticky="news")
        self.htmlbtn.grid(row=1, column=1, sticky="news")

        self.pageview.grid(row=2, column=1, sticky="news")

        self.rowconfigure(2, weight=1)
        self.columnconfigure(1, weight=1)

    def init_bindings(self, ):
        pass


    def update_wiki_xhtml(self, ):
        self.pageview.update_wiki_xhtml()

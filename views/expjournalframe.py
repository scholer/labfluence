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

from subentrieslistbox import SubentriesListbox


class ExpJournalFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        self.grid(row=1, column=1, sticky="nesw")#, padx=50, pady=30)
        self.Experiment = experiment
        #self.Confighandler = confighandler # Not sure this will ever be needed, probably better to always go through the experiment object...
        self.PropVariables = dict()
        self.DynamicVariables = dict()
        self.Labels = dict()
        self.Entries = dict()

        self.listframe = SubentriesListbox(self, experiment, confighandler)
        self.listframe.grid(row=1, column=0)
        self.journalframe = ttk.Frame(self)
        self.journalframe.grid(row=1, column=1, sticky="nesw")
        self.columnconfigure(1, weight=1)
        label = tk.Label(self, text="hej der")
        label.grid(row=0, column=0, sticky="e")

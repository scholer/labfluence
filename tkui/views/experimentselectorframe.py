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
import logging
logger = logging.getLogger(__name__)

from expmanagerlistboxes import ActiveExpsListbox, LocalExpsListbox, WikiExpsListbox


# This is generally called through a dialog or something...
# Or, well... a dialog is also just a toplevel, and all it has to do is update
# Experiment.ActiveExperimentIds, and the rest happens via callbacks registrered in the confighandler.


class ExperimentSelectorWindow(tk.Toplevel):

    def __init__(self, confighandler):
        # When you inherit, remember to call the parent ;-)
        tk.Toplevel.__init__(self)
        self.Confighandler = confighandler
        self.mainframe = ExperimentSelectorFrame(self, confighandler)
        self.mainframe.grid(row=0, column=0, sticky="nesw")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)



class ExperimentSelectorFrame(ttk.Frame):

    def __init__(self, parent, confighandler):
        self.Parent = parent
        self.Confighandler = confighandler
        # REMEMBER: super cannot be used with old-style classes, only new-style (which inherits from object)
        #super(ExperimentSelectorFrame, self).__init__(parent)
        # for old-style use: <parent-class>.__init__(self, <other args>)  -- where you would use p = ParentClass(<other args>)
        ttk.Frame.__init__(self, parent)
        self.init_widgets()
        self.init_layout()


    def init_widgets(self):
        # listboxes:
        self.activeexpslist = ActiveExpsListbox(self, self.Confighandler) # reversedsort=True is now default...
        self.localexpslist = LocalExpsListbox(self, self.Confighandler)
        self.wikiexpslist = WikiExpsListbox(self, self.Confighandler)
        # buttons:
        #self.localexps_selectbtn = ttk.Button(self, command=self.add_selectedlocalexps, text="Add selected >>")
        #self.wikiexps_selectbtn = ttk.Button(self, command=self.add_selectedwikiexps, text="<< Add selected")
        # labels:
        #self.activeexpsheader = ttk.Label(self, text="Active experiments")
        self.localexpsheader = ttk.Label(self, text="Local experiments")
        #self.wikiexpsheader = ttk.Label(self, text="Wiki experiments")

    def init_layout(self):
        #self.activeexpslist.grid(row=2, column=3, rowspan=3, sticky="news")
        self.localexpslist.grid(row=2, column=1, rowspan=3, sticky="news")
        #self.wikiexpslist.grid(row=2, column=5, rowspan=3, sticky="news")
        #self.localexps_selectbtn.grid(row=3, column=2)
        #self.wikiexps_selectbtn.grid(row=3, column=4)
        #self.activeexpsheader.grid(row=1, column=3)
        self.localexpsheader.grid(row=1, column=1)
        #self.wikiexpsheader.grid(row=1, column=5)

        # row+column configuration:
        #self.columnconfigure((1,5), weight=2, minsize=200)
        #self.columnconfigure((3,), weight=1, minsize=150)
        self.columnconfigure((1,), weight=1, minsize=400)
        self.rowconfigure((2), weight=2, minsize=500)


    @property
    def ExperimentManager(self):
        return self.Confighandler.Singletons.get('experimentmanager')

    def add_selectedlocalexps(self, event=None):
        # ExperimentManager will make sure to invoke the callbacks registrered
        # for changes to the ActiveExperiments list.
        expids = self.localexpslist.getSelectedIds()
        self.ExperimentManager.addActiveExperiments( expids )
        self.localexpslist.selection_clear(0, tk.END)

    def add_selectedwikiexps(self, event=None):
        expids = self.wikiexpslist.getSelectedIds()
        self.ExperimentManager.addActiveExperiments( expids )
        self.wikiexpslist.selection_clear(0, tk.END)

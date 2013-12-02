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

from explistboxes import LocalExpsListbox, WikiExpsListbox


# This is generally called through a dialog or something...
# Or, well... a dialog is also just a toplevel, and all it has to do is update
# Experiment.ActiveExperimentIds, and the rest happens via callbacks registrered in the confighandler.


class ExperimentManagerWindow(tk.Toplevel):

    def __init__(self, confighandler):
        # When you inherit, remember to call the parent ;-)
        tk.Toplevel.__init__(self)
        self.Confighandler = confighandler
        self.mainframe = ExperimentManagerFrame(self, confighandler)
        self.mainframe.grid(row=0, column=0, sticky="nesw")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)



class ExperimentManagerFrame(ttk.Frame):

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

        # frames:
        self.localexpsmanagerframe = ttk.Frame(self)
        self.wikiexpsmanagerframe = ttk.Frame(self)
        # listboxes:
        #self.activeexpslist = ActiveExpsListbox(self, self.Confighandler, reversedsort=True)
        self.localexpslist = LocalExpsListbox(self.localexpsmanagerframe, self.Confighandler)
        self.wikiexpslist = WikiExpsListbox(self.wikiexpsmanagerframe, self.Confighandler)
        # buttons:
        self.localexps_selectbtn = ttk.Button(self.localexpsmanagerframe, command=self.add_selectedlocalexps, text="<< Activate selected  ")
        self.wikiexps_importselectedbtn = ttk.Button(self.wikiexpsmanagerframe, command=self.importselectedwikiexps, text="<< Import selected  ")
        self.wikiexps_importallbtn = ttk.Button(self.wikiexpsmanagerframe, command=self.importallwikiexps, text="<< Import all wiki exps  ")
        # labels:
        #self.activeexpsheader = ttk.Label(self, text="Active experiments")
        self.localexpsheader = ttk.Label(self.localexpsmanagerframe, text="Local experiments")
        self.wikiexpsheader = ttk.Label(self.wikiexpsmanagerframe, text="Wiki experiments")



    def init_layout(self):
        # Frames:
        self.localexpsmanagerframe.grid(row=1, column=1, sticky="news")
        self.wikiexpsmanagerframe.grid(row=1, column=3, sticky="news")
        self.rowconfigure(1, weight=1) # Make sure the frames are expanded
        #self.wikiexpsmanagerframe.rowconfigure(1, weight=1)
        # row+column configuration:
        self.columnconfigure((1, 3), weight=3, minsize=300)
        self.columnconfigure((2,), weight=1, minsize=10)
        self.rowconfigure(1, weight=2, minsize=600)

        # Local experiment management frame:
        self.localexpslist.grid(row=4, column=1, columnspan=2, sticky="news")
        self.localexps_selectbtn.grid(row=3, column=1)
        self.localexpsheader.grid(row=1, column=1)
        self.localexpsmanagerframe.columnconfigure((1, 2), weight=1)
        self.localexpsmanagerframe.rowconfigure(4, weight=1)  # The row containing the two listboxes:

        # Wiki experiment management frame:
        self.wikiexpslist.grid(row=4, column=1, columnspan=2, sticky="news")
        self.wikiexpsheader.grid(row=1, column=1)
        self.wikiexps_importallbtn.grid(row=2, column=1)
        self.wikiexps_importselectedbtn.grid(row=3, column=1)
        self.wikiexpsmanagerframe.columnconfigure((1, ), weight=1)
        self.wikiexpsmanagerframe.rowconfigure(4, weight=5)  # The row containing the two listboxes:




    @property
    def ExperimentManager(self):
        return self.Confighandler.Singletons.get('experimentmanager')

    def add_selectedlocalexps(self, event=None):
        # ExperimentManager will make sure to invoke the callbacks registrered
        # for changes to the ActiveExperiments list.
        expids = self.localexpslist.getSelectedIds()
        self.ExperimentManager.addActiveExperiments( expids )
        self.localexpslist.selection_clear(0, tk.END)

    def importselectedwikiexps(self, event=None):
        expids = self.wikiexpslist.getSelectedIds()
        logger.info("Merging experiments: %s", expids)
        if expids:
            self.ExperimentManager.mergeCurrentWikiExperiments(autocreatelocaldirs=True, mergeonlyexpids=expids)
        #self.ExperimentManager.addActiveExperiments( expids )
        #self.wikiexpslist.selection_clear(0, tk.END)

    def importallwikiexps(self, ):
        """
        Import all experiments from the wiki...
        """
        self.ExperimentManager.mergeCurrentWikiExperiments(autocreatelocaldirs=True)
        self.localexpslist.updatelist()

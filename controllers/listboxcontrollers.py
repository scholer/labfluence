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

# python 3.x:
#from tkinter import ttk
# python 2.7:
import Tkinter as tk
import ttk

import logging
logger = logging.getLogger(__name__)

# Note: A simpler alternative to using a controller could be to simply expend the tk.Listbox class,
# or just configure the listbox manually...
# See views/experimentmanagerframes.py for widgets that implement this approach

class ExpListBoxController(object):

    def __init__(self, listbox, confighandler, app=None):
        self.Listbox = listbox
        self.Confighandler = confighandler
        self._app = app
        self.ExperimentByListIndex = list()
        # You could also just assume the list is immutable and simply rely on the indices.
        #self.EntryMap = dict() # Maps an entry
        self.updateList()
        self.Listbox.bind('<<ListboxSelect>>', self.on_select ) # Will throw the event to the show_notebook
        self.Listbox.bind("<Double-Button-1>", self.on_doubleclick)

    @property
    def App(self):
        return self._app or self.Confighandler.Singletons.get('app')
    @property
    def ExperimentManager(self):
        return self.Confighandler.Singletons.get('experimentmanager')
    @property
    def Experiments(self):
        """
        Override this in custom classes...
        """
        return None

    def populateList(self, experiments):
        # uhm... maybe just doing repr(e) or even e is okay, even for experiment objects??
        # must the items be strings? Or should they just have a string representation?
        self.Listbox.insert(tk.END, *experiments)

    def updateList(self):
        exps = self.Experiments # This property works rather like the getlist() method in filemanager.
        logger.debug("updating list with experiments: {}".format(exps))
        self.clearList()
        if exps:
            logger.debug("\nUpdating self {} list with experiments:\n{}".format(self, "\n".join("{e} with props {e.Props}".format(e=e) for e in self.Experiments)))
            # Note: The list will get the string representation from the experiment ( __repr__ method).
            # This is also what is returned upon querying.
            self.ExperimentByListIndex = exps # This list should be consolidated to match the (<display>, <identifier>, <full object>) tuple list structure
            self.Listbox.insert(tk.END, *exps) # Nope, keyword arguments cannot be used as far as I can tell...

    def clearList(self):
        self.Listbox.delete(0, tk.END)

    def on_select(self, event):
        lst = event.widget
        curselection = lst.curselection() # Returns tuple of selected indices., e.g. (1, )
        selected_items = lst.get(tk.ACTIVE) # Returns the string values of the list entries
        logger.info("curselection={}, selected_items={}, selected_items type: {}".format(curselection, selected_items, type(selected_items)))
        experiment = self.ExperimentByListIndex[int(curselection[0])]
        logger.info("curselection={}, experiment={}, experiment type: {}".format(curselection, experiment, type(experiment)))
        self.showExp(experiment)
    def on_doubleclick(self, event):
        pass

    def showExp(self, experiment):
        app = self.App
        app.show_notebook(experiment)



class ActiveExpListBoxController(ExpListBoxController):

    def __init__(self, listbox, confighandler, app=None):
        super(ActiveExpListBoxController, self).__init__(listbox, confighandler, app)
        self.Confighandler.registerEntryChangeCallback('app_active_experiments', self.updateList)

    @property
    def Experiments(self):
        em = self.ExperimentManager
        if em:
            logger.debug("Returning em.ActiveExperiments.")
            return em.ActiveExperiments
        #logger.debug("Getting self.Confighandler.get('app_active_experiments')"
        #return self.Confighandler.get('app_active_experiments')


class RecentExpListBoxController(ExpListBoxController):

    def __init__(self, listbox, confighandler, app=None):
        super(RecentExpListBoxController, self).__init__(listbox, confighandler, app)
        self.Confighandler.registerEntryChangeCallback('app_recent_experiments', self.updateList)

    @property
    def Experiments(self):
        em = self.ExperimentManager
        if em:
            logger.debug("Returning em.RecentExperiments.")
            return em.RecentExperiments

    def on_doubleclick(self, event):
        lst = event.widget
        curselection = lst.curselection() # Returns tuple of selected indices., e.g. (1, )
        selected_items = lst.get(tk.ACTIVE) # Returns the string values of the list entries
        logger.info("curselection={}, selected_items={}, selected_items type: {}".format(curselection, selected_items, type(selected_items)))
        experiment = self.ExperimentByListIndex[int(curselection[0])]
        logger.info("curselection={}, experiment={}, experiment type: {}".format(curselection, experiment, type(experiment)))
        expid = experiment.Expid
        self.ExperimentManager.addActiveExperiments( (expid, ))
        # possibly invoke
        # self.Confighandler.invoke # nope, this is done by Manager.addActiveExperiments...
        # however, if you use Manager.addActiveExperiment(expid), then it is _not_ invoked.

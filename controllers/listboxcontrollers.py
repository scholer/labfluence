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

# Note: A simpler alternative to using a controller could be to simply expend the tk.Listbox class,
# or just configure the listbox manually...


class ExpListBoxController(object):

    def __init__(self, listbox, confighandler, app=None):
        self.Listbox = listbox
        self.Confighandler = confighandler
        self.App = app or self.Confighandler.Singletons.get('app')
        self.ExperimentByListIndex = list()
        # You could also just assume the list is immutable and simply rely on the indices.
        #self.EntryMap = dict() # Maps an entry
        self.updateList()
        #self.activeexps_list.bind('<<ListboxSelect>>', self.show_notebook ) # Will throw the event to the show_notebook
        self.Listbox.bind('<<ListboxSelect>>', self.on_select ) # Will throw the event to the show_notebook

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
        if exps:
            print "\nUpdating self {} list with experiments:\n{}".format(self, "\n".join("{e} with props {e.Props}".format(e=e) for e in self.Experiments))
            self.clearList()
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
        print curselection, selected_items, type(selected_items)
        experiment = self.ExperimentByListIndex[int(curselection[0])]
        print curselection, experiment, type(experiment)
        self.showExp(experiment)


    def showExp(self, experiment):
        app = self.App
        app.show_notebook(experiment)



class ActiveExpListBoxController(ExpListBoxController):

    def __init__(self, listbox, confighandler, app=None):
        super(ActiveExpListBoxController, self).__init__(listbox, confighandler, app)
        self.Confighandler.registerEntryChangeCallback('app_active_experiments', self.updateList)

    @property
    def Experiments(self):
        em = self.Confighandler.Singletons.get('experimentmanager', None)
        if em:
            print "Getting em.ActiveExperiments"
            return em.ActiveExperiments
        print "Getting self.Confighandler.get('app_active_experiments')"
        return self.Confighandler.get('app_active_experiments')



class RecentExpListBoxController(ExpListBoxController):

    def __init__(self, listbox, confighandler, app=None):
        super(RecentExpListBoxController, self).__init__(listbox, confighandler, app)
        self.Confighandler.registerEntryChangeCallback('app_recent_experiments', self.updateList)

    @property
    def Experiments(self):
        em = self.Confighandler.Singletons.get('experimentmanager', None)
        if em:
            return em.RecentExperiments
        return self.Confighandler.get('app_recent_experiments')

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
- ExpManagerListBox: List box to display lists of experiments
  |- ActiveExpsListbox:
  |- RecentExpsListbox:

Notice: ActiveExpsListbox and RecentExpsListbox are implemented using controllers!

"""

# python 2.7:
import Tkinter as tk
#import ttk
#import Tix # Lots of widgets, but tix is not being developed anymore, so only use if you really must.
import logging
logger = logging.getLogger(__name__)




class ExpManagerListBox(tk.Listbox):
    """
    Listbox class for all listboxes that displays list of experiments as managed through
    an ExperimentManager object/singleton.
    """

    def __init__(self, parent, confighandler, isSelectingCurrent=False, reversedsort=True, **kwargs):
        self.before_init(kwargs)
        self.IsSelectingCurrent = isSelectingCurrent
        self.Reversedsort = reversedsort
        # tk.MULTIPLE or tk.EXTENDED, tk.BROWSE is default tk mode
        kwargs.setdefault('selectmode', 'browse' if isSelectingCurrent else 'extended')
        tk.Listbox.__init__(self, parent, **kwargs)
        #self.ExperimentManager = experimentmanager # Property now...
        self.Confighandler = confighandler
        self.TupleList = list() ## list of (<display>, <identifier>, <full object>) tuples.
        self.init_variables()
        self.init_widgets()
        self.init_layout()
        self.updatelist()
        # standard bindings, enabling on_select and on_doubleclick for sub classes.
        # subclasses should add more in the init_bindings method.
        self.bind('<<ListboxSelect>>', self.on_select ) # Will throw the event to the show_notebook
        self.bind("<Double-Button-1>", self.on_doubleclick)
        self.init_bindings()
        self.after_init()

    @property
    def ExperimentManager(self, ):
        """
        Property, returns the confighandler's currently set ExperimentManager singleton.
        """
        return self.Confighandler.Singletons.get('experimentmanager')

    def before_init(self, kwargs):
        """ Hook method, invoked automatically during init, override in subclasses. """
        pass
    def after_init(self):
        """ Hook method, invoked automatically during init, override in subclasses. """
        pass
    def init_variables(self):
        """ Hook method, invoked automatically during init, override in subclasses. """
        pass
    def init_widgets(self):
        """ Hook method, invoked automatically during init, override in subclasses. """
        pass
    def init_layout(self):
        """ Hook method, invoked automatically during init, override in subclasses. """
        pass
    def init_bindings(self):
        """ Hook method, invoked automatically during init, override in subclasses. """
        pass
    def on_select(self, event):
        """
        Currently, does nothing, except if self.IsSelectingCurrent is True,
        then it will invoke self.ExperimentManager.setCurrentExpid(expid)
        """
        #lst = event.widget
        #lst = self
        #curselection = lst.curselection() # Returns tuple of selected indices., e.g. (1, )
        #selected_items = lst.get(tk.ACTIVE) # Returns the string values of the list entries
        #logger.info("curselection={}, selected_items={}, selected_items type: {}".format(curselection, selected_items, type(selected_items)))
        #experiment = self.ExperimentByListIndex[int(curselection[0])]
        #expids = [self.TupleList[int(i)][1] for i in self.curselection()]
        #logger.info("curselection={}, experiment={}, experiment type: {}".format(curselection, experiment, type(experiment)))
        expids = self.getSelectedIds()
        logger.debug("(%s) - selected expids: %s", self.__class__.__name__, expids)
        logger.debug("(%s) - self.TupleList is: %s", self.__class__.__name__, self.TupleList)
        logger.debug("(%s) - self.Reversedsort=%s, self.IsSelectingCurrent=%s",
                     self.__class__.__name__, self.Reversedsort, self.IsSelectingCurrent)
        if self.IsSelectingCurrent and expids:
            expid = expids[0]
            logger.info("%s: Setting 'app_current_expid' to %s", self, expid)
            self.ExperimentManager.setCurrentExpid(expid)

    def on_doubleclick(self, event):
        """
        Currently, does nothing.
        """
        pass

    def update_widget(self, ):
        """ Hook method, invoked automatically during init, override in subclasses. """
        pass

    def getConfigKey(self, key):
        """ Returns config value for <key> """
        self.Confighandler.get(key)

    def getSelectedIds(self, ):
        """ Returns expids corresponding to selected experiments in the list. """
        # self.curselection() returns tuple with selected indices.
        # This makes it easier to get the corresponding identifiers,
        # based on self.getExpByListIndices
        return [self.TupleList[int(i)][1] for i in self.curselection()]

    def getExpIds(self, ):
        """ Hook method, invoked automatically during init, override in subclasses. """
        return list()

    def getExperiments(self):
        # Not used...
        return self.getTupleList()

    def getTupleList(self):
        # returns the familiar list of (<display>, <identifier>, <full object>) tuples.
        # You can override this in subclasses, or choose to just override self.getExpsByIds()
        # where display is the text to show in list and identifier is e.g. an expid.
        # Reference implementation provided here:
        # expids =  # Which experiments to show?
        expids, experiments = self.ExperimentManager.getExpsById(self.getExpIds()) # Obtain these experiments from experiment manager
        display = [repr(exp) for exp in experiments] # Make a 'display' string representation
        if self.Reversedsort:
            tuplist = list(reversed(zip(display, expids, experiments)))
        else:
            tuplist = zip(display, expids, experiments)
        logger.debug("(%s) - returning tuplelist: %s", self.__class__.__name__, tuplist)
        return tuplist

    def populatelist(self, experiments):
        """ For manual external use. And reference. This is not used internally. """
        self.insert(tk.END, *experiments)

    def clearlist(self):
        """Removes all items from the list"""
        self.delete(0, tk.END)

    def updatelist(self, event=None):
        """
        Updates the list by first clearing it and then
        calling self.getTupleList()
        """
        tuples = list(self.getTupleList())
        self.clearlist()
        if tuples:
            logger.debug("Updating %s listbox with experiment tuples:\n%s",
                         self.__class__.__name__,
                         "\n".join("{e}".format(e=e) for e in tuples))
            # Note: The list will get the string representation from the experiment ( __repr__ method).
            # This is also what is returned upon querying.
            self.TupleList = tuples # save (<display>, <identifier>, <full object>) tuple list structure
            for tup in tuples:
                logger.debug("(%s) Adding %s with self.insert(%s, %s)", self.__class__.__name__, tup[0], tk.END, tup[0])
                self.insert(tk.END, tup[0])
            #self.insert(tk.END, *[tup[0] for tup in tuples])
        else:
            logger.info("getTupleList() returned a boolean false result: %s", tuples)


    def addSelectionToActiveExpsList(self, ):
        """
        Adds the current selection to the manager's active experiments list.
        """
        curselection = self.curselection() # Returns tuple of selected indices., e.g. (1, )
        #selected_items = lst.get(tk.ACTIVE) # Returns the string values of the list entries
        #logger.info("curselection={}, selected_items={}, selected_items type: {}".format(curselection, selected_items, type(selected_items)))
        expid = self.TupleList[int(curselection[0])][1]
        logger.info("curselection=%s, expid=%s", curselection, expid)
        self.ExperimentManager.addActiveExperiments( (expid, )) # This takes care of invoking callbacks.




class ActiveExpsListbox(ExpManagerListBox):
    """
    A listbox for displaying experimentmanager's active experiments.
    """

    def getExpIds(self, ):
        """
        Using the default getTupleList and just overriding getExpsIds method:
        """
        return self.ExperimentManager.ActiveExperimentIds

    def init_bindings(self, ):
        self.Confighandler.registerEntryChangeCallback('app_active_experiments', self.updatelist)
        self.bind('<Destroy>', self.unbind_on_destroy)

    def unbind_on_destroy(self, event):
        """
        You need to make sure the confighandler callbacks are unregistrered.
        Otherwise,
        ## TODO: implement try clause in confighandler.invokeEntryChangeCallback and
        ## automatically unregister failing calls.
        """
        # profile: unregisterEntryChangeCallback(<config_entry_key>, function=None, *args=None, **kwargs=None)
        # will unregister any registrered callbacks matching
        # (<config_entry_key>, function, args, kwargs) tuple, with None interpreted as wildcard.
        logger.debug("Here I would unbind: 'app_active_experiments', self.updatelist")
        self.Confighandler.unregisterEntryChangeCallback('app_active_experiments', self.updatelist)


class RecentExpsListbox(ExpManagerListBox):
    """
    Listbox class for displaying experimentmanager's recent experiments list
    """

    def getExpIds(self, ):
        """
        Using the default getTupleList and just overriding getExpsIds method:
        """
        return self.ExperimentManager.RecentExperimentIds

    def init_bindings(self, ):
        self.Confighandler.registerEntryChangeCallback('app_recent_experiments', self.updatelist)
        self.bind('<Destroy>', self.unbind_on_destroy)

    def on_doubleclick(self, event):
        # NB: This is bound during __init__, not in init_bindings.
        self.addSelectionToActiveExpsList()

    def unbind_on_destroy(self, event):
        """
        You need to make sure the confighandler callbacks are unregistrered.
        Otherwise,
        ## TODO: implement try clause in confighandler.invokeEntryChangeCallback and
        ## automatically unregister failing calls.
        """
        # profile: unregisterEntryChangeCallback(<config_entry_key>, function=None, *args=None, **kwargs=None)
        # will unregister any registrered callbacks matching
        # (<config_entry_key>, function, args, kwargs) tuple, with None interpreted as wildcard.
        logger.debug("Here I would unbind: 'app_recent_experiments', self.updatelist")
        self.Confighandler.unregisterEntryChangeCallback('app_recent_experiments', self.updatelist)


class LocalExpsListbox(ExpManagerListBox):
    """
    Listbox class for displaying experimentmanager's local experiments list
    """

    def getTupleList(self):
        """
        returns the familiar list of (<display>, <identifier>, <full object>) tuples.
        In this case, it is more efficient to re-implement the getTupleList:
        Several implementation options:
        1) Simply use ExperimentManager.ExperimentsById cached object list
        2) Call ExperimentManager.getLocalExperiments(ret='expid') to get an updated list.
        """
        logger.info("self.ExperimentManager.ExperimentsById: %s", self.ExperimentManager.ExperimentsById)
        expids, experiments = zip(*self.ExperimentManager.ExperimentsById.items())
        display = ( getattr(exp, 'Foldername', "") for exp in experiments )
        displaytuples = zip(display, expids, experiments)
        if self.Reversedsort:
            # Returning an iterator does not work for tkinter... :<
            ret = reversed(displaytuples)
            logger.debug("Returning display tuples (reversed): %s", ret)
            return ret
        else:
            logger.debug("Returning display tuples: %s", displaytuples)
            return displaytuples

    def on_doubleclick(self, event):
        # NB: This is bound during __init__, not in init_bindings.
        self.addSelectionToActiveExpsList()




class WikiExpsListbox(ExpManagerListBox):
    """
    Listbox class for displaying wiki experiments obtained
    through experimentmanager.
    """

    def getTupleList(self):
        """
        returns the familiar list of (<display>, <identifier>, <full object>) tuples.
        In this case, it is more efficient to re-implement the getTupleList:
        """
        displaytuples = list(self.ExperimentManager.getCurrentWikiExperiments(ret='display-tuple'))
        logger.info("%s displaytuples: %s", self.__class__.__name__, displaytuples )
        if self.Reversedsort:
            ret = reversed(displaytuples)
            logger.debug("Returning display tuples (reversed): %s", ret)
            return ret
        else:
            logger.debug("Returning display tuples: %s", displaytuples)
            return displaytuples

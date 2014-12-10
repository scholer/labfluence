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

# python 2.7:
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

import logging
logger = logging.getLogger(__name__)

"""
Some general-purpose listboxes that all requires some interaction with and experiment object.
(Yes, I refuse the C in MVC)

- ExpListBox: Base class with reference to a single Experiment instance
  |- FilelistListbox
  |- LocalFilelistListbox
  |- WikiFilelistListbox
  |- SubentriesListbox


- ExpManagerListBox: List box to display lists of experiments
  |- ActiveExpsListbox:
  |- RecentExpsListbox:

Notice: The logic for ActiveExpsListbox and RecentExpsListbox have also been implemented using controllers.
        See controllers/listboxcontrollers.py


"""



class ExpListbox(tk.Listbox):
    """
    Base frame for most list widgets that has a direct control over an experiment.
    **kwargs are passed as keyword arguments to ttk.Frame super class.
    Includes hook methods that should make it easy to avoid overriding the default init.
    These are (in order of invokation):
    - before_init   : prepare for frame initialization. This is passed the kwargs dict, which
                        so you can manipulate this before it is passed to the ttk.Frame super class.
    - frame_defaults: return dict of default frame options.
    - init_variables: initialize any variables and non-widget attributes. Tkinter variables should be stored in self.Variables dict unless special circumstances are required.
    - init_widgets  : initialize child widgets. Store references in dicts self.Labels, Buttons, Entries, Frames, etc.
    - init_layout   : should be used for the frame layout (if not specified under init_widgets)
    - init_bindings : bindings can be placed here.
    - after_init    : if you need to do some additional stuff after frame initialization, this is the place to do so.
    """

    def __init__(self, parent, experiment, **kwargs):
        #ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        self.before_init(kwargs)
        tk.Listbox.__init__(self, parent, **kwargs)
        self.Experiment = experiment
        self.init_variables()
        self.init_widgets()
        self.init_layout()
        self.init_bindings()
        self.after_init()
        #logger.debug("%s.__init__() finished using experiment %s", self.__class__.__name__, experiment)

    def frame_defaults(self):
        return dict()
    def before_init(self, kwargs):
        pass
    def after_init(self):
        pass
    def init_variables(self):
        pass
    def init_widgets(self):
        pass
    def init_layout(self):
        pass
    def init_bindings(self):
        pass



class FilelistListbox(ExpListbox):
    """
    """
    #def __init__(self, parent, experiment, **options):
    #    tk.Listbox.__init__(self, parent, **options)
    #    self.Experiment = experiment

    def init_variables(self):
        self.Filetuples = list()
        self.Fileslist = list()

    # I should make a convention as to what is display and what is reference
    # in tuples used in list, e.g. (<filename-displayed>, <real-file-path>)
    # same goes for (subentry-display-format, subentry_idx)
    def updatelist(self, filterdict=None):
        if filterdict is None:
            filterdict = dict()
        lst = self.getlist(filterdict)
        self.Filetuples = lst
        self.Fileslist = zip(*lst)
        self.delete(0, tk.END)
        if lst:
            self.insert(tk.END, *self.Fileslist[0])

    def getlist(self, filterdict):
        # override this method; must return a list of two-tuple items.
        return list()

    def getSelection(self):
        # Returning the complete file tuple with metadata -- makes it more useful.
        indices = map(int, self.curselection())
        return [self.Filetuples[ind] for ind in indices]


class LocalFilelistListbox(FilelistListbox):

    def getlist(self, filterdict):
        return self.Experiment.getLocalFilelist(**filterdict)


class WikiFilelistListbox(FilelistListbox):

    def getlist(self, filterdict):
        return self.Experiment.getAttachmentList(**filterdict)




class SubentriesListbox(ExpListbox):
    """
    A frame for displaying a list of subentries.
    I use a frame rather than a list directly because... I want to be able to add something later?
    Nah, fuck that, I just inherit from tk.Listbox directly.
    """

    def init_variables(self):
        self.Subentrylist = list() # list of (<display-str>, <subentry_idx>, <subentry-dict>)
        #self.subentrieslistbox = tk.Listbox(self)
        #self.subentrieslistbox.grid(row=0, column=0, sticky="news")
        #self.rowconfigure(0, weight=1)

    def updatelist(self):
        #logger.debug("%s updatelist() invoked, self.Experiment is: %s", self.__class__.__name__, self.Experiment)
        exp_subentry_dir_fmt = self.Experiment.getConfigEntry('exp_subentry_dir_fmt')
        def subentryrepr(subentry):
            #return foldername if foldername in subentry else exp_subentry_dir_fmt.format(**subentry)
            return subentry.get('foldername',
                                exp_subentry_dir_fmt.format(**self.Experiment.makeFormattingParams(subentry['subentry_idx'])) )
        lst = [ (subentryrepr(subentry), idx,subentry) for idx, subentry in self.Experiment.Subentries.items()]
        #logger.debug("%s.updatelist() :: lst is: %s", self.__class__.__name__, lst)
        self.Subentrylist = zip(*lst) # self.Subentrylist[0] is repr, while [1] is subentry_idx and [2] is the actual subentry dict properties.
        #self.subentrieslistbox.delete(0,tk.END)
        #self.subentrieslistbox.insert(tk.END, *self.Subentrylist[0])
        self.delete(0, tk.END)
        if lst:
            self.insert(tk.END, *self.Subentrylist[0])
        else:
            logger.info("%s, empty list: %s", self.__class__.__name__, lst)
        #logger.debug("%s, self.get(0, tk.END) is now: %s", self.__class__.__name__, self.get(0, last=tk.END))

    def clearlist(self):
        """ Clears the list of all items """
        #self.subentrieslistbox.delete(0,tk.END)
        self.delete(0, tk.END)

    def getSelectedSubentryIdxs(self):
        """ Returns currently selected subentry indices """
        curselection = [int(i) for i in self.curselection()]
        return [self.Subentrylist[1][i] for i in curselection] # Subentrylist[1] is list of subentry_idxs

    def getSelectedSubentries(self):
        """ Returns currently selected subentries """
        curselection = [int(i) for i in self.curselection()]
        return [self.Subentrylist[2][i] for i in curselection] # Subentrylist[1] is list of subentry_idxs

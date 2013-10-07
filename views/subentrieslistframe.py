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


class SubentriesListFrame(tk.Listbox):
    """
    A frame for displaying a list of subentries.
    I use a frame rather than a list directly because... I want to be able to add something later?
    Nah, fuck that, I just inherit from tk.Listbox directly.
    """
    def __init__(self, parent, experiment, confighandler):
        #ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        tk.Listbox.__init__(self, parent)
        self.Confighandler = confighandler
        self.Experiment = experiment
        self.Subentrylist = list() # list of (<display-str>, <subentry_idx>, <subentry-dict>)
        #self.subentrieslistbox = tk.Listbox(self)
        #self.subentrieslistbox.grid(row=0, column=0, sticky="news")
        #self.rowconfigure(0, weight=1)


    def updatelist(self):
        exp_subentry_dir_fmt = self.Confighandler.get('exp_subentry_dir_fmt')
        def subentryrepr(subentry):
            return foldername if foldername in subentry else exp_subentry_dir_fmt.format(**subentry)
        self.Subentrylist = zip(*[ (subentryrepr(subentry),idx,subentry) for idx,subentry in self.Experiment.Subentries])
        #self.subentrieslistbox.delete(0,tk.END)
        #self.subentrieslistbox.insert(tk.END, *self.Subentrylist[0])
        self.delete(0,tk.END)
        self.insert(tk.END, *self.Subentrylist[0])

    def clearlist(self):
        #self.subentrieslistbox.delete(0,tk.END)
        self.delete(0,tk.END)

    def getSelectedSubentryIdxs(self):
        curselection = self.curselection()
        return [self.Subentrylist[1][i] for i in curselection] # Subentrylist[1] is list of subentry_idxs

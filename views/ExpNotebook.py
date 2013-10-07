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

from expoverviewframe import ExpOverviewFrame
from expfilemanagerframe import ExpFilemanagerFrame
from expjournalframe import ExpJournalFrame


class BackgroundFrame(tk.Frame):

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)#, background='red') # note: background etc only for tk.Frame, not ttk.Frame.
        #self.grid(row=0, column=0, sticky="nesw") # No, ui elements should rarely configure this themselves, it should be the parent that decides this.
        startinfo = """
Open an experiment in the list to the left.
Click "Select" to add experiments to the active experiments list.
Click "New" to create a new experiment.
"""
        self.label = ttk.Label(self, text=startinfo, justify=tk.CENTER)
        #self.configure(relief='raised', borderwidth=2)
        self.label.grid(row=0, column=0) # without sticky, it should be center-aligned vertically and horizontally.
        # It is perfectly ok for an object to use row/columnconfigure to specify it's own internal grid layout structure.
        # Use weight=1 to make a row/column expand; otherwise it will default to 0 (i.e. take minimum amount of space)
        # This will thus make the label center-aligned both vertically and horizontally.
        self.rowconfigure(0, weight=1) #minsize=600)
        self.columnconfigure(0, weight=1) #minsize=600)


class ExpNotebook(ttk.Notebook):
    """
    For info, see:
    - http://docs.python.org/2/library/ttk.html
    """
    def __init__(self, parent, experiment, confighandler, **options):
        # init super:
        #self.notebook = super(ttk.Notebook, self).__init__(parent) # only works for
        # for old-type classes, use:
        ttk.Notebook.__init__(self, parent, **options)#, padding=(5,5,5,5)) # returns None...
        # Note: ttk objects does not support '*color', relief and other specs directly but uses 'style'.
        # grid() should generally be called by the parent, specifies how this widget is positioned in its parent's grid.
        # It is perfectly ok for an object to use row/columnconfigure to specify it's own internal grid layout structure.
        # Use weight=1 to make a row/column expand; otherwise it will default to 0 (i.e. take minimum amount of space)
        #self.rowconfigure(1, weight=1) # also: minsize, (i)pad, etc...
        #self.columnconfigure(1, weight=1)#, pad=50)
        # however, since Notebook widgets does not usually use a grid layout manager, this does not have any effect...
        self.overviewframe = ExpOverviewFrame(self, experiment, confighandler)
        self.filemanagerframe = ExpFilemanagerFrame(self, experiment, confighandler)
        self.journalframe = ExpJournalFrame(self, experiment, confighandler)
        # Adding tabs (pages) to notebook
        self.add(self.overviewframe, text="Overview", sticky="nesw", underline=0)
        self.add(self.filemanagerframe, text="File management", sticky="nesw", underline=0)
        self.add(self.journalframe, text="Journal assistent", sticky="nesw", underline=0)
        self.enable_traversal()

    def update_info(self):
        self.overviewframe.update_properties()

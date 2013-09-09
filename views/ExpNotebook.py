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


class ExpNotebook(ttk.Notebook):
    
    def __init__(self, parent, experiment=None):
        # init super:
        #self.notebook = super(ttk.Notebook, self).__init__(parent) # only works for 
        # for old-type classes, use:
        ttk.Notebook.__init__(self, parent) # returns None...
        
        self.overviewframe = ttk.Frame(self)
        self.filesframe = ttk.Frame(self)
        self.journalframe = ttk.Frame(self)
        # Adding tabs (pages) to notebook
        self.add(self.overviewframe, text="Overview")
        self.add(self.filesframe, text="File management")
        self.add(self.journalframe, text="Journal assistent")

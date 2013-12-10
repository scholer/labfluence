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
Unfinished module.
Intended to be used to display files and directories of satellite locations,
e.g. mounted ftp shares, etc.
"""

# python 2.7:
import ttk

import logging
logger = logging.getLogger(__name__)

#from subentrieslistbox import SubentriesListbox
#from explistboxes import SubentriesListbox, FilelistListbox, LocalFilelistListbox, WikiFilelistListbox
from shared_ui_utils import ExpFrame


class ExpSatellitelocationsFrame(ExpFrame):
    """
    Intended to be used to display files and directories of satellite locations,
    e.g. mounted ftp shares, etc.
    """
    #def __init__(self, parent, experiment):
    #    ttk.Frame.__init__(self, parent)
    #    self.Parent = parent
    #    self.Experiment = experiment
    #    self.Confighandler = confighandler

    def init_widgets(self, ):
        self.controlframe = ttk.Frame(self)
        #self.pageview = JournalViewer(self, self.Experiment)

        self.controlframe.grid(row=1, column=1, sticky="news")
        #self.pageview.grid(row=2, column=1, sticky="news")
        self.rowconfigure(2, weight=1)
        self.columnconfigure(1, weight=1)

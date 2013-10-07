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

"""
Moving control logic to separate class, since I am starting to have quite a lot of different
ui/view elements involved...
"""


class ExpFilemanagerController(object):
    """
    Uhm... I think I will start out by implementing most logic in the ui elements directly,
    and then move it to dedicated controllers later.
    And looking at it as it is now, there isn't really any logic here at the momemt.
    """
    def __init__(self, confighandler, filemanagerframe):
        self._filemanagerframe = filemanagerframe
        self.Confighandler = confighandler
        # subentries_list by-passes the filterframe
        self.FilemanagerFrame.subentries_list.subentrieslistbox.bind('<<ListboxSelect>>', self.on_subentry_select ) # Will throw the event to the show_notebook



    @property
    def FilemanagerFrame(self):
        return self._filemanagerframe
    @FilemanagerFrame.setter
    def FilemanagerFrame(self, frame):
        self._filemanagerframe = frame
        return frame
    @FilemanagerFrame.deleter
    def FilemanagerFrame(self):
        self._filemanagerframe = None

    @property
    def Filterdict(self):
        return self.FilemanagerFrame.filelistfilterframe.getFilterdict()

    def on_subentry_select(self, event):
        lst = event.widget
        curselection = lst.curselection()
        self.updatefilelist()


    def updatefilelist(self):
        pass
        #self.FilemanagerFrame.localfilelistframe.updatefilelist()


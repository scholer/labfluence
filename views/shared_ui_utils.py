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
import webbrowser


class HyperLink(ttk.Label):
    """
    Based partially on:
    - http://effbot.org/zone/tkinter-text-hyperlink.htm
    - http://stackoverflow.com/questions/11639103/python-tkinter-tkfont-label-resize
    """

    def __init__(self, parent, uri=None, experiment=None, confighandler=None, **options):
        #defaults = dict(foreground="blue") # text color is not a property of the font, as far as I can tell.
        #options = dict(defaults, **options)
        ttk.Label.__init__(self, parent, **options)
        self.URI = uri
        self.Experiment = experiment
        self.Confighandler = confighandler
        if self.getUrl():
            self.configure(foreground="blue")
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Button-1>', self.open_uri)

    def on_enter(self, event):
        # NOTICE: This requires that 'hyperlink_active' has been stored as a named font,
        # e.g. initialized by a FontManager object.
        # self = event.widget
        if self.getUrl():
            lbl = event.widget
            lbl.configure(font='hyperlink_active', cursor="hand2")
        #print "entering hyperlink."

    def on_leave(self, event):
        event.widget.configure(font='hyperlink_inactive', cursor="")
        #print "leaving hyperlink."

    def getUrl(self):
        if self.URI:
            url = self.URI
        elif self.Experiment:
            url = self.Experiment.Props.get('url', None)
        else:
            url = None
        return url

    def open_uri(self, event):
        # http://stackoverflow.com/questions/8742644/python-2-7-tkinter-open-webbrowser-click
        url = self.getUrl()
        if not url:
            print "No url available...\n-url='{}'\nself.Experiment='{}'".format(url, self.Experiment)
            return
        print "Opening '{}'".format(url)
        # Perhaps check what protocol to use first, and open in webbrowser/filebrowser/ftpclient/?
        webbrowser.open_new(url)
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
import logging
logger = logging.getLogger(__name__)


class ExpFrame(ttk.Frame):
    """
    Base frame for most widgets that has a direct control over an experiment.
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
        self.before_init(kwargs)
        frameopts = dict(self.frame_defaults(), **kwargs)
        ttk.Frame.__init__(self, parent, **frameopts)
        self.Parent = parent
        self.Experiment = experiment
        # Edit: widgets should not have access to confighandler.
        # If they need a config entry, they should use experiment.getConfigEntry(key).
        self.Variables = dict()
        self.Labels = dict()
        self.Entries = dict()
        self.Buttons = dict()
        self.Frames = dict()
        self.init_variables()
        self.init_widgets()
        self.init_layout()
        self.init_bindings()
        self.after_init()

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

    def getApp(self):
        try:
            return self.Experiment.Confighandler.Singletons.get('app')
        except AttributeError:
            return None
    def getManager(self):
        try:
            return self.Experiment.Confighandler.Singletons.get('experimentmanager')
        except AttributeError:
            return None
    def getConfighandler(self):
        try:
            return self.Experiment.Confighandler
        except AttributeError:
            return None
    def getFonts(self, ):
        app = self.getApp()
        if app:
            return getattr(app, 'CustomFonts', None)


class HyperLink(ttk.Label):
    """
    Based partially on:
    - http://effbot.org/zone/tkinter-text-hyperlink.htm
    - http://stackoverflow.com/questions/11639103/python-tkinter-tkfont-label-resize
    state can be controlled as configure(state='disabled)
    """

    def __init__(self, parent, uri=None, experiment=None, **options):
        #defaults = dict(foreground="blue") # text color is not a property of the font, as far as I can tell.
        #options = dict(defaults, **options)
        ttk.Label.__init__(self, parent, **options)
        self.URI = uri
        self.Experiment = experiment
        if self.getUrl():
            self.configure(foreground="blue")
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave) # Enter=Mouse cursor hovering over widget; Return=Return key is pressed.
        self.bind('<Button-1>', self.open_uri) # Pressing left mouse btn. (bindings only apply when the widget is active).

    def on_enter(self, event):
        """
        NOTICE: This requires that 'hyperlink_active' has been stored as a named font,
        e.g. initialized by a FontManager object.
        """
        #self = event.widget
        if self.getUrl():
            lbl = event.widget
            lbl.configure(font='hyperlink_active', cursor="hand2")

    def on_leave(self, event):
        """ Bound to <Leave> virtual event """
        event.widget.configure(font='hyperlink_inactive', cursor="")

    def getUrl(self):
        """ Returns a browser-openable URL """
        if self.URI:
            url = self.URI
        elif self.Experiment:
            url = self.Experiment.getUrl()
        else:
            url = None
        return url

    def open_uri(self, event):
        """
        Based on http://stackoverflow.com/questions/8742644/python-2-7-tkinter-open-webbrowser-click
        """
        # self should equal event.widget
        url = event.widget.getUrl()
        if not url:
            logger.debug("No url available! url='%s', self.Experiment='%s'", url, self.Experiment)
            return
        logger.debug("Opening '%s'", url)
        # Perhaps check what protocol to use first, and open in webbrowser/filebrowser/ftpclient/?
        webbrowser.open_new(url)

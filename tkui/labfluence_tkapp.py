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
"""

I refactored the long labfluence_gui module to the following UI specific
tkui/labfluence_tkapp   - Contains "app" level items, has properties (which tk.Tk
                        objects can't because they are not new-style objects)
                        This should be suffiently abstract that it can theoretically be substituted
                        with e.g. a qt app class and most calls will work ok.
tkui/labfluence_tkroot  - Derives from tkinter.Tk, acts as the "tkroot".
tkui/mainwindow         - Does all the widget layout, etc.

Left, we have:
labfluence_gui          - Main script for the main labfluence application.

Optionally:
tkui/labfluence_app     - Could provide a base class that could be derived in
                        tkui/labfluence_tkapp with tk-specific things.


"""


# python 3.x:
#from tkinter import ttk
# python 2.7:
#import Tkinter as tk
#import ttk
#import tkFont
from Tkinter import TclError

# Other standard lib modules:
#import socket
#from datetime import datetime
#from collections import OrderedDict
import logging
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)

# Labfluence modules and classes:

from model.confighandler import ExpConfigHandler
from model.experimentmanager import ExperimentManager
#from model.experiment import Experiment
#from model.server import ConfluenceXmlRpcServer

from labfluence_tkroot import LabfluenceTkRoot

#from views.expnotebook import BackgroundFrame
#from views.experimentselectorframe import ExperimentSelectorWindow
#from views.dialogs import Dialog

#from controllers.listboxcontrollers import ActiveExpListBoxController, RecentExpListBoxController
#from controllers.filemanagercontroller import ExpFilemanagerController
from fontmanager import FontManager




class LabfluenceApp(object):
    """
    Note:
        -ActiveExperiments is a list of experiments that the user can modify himself, using the "Select..." functionality.
        -RecentExperiments is a list of the last 10 recently closed experiments; this is controlled soly by the app.
    """


    def __init__(self, confighandler=None):
        #self.ActiveExperiments = list() # Probably better to use a property attribute
        #self.RecentExperiments = list()
        logger.info(">>>>>>>>>>>>>>  Starting init of LabfluenceGUI  >>>>>>>>>>>>>>>>")

        self.Confighandler = confighandler or ExpConfigHandler(pathscheme='default1')
        #self.Confighandler.Singletons.setdefault('app', self)
        self.Confighandler.Singletons['app'] = self
        if 'experimentmanager' not in self.Confighandler.Singletons:
            print "LabfluenceGUI.__init__ >> Instantiating new ExperimentManager!"
            self.Confighandler.Singletons['experimentmanager'] = ExperimentManager(confighandler=self.Confighandler, autoinit=('localexps', ))

        #self.init_ui()
        self.tkroot = LabfluenceTkRoot(confighandler)
        logger.debug("self.tkroot initialized")
        self.Controllers = dict()
        self.ExpNotebooks = dict()
        self.init_bindings()
        self.init_fonts()
        self.connect_controllers()
        #persisted_windowstate = self.Confighandler.get('tk_window_state', None)
        #if persisted_windowstate == 'zoomed':
        #    self.tkroot.state('zoomed')
        #persisted_windowgeometry = self.Confighandler.get('tk_window_geometry', None)
        #if persisted_windowgeometry:
        #    try:
        #        self.tkroot.geometry(persisted_windowgeometry)
        #    except tk.TclError as e:
        #        print e

    # Properties, http://docs.python.org/2/library/functions.html#property
    # Note: Only works for new-style classes (which inherits from 'object').
    @property
    def Server(self):
        """Experiment manager, obtained from confighandler if possible.
        Edit: Not 'if possible'. Having a well-behaved confighandler is now a requirement as this significantly simplifies a lot of code.
        """
        return self.Confighandler.Singletons.get('server', None)

    # Property definition for old-style classes:
    # (Tkinter does not use new-style classes under python2.)
    #def getActiveExperimentIds(self):
    #    """ Returns ActiveExperimentIds from confighandler """
    #    return self.Confighandler.setdefault('app_active_experiments', list())
    #def setActiveExperimentIds(self, value):
    #    print "Setting (overwriting) the active experiments list is not allowed...  You can empty/clear it using del my_list[:] or mylist[:] = [] "
    #def delActiveExperimentIds(self):
    #    print "Deleting the active experiments list is not allowed...  You can empty/clear it using del my_list[:] or mylist[:] = [] "
    #ActiveExperimentIds = property(getActiveExperimentIds, setActiveExperimentIds, delActiveExperimentIds, "List of currently active experiments, obtained from confighandler.")
    # Alternative, using decorators:
    @property
    def ActiveExperimentIds(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())
    @property
    def RecentExperimentIds(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())
    #@RecentExperimentIds.setter
    #def RecentExperimentIds(self, value):
    #    print "Setting (overwriting) the recent experiments list is not allowed... You can empty/clear it using del my_list[:] or mylist[:] = [] "
    #@RecentExperimentIds.deleter
    #def RecentExperimentIds(self):
    #    print "Deleting the recent experiments list is not allowed... You can empty/clear it using del my_list[:] or mylist[:] = [] "

    @property
    def ExperimentManager(self):
        """Experiment manager, obtained from confighandler if possible.
        Edit: Not 'if possible'. Having a well-behaved confighandler is now a requirement as this significantly simplifies a lot of code.
        """
        return self.Confighandler.Singletons.get('experimentmanager', None)
    @ExperimentManager.setter
    def ExperimentManager(self, value):
        "List of recently opened experiments, obtained from confighandler."
        # Do NOT override existing experimentmanager if set, so using setdefault...
        self.Confighandler.Singletons.setdefault('experimentmanager', value)

    @property
    def ActiveExperiments(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.ExperimentManager.ActiveExperiments
    @property
    def RecentExperiments(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.ExperimentManager.RecentExperiments
    @property
    def WindowState(self):
        """ Returns the saved app window state from confighandler """
        return self.Confighandler.get('app_window_state', None)
    @WindowState.setter
    def WindowState(self, value):
        """ Sets tkroot window state and saves app window state to confighandler """
        try:
            self.tkroot.state(value)
            self.Confighandler.setkey('app_window_state', value, 'user')
        except TclError as e:
            print e
    @property
    def WindowGeometry(self):
        """ Returns the saved app window state from confighandler """
        return self.Confighandler.get('app_window_geometry', None)
    @WindowGeometry.setter
    def WindowGeometry(self, value):
        """ Sets tkroot window state and saves app window state to confighandler """
        try:
            self.tkroot.geometry(value)
            self.Confighandler.setkey('app_window_geometry', value, 'user')
        except TclError as e:
            print e

    ################
    ## BINDINGS ####
    ################

    #def tk_window_configured(self):
    #    self.Confighandler.setkey('app_window_geometry', self.tkroot.geometry(), 'user')
    #    self.Confighandler.setkey('app_window_state', self.tkroot.state(), 'user')

    def init_bindings(self):
        """ Initiates application bindings. Not currently used. """
        logger.debug("LabfluenceApp init_bindings currently does nothing.")
        # Use the following to intercept a window exit request:
        #self.tkroot.protocol("WM_DELETE_WINDOW", self.exitApp)
        #self.Confighandler.registerEntryChangeCallback("wiki_server_status", self.serverStatusChange)
        # Edit, these bindings are currently handled by the relevant controllers...
        #self.Confighandler.registerEntryChangeCallback("app_active_experiments", self.activeExpsChanged)
        #self.Confighandler.registerEntryChangeCallback("app_recent_experiments", self.recentExpsChanged)

    def init_fonts(self):
        """
        Based on http://stackoverflow.com/questions/4072150/python-tkinter-how-to-change-a-widgets-font-style-without-knowing-the-widgets
        Valid specs: family, size, weight (bold/normal), slant (italic/roman), underline (bool), overstrike (bool).
        """
        self.Fontmanager = FontManager()
        self.CustomFonts = self.Fontmanager.CustomFonts

    def connect_controllers(self):
        """ Initiates application controllers. Not currently used. """
        pass




    #####################
    ## STARTUP METHODS ##
    #####################
    def start(self):
        """ Starts the application's UI loop. """
        logger.info("starting tk.mainloop()...")
        self.tkroot.mainloop()
        logger.info("tk.mainloop() finished.")


    def add_notebook(self, experiment):
        """ Adds a notebook to the main UI. """
        return self.tkroot.add_notebook(experiment)

    def show_notebook(self, experiment):
        """ Shows a notebook to the main UI. """
        return self.tkroot.show_notebook(experiment)

    def load_experiment(self, experiment, show=True):
        """ Loads an experiment and shows it in the main UI. """
        if show:
            self.show_notebook(experiment)
        else:
            self.add_notebook(experiment)

    def exitApp(self):
        """
        Registrered with root.protocol("WM_DELETE_WINDOW", ask_quit)
        You can also get a similar effect with code that follows
        labfluence.start_loop() / tkroot.mainloop()
        (e.g. in the if __name__ == '__main__' section...)
        This *must* be called by labfluence_tkroot.
        """
        self.Confighandler.saveConfigs()
        self.tkroot.destroy()

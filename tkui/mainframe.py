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
import tkFont

# Other standard lib modules:
import socket
from datetime import datetime
from collections import OrderedDict
import logging
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)

# Labfluence modules and classes:

from model.confighandler import ExpConfigHandler
from model.experimentmanager import ExperimentManager
from model.experiment import Experiment
from model.server import ConfluenceXmlRpcServer

from views.expnotebook import ExpNotebook, BackgroundFrame
from views.experimentselectorframe import ExperimentSelectorWindow
from views.dialogs import Dialog

from views.expmanagerlistboxes import ActiveExpsListbox, RecentExpsListbox #LocalExpsListbox, WikiExpsListbox
# Edit: Using the self-controlling ActiveExpsListbox and RecentExpListbox listboxes instead of having
# simple listboxes with controllers attached:
from controllers.listboxcontrollers import ActiveExpListBoxController, RecentExpListBoxController
from controllers.filemanagercontroller import ExpFilemanagerController


from fontmanager import FontManager





class LabfluenceMainFrame(ttk.Frame):


    def __init__(self, parent, confighandler, **kwargs):
        ttk.Frame.__init__(self, parent, **kwargs)
        self.Parent = parent # uh... you mean the same as self.master??
        self.Confighandler = confighandler
        self.init_widgets()
        self.init_layout()
        self.connect_controllers()
        self.update_widgets()
        logger.debug("---> LabfluenceMainwindow.__init__() complete.")


    def getServer(self):
        return self.Confighandler.Singletons.get('server')


    def init_widgets(self):

        self.leftframe = ttk.Frame(self)
        self.controlsframe = ttk.Frame(self.leftframe)
        self.home_btn = tk.Button(self.controlsframe, text="Home", command=self.showHome)

        self.serverstatus_btn = tk.Button(self.controlsframe, text="(offline)", command=self.serverStatus)


        self.activeexps_frame = ttk.Frame(self.leftframe)
        self.activeexps_label = ttk.Label(self.activeexps_frame, text="Active experiments:")
        self.activeexps_select_btn = ttk.Button(self.activeexps_frame, text="<< Select", command=self.selectExperiments)
        self.manageexps_btn = ttk.Button(self.activeexps_frame, text="Manage...", command=self.manageExperiments)
        self.activeexps_new_btn = ttk.Button(self.activeexps_frame, text="Create...", command=self.createNewExperiment)
        # you do not strictly need to be able to reference this from self.
        ## Active experiments list:
        self.activeexps_list = ActiveExpsListbox(self.activeexps_frame, self.Confighandler,
                                                 isSelectingCurrent=True, # setting this sould also set setlectmode='browse' automatically.
                                                 height=16, activestyle='dotbox')#, selectmode='browse')
        #self.activeexps_list = tk.Listbox(self.activeexps_frame, height=16, activestyle='dotbox')

        # Recent experiments widgets
        ## TODO: Implement double-click action
        # (actually, this can be implemented in the class as a call to the model domain:
        # generally, if you double-click an experiment on the recent experiments list,
        # it should move the the active experiments list.
        self.recentexps_frame = ttk.Frame(self.leftframe)
        self.recentexps_list = RecentExpsListbox(self.recentexps_frame, self.Confighandler,
                                                 isSelectingCurrent=True,
                                                 height=10, width=30)#, , selectmode='browse')
        #self.recentexps_list = tk.Listbox(self.recentexps_frame, height=10, width=30)
        self.recentexps_label = ttk.Label(self.recentexps_frame, text="Recent experiments:")
        # Question: Have only _one_ notebook which is updated when a new experiment is selected/loaded?
        # Or have several, one for each active experiment, which are then shown and hidden when the active experiment is selected?
        # I decided to go for one for each active experiment, and that was a really good decision!
        self.rightframe = ttk.Frame(self)#, width=800, height=600)
        self.backgroundframe = BackgroundFrame(self.rightframe)
        logger.debug("mainframe init_widgets() complete.")



    def init_layout(self):

        # Making sure main frame expands and fills everything, using the grid geometry manager:
        self.grid(column=0, row=0, sticky="nsew") # position mainframe using grid gm.
        self.columnconfigure(0, weight=1, minsize=180) # sets column "0" to weight "1".
        self.columnconfigure(1, weight=5, minsize=500) # rightframe expands 5x more than leftframe
        self.rowconfigure(1, weight=1) # expand row 1

        #############################
        #### LEFT FRAME layout ######
        #############################
        self.leftframe.grid(column=0, row=1, sticky="nsew") # position leftframe in column 0, row 1 in the outer (mainframe) widget.
        self.leftframe.columnconfigure(0, weight=1)
        self.leftframe.rowconfigure((2,3), weight=1) # distribute space evently between row 0 and row 1

        #### CONTROLS layout   ###
        # Not specifying "row" in grid will use the next empty row; column defaults to 0
        self.controlsframe.grid(row=1, sticky="nesw")
        self.home_btn.grid(row=1, column=1)
        self.serverstatus_btn.grid(row=1, column=2)

        # Active experiments frame
        self.activeexps_frame.grid(row=2, sticky="nesw")
        self.activeexps_frame.rowconfigure(5, weight=1) # make the 5th row expand.
        self.activeexps_frame.columnconfigure(3, weight=2)
        #self.activeexps_frame.columnconfigure(0, weight=0)
        # Active experiments widgets
        #self.activeexps_list.bind('<<ListboxSelect>>', self.show_notebook ) # Will throw the event to the show_notebook
        # Active experiments widgets layout:
        self.activeexps_label.grid(column=1, row=0, columnspan=3, sticky="nw")
        self.activeexps_select_btn.grid(column=1, row=1, columnspan=2, sticky="we")
        self.manageexps_btn.grid(column=1, row=2)
        self.activeexps_new_btn.grid(column=2, row=2)

        self.activeexps_list.grid(column=0, row=5, columnspan=4, sticky="nesw")

        # Recent experiment frame
        self.recentexps_frame.grid(row=3, sticky="nesw")
        self.recentexps_frame.rowconfigure(5, weight=1) # make the 5th row expand.
        self.recentexps_frame.columnconfigure(1, weight=1) # make the 5th row expand.
        # Recent experiments widgets layout:
        self.recentexps_label.grid(column=0, row=0, columnspan=3, sticky="nw")
        self.recentexps_list.grid(column=0, row=5, columnspan=3, sticky="nesw")

        #####################
        #### RIGHT FRAME ####
        #####################
        # colors: http://www.tcl.tk/man/tcl8.4/TkCmd/colors.htm
        # note: ttk objects does not support specifying e.g. background colors on a per-widget basis,
        #self.rightframe.configure(background='cyan')
        # http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/ttk-Frame.html
        # options for grid is sticky, column, row, columnspan, rowspan, (i)pad(x/y),
        self.rightframe.grid(column=1, row=1, sticky="nsew")
        #self.rightframe.configure(relief='ridge', bd=2) # just to see the right frame...
        self.backgroundframe.grid(column=1, row=1, sticky="nesw")
        self.rightframe.columnconfigure(1, weight=1, minsize=700)
        self.rightframe.rowconfigure(1, weight=1, minsize=600)
        #self.add_notebook()


    def init_bindings(self):
        #self.tkroot.protocol("WM_DELETE_WINDOW", self.exitApp)
        self.Confighandler.registerEntryChangeCallback("wiki_server_status", self.serverStatusChange)
        # Edit, these bindings are currently handled by the relevant controllers.
        # And if you use the controller-independent versions, they will register those
        # callbacks themselves...
        #self.Confighandler.registerEntryChangeCallback("app_active_experiments", self.activeExpsChanged)
        #self.Confighandler.registerEntryChangeCallback("app_recent_experiments", self.recentExpsChanged)

    def update_widgets(self):
        self.serverStatusChange()



    #################################
    ### Controller-like methods #####
    #################################

    def serverStatus(self, event=None):
        """
        Invoked when the Online/(offline) server button is pressed.
        Will implicitly invoke serverStatusChange if the server's status has changed.
        """
        server = self.getServer()
        if server is None:
            # This call is needed in case the server was never activated
            # (in which case serverStatusChange is not called as a confighandler ConfigEntryChange callback)
            self.serverStatusChange()
            return
        serverinfo = server.getServerInfo()
        logger.debug("Server status, serverinfo: %s", serverinfo)
        # Calling any server command will check whether the server's connection status change.
        # If it has changed since the last call, the server will invoke all
        # callbacks registrered to 'wiki_server_status'. This includes self.serverStatusChange,
        # which was registrered in self.init_bindings()

    def serverStatusChange(self):
        """
        This is invoked automatically when the server's status changes,
        since this method is registrered with
        confighandler.registerConfigEntryChange('wiki_server_status', serverStatusChange)
        and the server will call confighandler.invokeConfigEntryChange('wiki_server_status')
        if the server's connection status changes.
        """
        server = self.Confighandler.Singletons.get('server')
        if server is None:
            self.serverstatus_btn.configure(background="red", text="(offline)")
            logger.debug( "No server available, server is: %s", server)
            return
        logger.debug( "SERVER: %s, _connectionok: %s", server, server._connectionok )
        if server._connectionok is None:
            logger.debug("Server._connectionok is None, perhaps the server has not had a chance to connect yet... ")
            server.autologin()
        if server:
            self.serverstatus_btn.configure(background="green", text="Online")
            logger.debug( "Server reported to be online :-)" )
            logger.debug( "self.Parent.ExpNotebooks: %s", self.Parent.ExpNotebooks )
            for expid,notebook in self.Parent.ExpNotebooks.items():
                notebook.update_info()
        else:
            self.serverstatus_btn.configure(background="red", text="(offline)")
            logger.debug( "Server reported to be offline, server._connectionok: %s", server._connectionok)


    def createNewExperiment(self, event=None):
        self.Parent.createNewExperiment()


    def connect_controllers(self):
        """

        """
        ## TODO: This needs to be refactored...
        return None
        # No longer using controllers, but using the self-controlling ActiveExpsListbox and RecentExpsListbox widgets.
        #self.ActiveExpListController = ActiveExpListBoxController(self.activeexps_list, self.Confighandler)
        #self.RecentExpListController = RecentExpListBoxController(self.recentexps_list, self.Confighandler)


    def showHome(self, event=None):
        self.backgroundframe.lift()


    def manageExperiments(self, event=None):
        self.Parent.manageExperiments()


    def selectExperiments(self, event=None):
        if hasattr(self, 'localexpslist'):
            pass
        self.Parent.selectExperiments()

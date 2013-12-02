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

#from model.confighandler import ExpConfigHandler
#from model.experimentmanager import ExperimentManager
from model.experiment import Experiment
#from model.server import ConfluenceXmlRpcServer


from mainframe import LabfluenceMainFrame
from views.expnotebook import ExpNotebook #, BackgroundFrame
from views.experimentselectorframe import ExperimentSelectorWindow
from views.experimentmanagerframe import ExperimentManagerWindow
from views.dialogs import Dialog

from controllers.listboxcontrollers import ActiveExpListBoxController, RecentExpListBoxController
#from controllers.filemanagercontroller import ExpFilemanagerController





class LabfluenceTkRoot(tk.Tk):

    def __init__(self, confighandler):
        tk.Tk.__init__(self)
        self.Controllers = dict()
        self.ExpNotebooks = dict()
        self.Confighandler = confighandler
        self.init_ui()
        self.init_bindings()
        self.connect_controllers()
        persisted_windowstate = self.Confighandler.get('tk_window_state', None)
        if persisted_windowstate == 'zoomed':
            self.state('zoomed')
        persisted_windowgeometry = self.Confighandler.get('tk_window_geometry', None)
        if persisted_windowgeometry:
            try:
                self.geometry(persisted_windowgeometry)
            except tk.TclError as e:
                print e
        #self.update_widgets()

    ### Getters and setters (old-school tk widgets does not support new-object properties)
    def getExperimentManager(self):
        return self.Confighandler.Singletons.get('experimentmanager', None)
    def getActiveExperimentIds(self):
        return self.Confighandler.setdefault('app_active_experiments', list())
    def getRecentExperimentIds(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())
    def getActiveExperiments(self):
        return self.getExperimentManager().ActiveExperiments
    def getRecentExperiments(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.getExperimentManager().RecentExperiments
    def Server(self):
        """Experiment manager, obtained from confighandler if possible.
        Edit: Not 'if possible'. Having a well-behaved confighandler is now a requirement as this significantly simplifies a lot of code.
        """
        return self.Confighandler.Singletons.get('server', None)



    def init_ui(self):
        #self.tkroot = tk.Tk()
        self.option_add('*tearOff', tk.FALSE)
        self.title("Labfluence - Experiment Assistent")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.add_menus()

        # to create a new window:
        #win = tk.Toplevel(self.tkroot) # uh... I guess this will create a new toplevel window?

        self.mainframe = LabfluenceMainFrame(self, self.Confighandler, padding="3 3 3 3") #"3 3 12 12"
        logger.debug("LabfluenceTkRoot.init_ui completed. self.mainframe is %s", self.mainframe)
        #self.mainframe.init_widgets()
        #self.mainframe.init_ui()

    def init_bindings(self):
        # Example using the new "pass_newvalue_as" argument.
        # The new
        """
        Invoking:
            self.Confighandler.registerEntryChangeCallback("app_current_expid", self.show_notebook, pass_newvalue_as='experiment')
        will set *args = list() and **kwargs = dict().
        This means that when invokeEntryChangeCallback is called for 'app_current_expid', the following is called:
            kwargs['experiment'] = <new value>
            self.show_notebook(*args, **kwargs), i.e. self.show_notebook(experiment=<new value>)
        """
        logger.debug("Registering 'app_current_expid' configentry change callback to %s", self.show_notebook)
        self.Confighandler.registerEntryChangeCallback("app_current_expid", self.show_notebook, pass_newvalue_as='experiment')
        # self.bind('<Destroy>', self.unbind_on_destroy)
        self.protocol("WM_DELETE_WINDOW", self.exitApp)
        #self.Confighandler.registerEntryChangeCallback("wiki_server_status", self.serverStatusChange) # Moved to mainframe.
        # These bindings are currently handled by the relevant controllers...
        #self.Confighandler.registerEntryChangeCallback("app_active_experiments", self.activeExpsChanged)
        #self.Confighandler.registerEntryChangeCallback("app_recent_experiments", self.recentExpsChanged)


    def exitApp(self):
        logger.info("VM_DELETE_WINDOW called for tk root.")
        # Make sure to unregister callbacks (in case you want to continue working with the model after shutting down the ui...)
        self.Confighandler.unregisterEntryChangeCallback('app_current_expid', self.show_notebook)
        app = self.getApp()
        if app:
            app.exitApp()
        else:
            logger.debug("self.getApp() returned '%s', destroying self by my self:", app)
            self.destroy()

    def getApp(self, ):
        return self.Confighandler.Singletons.get('app')

    def update_widgets(self):
        pass


    def add_notebook(self, experiment):
        #self.notebook = ttk.Notebook(self.rightframe)
        #self.notebook = expnotebook.ExpNotebook(self.rightframe)
        # Determine whether an actual experiment object was passed or just a string with expid
        # (the latter will normally be the case!)
        if not experiment:
            logger.info("add_notebook was called with boolean false experiment (%s), aborting...", experiment)
            return
        expid, experiment = self.get_expid_and_experiment(experiment)
        if expid not in self.ExpNotebooks:
            notebook = ExpNotebook(self.mainframe.rightframe, experiment)
            notebook.grid(column=1, row=1, sticky="nesw") # how to position notebook in its parent (rightframe)
            self.ExpNotebooks[expid] = notebook
        return self.ExpNotebooks[expid], expid, experiment
        # overviewframe = ttk.Frame(self.notebook)
        # filesframe = ttk.Frame(self.notebook)
        # journalframe = ttk.Frame(self.notebook)
        # # Adding tabs (pages) to notebook
        # self.notebook.add(overviewframe, text="Overview")
        # self.notebook.add(filesframe, text="File management")
        # self.notebook.add(journalframe, text="Journal assistent")

    def show_notebook(self, experiment):
        # http://stackoverflow.com/questions/3819354/in-tkinter-is-there-any-way-to-make-a-widget-not-visible
        #expid, experiment = self.get_expid_and_experiment(experiment)
        if not experiment:
            logger.info("show_notebook was called with boolean false experiment (%s), aborting...", experiment)
            return
        notebook, expid, experiment = self.add_notebook(experiment)
        notebook.lift() #http://effbot.org/tkinterbook/widget.htm#Tkinter.Widget.lift-method
        return notebook, expid, experiment
        # I found that it was indeed impossible to have only a single controller, as I would have to
        # also rebind e.g. ListSelect events etc.
        #self.FilemanagerController.FilemanagerFrame = notebook.filemanagerframe
        # alternative to lift is to use grid_remove to hide and grid() again to show
        # but lift() makes it easy to close one frame without worrying about showing the next and keeping track of frame z-positions manually.

    def load_experiment(self, experiment, show=True):
        if show:
            self.show_notebook(experiment)
        else:
            self.add_notebook(experiment)


    def get_expid_and_experiment(self, experiment):
        if isinstance(experiment, basestring):
            expid = experiment
            experiment = self.getExperimentManager().ExperimentsById[expid]
        elif isinstance(experiment, Experiment):
            expid = experiment.Props.get('expid')
        return expid, experiment



    def add_menus(self):
        # Make manubar and menus for main window.
        # Bonus info: contextual ("right click") menus can be created in a similar fashion :)
        self.menubar = tk.Menu(self) # create a tk menu bar
        self['menu'] = self.menubar # attach the menubar to
        menu_file = tk.Menu(self.menubar)
        menu_edit = tk.Menu(self.menubar)
        menu_other_global = tk.Menu(self.menubar)
        menu_fetch = tk.Menu(self.menubar)

        menu_help = tk.Menu(self.menubar, name='help')

        # cascade entries opens a new (sub)menu when selected
        self.menubar.add_cascade(menu=menu_file, label='File')
        self.menubar.add_cascade(menu=menu_edit, label='Edit')
        self.menubar.add_cascade(menu=menu_fetch, label='Fetch')
        self.menubar.add_cascade(menu=menu_other_global, label='Global functions')
        self.menubar.add_cascade(menu=menu_help, label='Help')

        # command entries will execute a command (function/method) when selected
        menu_file.add_command(label='Create new experiment...', command=self.createNewExperiment)
        menu_file.add_command(label='Select active experiments...', command=self.selectExperiments)
        menu_file.add_separator()
        menu_file.add_command(label='Exit', command=self.exitApp)


    #############################
    #### Callback methods  ######
    #############################

    def activeexps_contextmenu(self, event):
        menu = tk.Menu(self)
        menu.add_command(label='Close experiment')
        menu.add_command(label='Mark as complete')
        menu.add_command(label='Close & mark complete')



    def manageExperiments(self, event=None):
        logger.info("Opening ExperimentManagerWindow")
        experiment_selector_window = ExperimentManagerWindow(self.Confighandler)


    def selectExperiments(self, event=None):
        #print "Not implemented yet..."
        logger.info("Opening ExperimentSelectorWindow")
        experiment_selector_window = ExperimentSelectorWindow(self.Confighandler)


    def activeExpsChange(self, event=None):
        # I guess this is not really needed; this is managed via callbacks
        # in the confighandler.
        self.activeexps_list.reload()



    def connect_controllers(self):
        return
        self.ActiveExpListController = ActiveExpListBoxController(self.activeexps_list, self.Confighandler)
        self.RecentExpListController = RecentExpListBoxController(self.recentexps_list, self.Confighandler)
        # Hmm... een filemanager controller per aaben ExpNotebook? Eller bare een universal?
        # Well, med mindre du vil til at re-binde events hver gang et nyt eksperiment vises,
        # saa bor du nok have een controller for hver aaben ExpNotebook.
        #self.FilemanagerController = ExpFilemanagerController(self.Confighandler)


    def createNewExperiment(self, event=None):

        em = self.Confighandler.Singletons.get('experimentmanager')
        logger.info("Not implemented yet: createNewExperiment()")

        exp_idx = em.getNewExpid() if em else ''
        expid_fmt = self.Confighandler.get('expid_fmt')
        try:
            expid = expid_fmt.format(exp_series_index=exp_idx)
        except (TypeError, KeyError, AttributeError) as e:
            logger.warning("Failed to generate expid using format in config: %s", e)
            expid = ""

        #items are: variable, description, entry widget, kwargs for widget
        # edit:     ( key, description, value, kwargs_for_widget, entry_widget_class )
        entries = ( ('expid', "Experiment ID", expid),
                    ('exp_titledesc', "Experiment title desc", ""),
                    ('date', "Experiment date", "{:%Y%m%d}".format(datetime.now())),
                    ('makelocaldir', "Make local folder", True),
                    ('makewikipage', "Make wiki page", True),
                    )
        # casting to a mutable type...:
        fieldvars = OrderedDict( (key, [value, desc, dict()] ) for key,desc,value in entries )
        # dict with key : (value, description, tk-parameters-dict)
        # convert the value to a tk variable (the first item, index=0)
        for items in fieldvars.values(): # i.e. props[key] above
            if isinstance(items[0], bool):
                items[0] = tk.BooleanVar(value=items[0])
            else:
                items[0] = tk.StringVar(value=items[0])
        # to disable items:
        #fieldvars['expid'][2]['state'] = 'disabled'  # This is the third element, the dict.
        dia = Dialog(self, "Create new subentry", fieldvars)
        logger.debug(u"Dialog result: {}".format(dia.result))
        #subentry_titledesc, subentry_idx=None, subentry_date=None, ):
        #self.Experiment.addNewSubentry()
        if dia.result:
            # will be None if the 'ok' button was not pressed.
            # def addNewSubentry(self, subentry_titledesc, subentry_idx=None, subentry_date=None, extraprops=None, makefolder=False, makewikientry=False)
            #dia.result.pop('expid')
            logger.info("Create Experiment Dialog results: %s", dia.result)
            exp = self.getExperimentManager().addNewExperiment(**dia.result)
        logger.debug("Experiment created: %s", exp)

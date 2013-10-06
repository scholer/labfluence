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
#try:
#    import ttk

from model.confighandler import ExpConfigHandler
from model.experiment_manager import ExperimentManager
from model.experiment import Experiment
#from model.confighandler import ExpConfigHandler
#from model.confighandler import ExpConfigHandler
#from model.confighandler import ExpConfigHandler

from views.expnotebook import ExpNotebook, BackgroundFrame
from controllers.listboxcontrollers import ActiveExpListBoxController, RecentExpListBoxController

class LabfluenceGUI(object):
    """
    Note:
        -ActiveExperiments is a list of experiments that the user can modify himself, using the "Select..." functionality.
        -RecentExperiments is a list of the last 10 recently closed experiments; this is controlled soly by the app.
    """


    def __init__(self, confighandler=None, VERBOSE=5):
        #self.ActiveExperiments = list() # Probably better to use a property attribute
        #self.RecentExperiments = list()
        self.VERBOSE = VERBOSE
        self.Confighandler = confighandler or ExpConfigHandler(pathscheme='default1')
        self.Confighandler.Singletons.setdefault('app', self)
        if 'experimentmanager' not in self.Confighandler.Singletons:
            self.Confighandler.Singletons['experimentmanager'] = ExperimentManager(confighandler=self.Confighandler, autoinit=('localexps', ), VERBOSE=self.VERBOSE)
        self.init_ui()
        self.connect_controllers()
        self.Controllers = dict()
        self.ExpNotebooks = dict()


    # Properties, http://docs.python.org/2/library/functions.html#property
    # Note: Only works for new-style classes (which inherits from 'object').
    # Tkinter does not use new-style classes under python2.
    def getActiveExperiments(self):
        return self.Confighandler.setdefault('app_active_experiments', list())
    def setActiveExperiments(self, value):
        print "Setting (overwriting) the active experiments list is not allowed...  You can empty/clear it using del my_list[:] or mylist[:] = [] "
    def delActiveExperiments(self):
        print "Deleting the active experiments list is not allowed...  You can empty/clear it using del my_list[:] or mylist[:] = [] "
    ActiveExperiments = property(getActiveExperiments, setActiveExperiments, delActiveExperiments, "List of currently active experiments, obtained from confighandler.")
    # Alternative, using decorators:
    @property
    def RecentExperiments(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())
    @RecentExperiments.setter
    def RecentExperiments(self, value):
        print "Setting (overwriting) the recent experiments list is not allowed... You can empty/clear it using del my_list[:] or mylist[:] = [] "
    @RecentExperiments.deleter
    def RecentExperiments(self):
        print "Deleting the recent experiments list is not allowed... You can empty/clear it using del my_list[:] or mylist[:] = [] "

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


    def start_loop(self):
        self.tkroot.mainloop()

    def init_ui(self):
        self.tkroot = tk.Tk()
        self.tkroot.option_add('*tearOff', tk.FALSE)
        self.tkroot.title("Labfluence - Experiment Assistent")
        self.tkroot.columnconfigure(0, weight=1)
        self.tkroot.rowconfigure(0, weight=1)

        self.add_menus()

        # to create a new window:
        #win = tk.Toplevel(self.tkroot) # uh... I guess this will create a new toplevel window?

        self.mainframe = ttk.Frame(self.tkroot, padding="3 3 3 3") #"3 3 12 12"
        # Making sure main frame expands and fills everything, using the grid geometry manager:
        self.mainframe.grid(column=0, row=0, sticky="nsew") # position mainframe using grid gm.
        self.mainframe.columnconfigure(0, weight=1, minsize=180) # sets column "0" to weight "1".
        self.mainframe.columnconfigure(1, weight=5, minsize=500) # rightframe expands 5x more than leftframe
        self.mainframe.rowconfigure(1, weight=1) # expand row 1



        ######################
        #### LEFT FRAME ######
        ######################
        self.leftframe = ttk.Frame(self.mainframe)
        self.leftframe.grid(column=0, row=1, sticky="nsew") # position leftframe in column 0, row 1 in the outer (mainframe) widget.
        self.leftframe.columnconfigure(0, weight=1)
        self.leftframe.rowconfigure(0, weight=1) # distribute space evently between row 0 and row 1
        self.leftframe.rowconfigure(1, weight=1)

        # Active experiments frame
        self.activeexps_frame = ttk.Frame(self.leftframe)
        self.activeexps_frame.grid(column=0, row=0, sticky="nesw")
        self.activeexps_frame.rowconfigure(5, weight=1) # make the 5th row expand.
        self.activeexps_frame.columnconfigure(3, weight=2)
        self.activeexps_frame.columnconfigure(0, weight=0)
        # Active experiments widgets
        self.activeexps_list = tk.Listbox(self.activeexps_frame, height=16, activestyle='dotbox')
        #self.activeexps_list.bind('<<ListboxSelect>>', self.show_notebook ) # Will throw the event to the show_notebook
        self.activeexps_select_btn = ttk.Button(self.activeexps_frame, text="Select...", command=self.selectExperiments)
        self.activeexps_new_btn = ttk.Button(self.activeexps_frame, text="Create...", command=self.createNewExperiment)
        # you do not strictly need to be able to reference this from self.
        self.activeexps_label = ttk.Label(self.activeexps_frame, text="Active experiments:")
        # Active experiments widgets layout:
        self.activeexps_label.grid(column=1, row=0, columnspan=3, sticky="nw")
        self.activeexps_select_btn.grid(column=1, row=2)
        self.activeexps_new_btn.grid(column=2, row=2)
        self.activeexps_list.grid(column=0, row=5, columnspan=4, sticky="nesw")

        # Recent experiment frame
        self.recentexps_frame = ttk.Frame(self.leftframe)
        self.recentexps_frame.grid(column=0, row=1, sticky="nesw")
        self.recentexps_frame.rowconfigure(5, weight=1) # make the 5th row expand.
        self.recentexps_frame.columnconfigure(1, weight=1) # make the 5th row expand.
        # Recent experiments widgets
        self.recentexps_list = tk.Listbox(self.recentexps_frame, height=10, width=30)
        self.recentexps_label = ttk.Label(self.recentexps_frame, text="Recent experiments:")
        # Recent experiments widgets layout:
        self.recentexps_label.grid(column=0, row=0, columnspan=3, sticky="nw")
        self.recentexps_list.grid(column=0, row=5, columnspan=3, sticky="nesw")


        #####################
        #### RIGHT FRAME ####
        #####################
        # Question: Have only _one_ notebook which is updated when a new experiment is selected/loaded?
        # Or have several, one for each active experiment, which are then shown and hidden when the active experiment is selected?
        self.rightframe = ttk.Frame(self.mainframe)#, width=800, height=600)
        self.rightframe.grid(column=1, row=1, sticky="nsew")
        self.backgroundframe = BackgroundFrame(self.rightframe)
        self.backgroundframe.grid(column=0, row=1, sticky="nesw")
        #self.add_notebook()


    def add_notebook(self, experiment=None):
        #self.notebook = ttk.Notebook(self.rightframe)
        #self.notebook = expnotebook.ExpNotebook(self.rightframe)
        expid, experiment = self.get_expid_and_experiment(experiment)
        if expid not in self.ExpNotebooks:
            notebook = ExpNotebook(self.rightframe, experiment=experiment)
            notebook.grid(column=0, row=1, sticky="nesw")
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
        notebook, expid, experiment = self.add_notebook(experiment)
        notebook.lift() #http://effbot.org/tkinterbook/widget.htm#Tkinter.Widget.lift-method
        self.FilemanagerController.FilemanagerFrame = notebook.filemanagerframe
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
            experiment = self.ExperimentManager.ExperimentsById[expid]
        elif isinstance(experiment, Experiment):
            expid = experiment.Props.get('expid')
        return expid, experiment



    def add_menus(self):
        # Make manubar and menus for main window.
        # Bonus info: contextual ("right click") menus can be created in a similar fashion :)
        self.menubar = tk.Menu(self.tkroot) # create a tk menu bar
        self.tkroot['menu'] = self.menubar # attach the menubar to
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



    def activeexps_contextmenu(self):
        menu = tk.Menu(self.tkroot)
        menu.add_command(label='Close experiment')
        menu.add_command(label='Mark as complete')
        menu.add_command(label='Close & mark complete')



    def createNewExperiment(self):
        print "Not implemented yet..."

    def selectExperiments(self):
        #print "Not implemented yet..."
        experiment_selector_window = tk.Toplevel(self.tkroot)


    def exitApp(self):
        print "Not implemented yet..."



    def connect_controllers(self):
        self.ActiveExpListController = ActiveExpListBoxController(self.activeexps_list, self.Confighandler)
        self.RecentExpListController = RecentExpListBoxController(self.recentexps_list, self.Confighandler)
        # Hmm... én filemanager controller per åben ExpNotebook? Eller bare én universal?
        self.FilemanagerController = ExpFilemanagerController(self.Confighandler)





class ExperimentSelectorWidget():
    pass



# loading configurations:
# there are at least three locations for configs:
# - app dir
# - user home dir
# - experiment_root_dir

def find_user_home_config():
    pass

def find_configs():
    pass




if __name__ == '__main__':

    labfluencegui = LabfluenceGUI()
    confighandler = labfluencegui.Confighandler
    em = confighandler.Singletons.get('experimentmanager', None)
    if em:
        print "\nem.RecentExperiments:"
        print em.RecentExperiments
#    exps self.Confighandler.get('app_recent_experiments')
    print "Recent experiments:"
    print "\n".join( "-> {}".format(e) for e in labfluencegui.RecentExperiments )
    labfluencegui.start_loop()



"""


REFS:
* http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html
* http://effbot.org/tkinterbook (maybe a bit old...)


Other Confluence interface implementations:
* https://github.com/RaymiiOrg/confluence-python-cli/blob/master/confluence.py

"""

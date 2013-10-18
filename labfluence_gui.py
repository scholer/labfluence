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
#try:
#    import ttk

from model.confighandler import ExpConfigHandler
from model.experiment_manager import ExperimentManager
from model.experiment import Experiment
from model.server import ConfluenceXmlRpcServer

from views.expnotebook import ExpNotebook, BackgroundFrame
from controllers.listboxcontrollers import ActiveExpListBoxController, RecentExpListBoxController
from controllers.filemanagercontroller import ExpFilemanagerController
from ui.fontmanager import FontManager
import socket

class LabfluenceGUI(object):
    """
    Note:
        -ActiveExperiments is a list of experiments that the user can modify himself, using the "Select..." functionality.
        -RecentExperiments is a list of the last 10 recently closed experiments; this is controlled soly by the app.
    """


    def __init__(self, confighandler=None, VERBOSE=5):
        #self.ActiveExperiments = list() # Probably better to use a property attribute
        #self.RecentExperiments = list()
        print "\n\n\n>>>>>>>>>>>>>>  Starting init of LabfluenceGUI  >>>>>>>>>>>>>>>>\n"

        self.VERBOSE = VERBOSE
        self.Confighandler = confighandler or ExpConfigHandler(pathscheme='default1')
        self.Confighandler.Singletons.setdefault('app', self)
        if 'experimentmanager' not in self.Confighandler.Singletons:
            print "LabfluenceGUI.__init__ >> Instantiating new ExperimentManager!"
            self.Confighandler.Singletons['experimentmanager'] = ExperimentManager(confighandler=self.Confighandler, autoinit=('localexps', ), VERBOSE=self.VERBOSE)
        self.init_ui()
        self.init_fonts()
        self.connect_controllers()
        self.Controllers = dict()
        self.ExpNotebooks = dict()
        persisted_windowstate = self.Confighandler.get('tk_window_state', None)
        if persisted_windowstate == 'zoomed':
            self.tkroot.state('zoomed')
        persisted_windowgeometry = self.Confighandler.get('tk_window_geometry', None)
        if persisted_windowgeometry:
            try:
                self.tkroot.geometry(persisted_windowgeometry)
            except tk.TclError as e:
                print e



    # Properties, http://docs.python.org/2/library/functions.html#property
    # Note: Only works for new-style classes (which inherits from 'object').
    # Tkinter does not use new-style classes under python2.
    def getActiveExperimentIds(self):
        return self.Confighandler.setdefault('app_active_experiments', list())
    def setActiveExperimentIds(self, value):
        print "Setting (overwriting) the active experiments list is not allowed...  You can empty/clear it using del my_list[:] or mylist[:] = [] "
    def delActiveExperimentIds(self):
        print "Deleting the active experiments list is not allowed...  You can empty/clear it using del my_list[:] or mylist[:] = [] "
    ActiveExperimentIds = property(getActiveExperimentIds, setActiveExperimentIds, delActiveExperimentIds, "List of currently active experiments, obtained from confighandler.")
    # Alternative, using decorators:
    @property
    def RecentExperimentIds(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())
    @RecentExperimentIds.setter
    def RecentExperimentIds(self, value):
        print "Setting (overwriting) the recent experiments list is not allowed... You can empty/clear it using del my_list[:] or mylist[:] = [] "
    @RecentExperimentIds.deleter
    def RecentExperimentIds(self):
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
        return self.Confighandler.get('app_window_state', None)
    @WindowState.setter
    def WindowState(self, value):
        try:
            self.tkroot.state(value)
            self.Confighandler.setkey('app_window_state', value, 'user')
        except TclError as e:
            print e
    @property
    def WindowGeometry(self):
        return self.Confighandler.get('app_window_geometry', None)
    @WindowState.setter
    def WindowGeometry(self, value):
        try:
            self.tkroot.geometry(value)
            self.Confighandler.setkey('app_window_geometry', value, 'user')
        except TclError as e:
            print e

    ################
    ## BINDINGS ####
    ################

    def tk_window_configured(self):
        self.Confighandler.setkey('app_window_geometry', self.tkroot.geometry(), 'user')
        self.Confighandler.setkey('app_window_state', self.tkroot.state(), 'user')



    #####################
    ## STARTUP METHODS ##
    #####################
    def start_loop(self):
        self.tkroot.mainloop()

    def init_fonts(self):
        """
        Based on http://stackoverflow.com/questions/4072150/python-tkinter-how-to-change-a-widgets-font-style-without-knowing-the-widgets
        Valid specs: family, size, weight (bold/normal), slant (italic/roman), underline (bool), overstrike (bool).
        """
        self.Fontmanager = FontManager()
        self.CustomFonts = self.Fontmanager.CustomFonts

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
        self.leftframe = ttk.Frame(self.mainframe)
        self.activeexps_frame = ttk.Frame(self.leftframe)
        self.activeexps_list = tk.Listbox(self.activeexps_frame, height=16, activestyle='dotbox')
        self.activeexps_select_btn = ttk.Button(self.activeexps_frame, text="Select...", command=self.selectExperiments)
        self.activeexps_new_btn = ttk.Button(self.activeexps_frame, text="Create...", command=self.createNewExperiment)
        # you do not strictly need to be able to reference this from self.
        self.activeexps_label = ttk.Label(self.activeexps_frame, text="Active experiments:")
        self.recentexps_frame = ttk.Frame(self.leftframe)
        # Recent experiments widgets
        self.recentexps_list = tk.Listbox(self.recentexps_frame, height=10, width=30)
        self.recentexps_label = ttk.Label(self.recentexps_frame, text="Recent experiments:")
        # Question: Have only _one_ notebook which is updated when a new experiment is selected/loaded?
        # Or have several, one for each active experiment, which are then shown and hidden when the active experiment is selected?
        # I decided to go for one for each active experiment, and that was a really good decision!
        self.rightframe = ttk.Frame(self.mainframe)#, width=800, height=600)
        self.backgroundframe = BackgroundFrame(self.rightframe)


        # Making sure main frame expands and fills everything, using the grid geometry manager:
        self.mainframe.grid(column=0, row=0, sticky="nsew") # position mainframe using grid gm.
        self.mainframe.columnconfigure(0, weight=1, minsize=180) # sets column "0" to weight "1".
        self.mainframe.columnconfigure(1, weight=5, minsize=500) # rightframe expands 5x more than leftframe
        self.mainframe.rowconfigure(1, weight=1) # expand row 1

        ######################
        #### LEFT FRAME ######
        ######################
        self.leftframe.grid(column=0, row=1, sticky="nsew") # position leftframe in column 0, row 1 in the outer (mainframe) widget.
        self.leftframe.columnconfigure(0, weight=1)
        self.leftframe.rowconfigure(0, weight=1) # distribute space evently between row 0 and row 1
        self.leftframe.rowconfigure(1, weight=1)

        # Active experiments frame
        self.activeexps_frame.grid(column=0, row=0, sticky="nesw")
        self.activeexps_frame.rowconfigure(5, weight=1) # make the 5th row expand.
        self.activeexps_frame.columnconfigure(3, weight=2)
        self.activeexps_frame.columnconfigure(0, weight=0)
        # Active experiments widgets
        #self.activeexps_list.bind('<<ListboxSelect>>', self.show_notebook ) # Will throw the event to the show_notebook
        # Active experiments widgets layout:
        self.activeexps_label.grid(column=1, row=0, columnspan=3, sticky="nw")
        self.activeexps_select_btn.grid(column=1, row=2)
        self.activeexps_new_btn.grid(column=2, row=2)
        self.activeexps_list.grid(column=0, row=5, columnspan=4, sticky="nesw")

        # Recent experiment frame
        self.recentexps_frame.grid(column=0, row=1, sticky="nesw")
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


    def add_notebook(self, experiment):
        #self.notebook = ttk.Notebook(self.rightframe)
        #self.notebook = expnotebook.ExpNotebook(self.rightframe)
        expid, experiment = self.get_expid_and_experiment(experiment)
        if expid not in self.ExpNotebooks:
            notebook = ExpNotebook(self.rightframe, experiment)
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
        # Well, med mindre du vil til at re-binde events hver gang et nyt eksperiment vises,
        # så bør du nok have én controller for hver åben ExpNotebook.
        #self.FilemanagerController = ExpFilemanagerController(self.Confighandler)





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

    confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=0)
    try:
        server = ConfluenceXmlRpcServer(autologin=True, prompt='auto', ui=None, confighandler=confighandler, VERBOSE=0)
        confighandler.Singletons['server'] = server
    except socket.error:
        server = None
    manager = ExperimentManager(confighandler=confighandler, autoinit=('localexps', ), VERBOSE=0)
    confighandler.Singletons['experimentmanager'] = manager

    labfluencegui = LabfluenceGUI(confighandler=confighandler)
    # How to maximize / set window size:
    # http://stackoverflow.com/questions/15981000/tkinter-python-maximize-window
    # You can use tkroot.(wm_)state('zoomed') on windows to maximize. Does not work on unix.
    # You can bind tkroot.bind("<Configure>", method_handle)
    # This will invoke method_handle with event with attributes including width, height.

    #confighandler = labfluencegui.Confighandler
    #confighandler.VERBOSE = 0
    em = confighandler.Singletons.get('experimentmanager', None)
    if em:
        print "\nem.ActiveExperiments:"
        print em.ActiveExperiments
        print "\nem.RecentExperiments:"
        print em.RecentExperiments
#    exps self.Confighandler.get('app_recent_experiments')
    print "\nRecent experiments:"
    print "\n".join( "-> {}".format(e) for e in labfluencegui.RecentExperiments )
    print "\nActive experiments:"
    print "\n".join( "-> {}".format(e) for e in labfluencegui.ActiveExperiments )

    exps = labfluencegui.ActiveExperiments
    print "\n\nGUI init (almost) finished..."
    if exps:
        print "\n\nShowing exps: {}".format(exps[0])
        notebook, expid, experiment = labfluencegui.show_notebook(exps[0])
        #notebook.tab(1, state="enabled")
        #notebook.select(2)
    else:
        print "\n\nNo active experiments? -- {}".format(exps)

    labfluencegui.start_loop()



"""


REFS:
* http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html
* http://effbot.org/tkinterbook (maybe a bit old...)


Other Confluence interface implementations:
* https://github.com/RaymiiOrg/confluence-python-cli/blob/master/confluence.py

"""

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

from model import *
from views.expnotebook import ExpNotebook


class LabfluenceGUI():


    def __init__(self, globalconfig=None):
        self.ActiveExperiments = list()
        self.RecentExperiments = list()
        self.init_ui()
        if globalconfig is None:
            globalconfig = dict()
            




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
        self.activeexps_list = tk.Listbox(self.activeexps_frame, height=10)
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
        self.recentexps_list = tk.Listbox(self.recentexps_frame, height=10)
        self.recentexps_label = ttk.Label(self.recentexps_frame, text="Recent experiments:")
        # Recent experiments widgets layout:
        self.recentexps_label.grid(column=0, row=0, columnspan=3, sticky="nw")
        self.recentexps_list.grid(column=0, row=5, columnspan=3, sticky="nesw")


        #####################
        #### RIGHT FRAME ####
        #####################
        self.rightframe = ttk.Frame(self.mainframe)
        self.rightframe.grid(column=1, row=1, sticky="nsew")
        self.add_notebook()


    def add_notebook(self):
        
        #self.notebook = ttk.Notebook(self.rightframe)
        #self.notebook = expnotebook.ExpNotebook(self.rightframe)
        self.notebook = ExpNotebook(self.rightframe)
        self.notebook.grid(column=0, row=1, sticky="nesw")
        # overviewframe = ttk.Frame(self.notebook)
        # filesframe = ttk.Frame(self.notebook)
        # journalframe = ttk.Frame(self.notebook)
        # # Adding tabs (pages) to notebook
        # self.notebook.add(overviewframe, text="Overview")
        # self.notebook.add(filesframe, text="File management")
        # self.notebook.add(journalframe, text="Journal assistent")



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
    labfluencegui.start_loop()





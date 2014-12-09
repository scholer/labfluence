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
# pylint: disable-msg=R0901,R0902,C0103,R0904,W0201,W0613
"""
Module with a tk frame for displaying and editing an experiment's wiki page journal.
"""
# python 2.7:
import Tkinter as tk
import ttk
#import Tix # Lots of widgets, but tix is not being developed anymore, so only use if you really must.

from datetime import datetime
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

#from subentrieslistbox import SubentriesListbox
from explistboxes import SubentriesListbox #, FilelistListbox, LocalFilelistListbox, WikiFilelistListbox
from shared_ui_utils import ExperimentLink, ExpFrame
from dialogs import Dialog
from journalviewerframe import JournalViewer



class ExpJournalFrame(ExpFrame):
    """
    Frame displaying an experiment's wiki page journal.
    """
    #def __init__(self, parent, experiment, confighandler=None):
    #    ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
    #    self.grid(row=1, column=1, sticky="nesw")#, padx=50, pady=30)
    #    self.Experiment = experiment
    #    self.Confighandler = confighandler or dict() # Not sure this will ever be needed, probably better to always go through the experiment object...
    #    #self.PropVariables = dict()
    #    #self.App = self.Confighandler.Singletons['app']

    def frame_defaults(self):
        return dict(borderwidth=10)

    def init_variables(self):
        #print "\n\n\n-----------------------------\nExpJournalFrame.init_variables invoked !!\n---------------------------\n"
        self.Fonts = self.getFonts()
        # Init StringVars:
        v = ('wiki', 'cache', 'input', 'autoflush_interval', 'wiki_titledesc')
        self.Variables = dict((k, tk.StringVar()) for k in v )
        self.Variables['autoflush_interval'].set(self.Experiment.getConfigEntry('app_autoflush_interval', '10'))
        # Init BooleanVars:
        v = ('autoflush', )
        self.Boolvars = dict()# (k, tk.BooleanVar(value=False)) for k in v )
        self.Boolvars['autoflush'] = tk.BooleanVar(value=self.Experiment.getConfigEntry('app_autoflush_on', False))
        #self.Labels = dict()
        #self.Entries = dict()
        self.AutoflushAfterIdentifiers = list()
        #self.init_widgets()
        #self.init_layout()
        #self.init_bindings()

    def after_init(self):
        self.on_serverstatus_change()
        #print "\n\n\n-----------------------------\nExpJournalFrame.after_init invoked !!\n---------------------------\n"
        self.updatewidgets()
        logger.debug("%s, after_init finished, self.subentries_listbox.get(0, tk.END) is now: %s", self.__class__.__name__, self.subentries_listbox.get(0, last=tk.END))


    def init_widgets(self, ):
        # sub-frames:
        self.controlframe = ttk.Frame(self)
        #self.textframe = ttk.Frame(self)
        self.journalwikiframe = tk.Frame(self)#, bg='white')
        self.journalcacheframe = tk.Frame(self)#, bg='white')
        self.journalinputframe = ttk.Frame(self)
        self.cachecontrolsframe = ttk.Frame(self)

        # Other widgets:
        self.subentries_listbox = SubentriesListbox(self.controlframe, self.Experiment)
        #self.journalwiki_view = tk.Text(self.journalwikiframe, state='disabled', height=14)
        #self.journalcache_view = tk.Text(self.journalcacheframe, state='disabled', height=10)
        self.journalwiki_view = JournalViewer(self.journalwikiframe, self.Experiment, textopts=dict(height=10, width=60))
        self.journalcache_view = JournalViewer(self.journalcacheframe, self.Experiment, textopts=dict(height=6, width=60))
        #viewprops = dict(state='normal', bg='white', justify=tk.LEFT)
        #self.journalwiki_view = tk.Label(self.journalwikiframe, height=10, textvariable=self.Variables['wiki'], **viewprops)
        #self.journalcache_view = tk.Label(self.journalcacheframe, height=10, textvariable=self.Variables['cache'], **viewprops)
        self.journalentry_input = ttk.Entry(self.journalinputframe)

        # Minor control widgets and labels:
        # Headers:
        font_h3 = self.Fonts['header3']
        self.subentries_header = ttk.Label(self.controlframe, text="Select subentry:", font='header3', justify=tk.LEFT)
        self.wikiview_header = ttk.Label(self.journalwikiframe, text="Wiki journal:", font=font_h3, justify=tk.LEFT)
        self.cacheview_header = ttk.Label(self.cachecontrolsframe, text="Local cache:", font=font_h3, justify=tk.LEFT)
        #if 'url' in self.Experiment.Props:
        #    label = ttk.Label(self.cachecontrolsframe, text="Local cache:", font=font_h3, justify=tk.LEFT)
        logger.debug("Creating wiki page link, self.Experiment=%s", self.Experiment)
        self.wikiview_description = ExperimentLink(self.journalwikiframe, textvariable=self.Variables['wiki_titledesc'],
                                                   experiment=self.Experiment, urlmode='subentry')

        # Buttons:
        self.flush_btn = ttk.Button(self.cachecontrolsframe, text="Flush cache!", command=self.flushcache)
        self.flushall_btn = ttk.Button(self.controlframe, text="Flush cache for all subentries", command=self.flushallcaches)
        self.createnewsubentry_btn = ttk.Button(self.controlframe, text="Create new subentry", command=self.createnewsubentry)
        self.newwikipagesubentry_btn = ttk.Button(self.controlframe, text="Add section for selected", # "Create selected"
                                                command=self.insert_section_for_selected_subentry, state='disabled') # newwikipagesubentry

        # Other option input:
        self.autoflush_frame = ttk.Frame(self.controlframe)
        self.autoflushall_chkbtn = ttk.Checkbutton(self.autoflush_frame, text="Autoflush every ",
                                                   command=self.autoflush_changed, variable=self.Boolvars['autoflush'])
        self.autoflushinterval_spinbox = tk.Spinbox(self.autoflush_frame, from_=3, to=120, width=3,
                                                    command=self.autoflush_changed, textvariable=self.Variables['autoflush_interval'])
        self.autoflushinterval_lbl = ttk.Label(self.autoflush_frame, text=" minutes")
        #self.autoflushinterval_spinbox.configure()

        ## scrollbars:
        #self.journalwiki_scrollbar = ttk.Scrollbar(self.journalwikiframe)
        #self.journalcache_scrollbar = ttk.Scrollbar(self.journalcacheframe)


    def init_layout(self):

        self.columnconfigure(1, weight=1, minsize=200)
        self.columnconfigure(2, weight=2)
        self.rowconfigure((1, 3), weight=2)
        self.rowconfigure(4, weight=1)

        # Direct children:
        self.controlframe.grid(row=1, column=1, rowspan=2, sticky="nesw", padx=5)
        self.journalwikiframe.grid(row=1, column=2, sticky="nesw")
        self.cachecontrolsframe.grid(row=2, column=2, sticky="nesw")
        self.journalcacheframe.grid(row=3, column=2, sticky="nesw")
        self.journalinputframe.grid(row=4, column=2, sticky="nesw")

        # Make the sub-frames expand:
        self.controlframe.columnconfigure(1, weight=1)
        self.controlframe.rowconfigure(2, weight=1)
        self.journalwikiframe.columnconfigure(3, weight=1)
        self.journalwikiframe.rowconfigure(1, weight=1)
        self.cachecontrolsframe.columnconfigure(2, weight=1)
        self.cachecontrolsframe.rowconfigure(1, weight=1)
        self.journalcacheframe.columnconfigure(1, weight=1)
        self.journalcacheframe.rowconfigure(1, weight=1)
        self.journalinputframe.columnconfigure(1, weight=1)
        self.journalinputframe.rowconfigure(1, weight=1)


        # Control-frame widgets:
        self.subentries_header.grid(row=1, column=1, sticky="nw", columnspan=2)
        self.subentries_listbox.grid(row=2, column=1, sticky="news", columnspan=2)
        self.createnewsubentry_btn.grid(row=3, column=1, sticky="ew")
        self.newwikipagesubentry_btn.grid(row=3, column=2, sticky="ew")
        self.flushall_btn.grid(row=4, column=1, sticky="nwe", columnspan=2)
        self.autoflush_frame.grid(row=6, column=1, sticky="w", columnspan=2)
        # These are in self.autoflush_frame:
        self.autoflushall_chkbtn.grid(row=6, column=1, sticky="w")
        self.autoflushinterval_spinbox.grid(row=6, column=2, sticky="w")
        self.autoflushinterval_lbl.grid(row=6, column=3, sticky="w")


        # wiki-frame widgets:
        self.wikiview_header.grid(row=0, column=1, sticky="nw")
        self.wikiview_description.grid(row=0, column=2)
        self.journalwiki_view.grid(row=1, column=1, columnspan=3, sticky="nesw")
        #self.journalwiki_scrollbar.grid(row=1, column=4, sticky="nes")

        # cache-controls frame widgets:
        self.cacheview_header.grid(row=1, column=1)
        self.flush_btn.grid(row=1, column=3)#, sticky="nsew")

        # cacheframe widgets:
        self.journalcache_view.grid(row=1, column=1, sticky="nesw")
        #self.journalcache_scrollbar.grid(row=1, column=2, sticky="nes")

        # Journalentry widgets:
        self.journalentry_input.grid(row=1, column=1, sticky="nsew")


    def init_bindings(self):
        # Cross-widget dependencies/bindings:
        #self.journalwiki_view.config(yscrollcommand=self.journalwiki_scrollbar.set)
        #self.journalwiki_scrollbar.config(command=self.journalwiki_view.yview)
        #self.journalcache_view.config(yscrollcommand=self.journalcache_scrollbar.set)
        #self.journalcache_scrollbar.config(command=self.journalcache_view.yview)

        # Input / keypresses:
        self.subentries_listbox.bind('<<ListboxSelect>>', self.on_subentry_select)
        self.journalentry_input.bind('<Return>', self.add_entry)
        #self.autoflushinterval_spinbox.bind('<Return>', self.autoflush_changed)
        self.autoflushinterval_spinbox.bind('<<Modified>>', self.autoflush_changed)
        self.getConfighandler().registerEntryChangeCallback('wiki_server_status', self.on_serverstatus_change)

    def updatewidgets(self):
        """
        Updates all child widgets contained within this widget.
        """
        self.subentries_listbox.updatelist()
        logger.debug("%s, subentries_listbox updated, subentries_listbox.get(0, tk.END) is now: %s", self.__class__.__name__, self.subentries_listbox.get(0, last=tk.END))
        self.update_cacheview()
        self.update_wikititledesc()
        self.update_wikiview()

    def update_wikiview(self):
        """
        Update the view displaying the subentry within the wiki page.
        """
        xhtml = self.journalwiki_view.update_wiki_subentry()
        #subentrywiki_btns = (self.newwikipagesubentry_btn, self.flush_btn)
        #for button in subentrywiki_btns:
        if xhtml:
            self.newwikipagesubentry_btn['state'] = 'disabled'
            self.flush_btn['state'] = 'normal'
        else:
            self.newwikipagesubentry_btn['state'] = 'normal'
            self.flush_btn['state'] = 'disabled'

    def update_cacheview(self):
        """
        Updates the view displaying the JournalAssistant's cache.
        """
        # Label-like view with variable:
        #ja = self.Experiment.JournalAssistant
        #cache = ja.getCacheContent()
        #self.Variables['cache'].set(cache)
        self.journalcache_view.update_cache()

    def update_wikititledesc(self, ):
        """
        Updates the title, reflecting which subentry is selected.
        """
        v = self.Variables['wiki_titledesc']
        ja = self.Experiment.JournalAssistant
        titledesc = self.Experiment.getSubentryRepr(subentry_idx=ja.Current_subentry_idx, default="exp")
        logger.debug("Title desc: '%s'", titledesc)
        v.set(titledesc)


    def on_subentry_select(self, event):
        """
        Called when the user selects a subentry in the subentry list.
        """
        selectedsubentries = self.subentries_listbox.getSelectedSubentryIdxs()
        if not selectedsubentries:
            logger.debug("No subentries selected: %s", selectedsubentries)
            return
        subentry = selectedsubentries[0]
        logger.debug("Switching to subentry '%s'", subentry)
        ja = self.Experiment.JournalAssistant
        ja.Current_subentry_idx = subentry
        self.update_cacheview()
        self.update_wikiview()
        self.update_wikititledesc()

    def add_entry(self, event):
        """
        Used to add the content of the line-input to the JournalAssistant's cache,
        invoked when enter is hit.
        """
        logger.debug("ExpJournalFrame.add_entry() invoked.")
        new_entry = self.journalentry_input.get()
        ja = self.Experiment.JournalAssistant
        res = ja.addEntry(new_entry)
        logger.debug("ExpJournalFrame.add_entry() :: res = '%s'", res)
        if res:
            self.journalentry_input.delete(0, tk.END)
        self.update_cacheview()

    def flushcache(self, event=None):
        """
        Triggers JA.flush().
        Invoked when pressing the "flush" button, or automatically according to timer.
        """
        logger.debug("ExpJournalFrame.flushcache() invoked, flushing journal-assistant cache for exp '%s'", self.Experiment)
        res = self.Experiment.JournalAssistant.flush()
        logger.debug("%s :: res is %s", self.__class__.__name__, "dict with keys: {}".format(res.keys()) if hasattr(res, 'keys') else "type: {}".format(type(res)))
        self.update_cacheview()
        self.update_wikiview()

    def flushallcaches(self):
        """
        Used to make sure the cache of all entries are flushed.
        Invoked by button with similar text.
        """
        ja = self.Experiment.JournalAssistant
        res = ja.flushAll()
        self.autoflush_reset()
        self.update_cacheview()
        self.update_wikiview()



    def autoflush_interval_var_write(self, varname, index, mode):
        """
        Variable Trace based callback,
        is called when autoflush_interval tk.StringVar is set (written).
        Alternative approach to control widget event binding,
        binds directly to changes to the tk Variables.
        C.f. http://www.astro.washington.edu/users/rowen/ROTKFolklore.html
        """
        varValue = self.root.globalgetvar(varname)
        self.Experiment.setConfigEntry('app_autoflush_interval', varValue)

    def autoflush_var_write(self, varname, index, mode):
        varValue = self.root.globalgetvar(varname)
        self.Experiment.setConfigEntry('app_autoflush_on', varValue)

    def autoflush_changed(self):
        """
        Called when the autoflush interval value is changed to update the config.
        """
        self.autoflush_reset()
        self.Experiment.setConfigEntry('app_autoflush_interval', self.Variables['autoflush_interval'].get())
        self.Experiment.setConfigEntry('app_autoflush_on', bool(self.Boolvars['autoflush'].get()))
        self.Experiment.Confighandler.saveConfigForEntry('app_autoflush_on') # Probably not required, should be saved on normal app exit.

    def autoflush_reset(self):
        """
        Resets the autoflush timer.
        """
        for identifier in self.AutoflushAfterIdentifiers:
            self.after_cancel(identifier)
            logger.debug("afterTimer with id '%s' cancelled...", identifier)
        del self.AutoflushAfterIdentifiers[:]
        if not self.Boolvars['autoflush'].get():
            logger.debug("Autoflush not active (due to checkbox...)")
            return
        mins = int(self.Variables['autoflush_interval'].get())
        after_identifier = self.after(mins*60*1000, self.flushallcaches)
        self.AutoflushAfterIdentifiers.append(after_identifier)
        logger.debug("New afterTimer with id %s added for self.flushallcaches in %s ms", after_identifier, mins*60*1000)
        return after_identifier


    def on_serverstatus_change(self, ):
        """
        Invoked when the server's status changes.
        Invoked through the callback system in the confighandler.
        """
        statewidgets = (
                        self.wikiview_description,
                        self.flush_btn,
                        self.flushall_btn,
                        self.createnewsubentry_btn,
                        self.newwikipagesubentry_btn,
                        self.autoflushall_chkbtn,
                       )
        bgcolorwidgets = (
                          self.journalwiki_view.text,
                          )
        if self.Experiment.Server:
            bgcolor = 'white'
            state = 'normal'
        else:
            bgcolor = 'gray'
            state = 'disabled'
        for widget in statewidgets:
            widget.config(state=state)
        for widget in bgcolorwidgets:
            widget.config(bg=bgcolor)





    def createnewsubentry(self, event=None):
        """
        Invoked when the button with same text is pressed.

        Implemented using a the very generic dialog box.
        This takes a "fieldvars" argument. This is an ordered dict of:
            key : [ Variable, description, kwargs ]
        The kwargs dict is passed on to the constructor and can be used to e.g.
        change states of input widgets.
        The default Dialog class will make a two-column grid, where the left
        column in each row is a label with the description and the right column is the input/control widget.
        The input widgets will adapt to the variable type:
        Checkboxes will be used for tk.BooleanVars.
        The dialog will additionally try to adapt the layout.
        For example, for booleanvars displayed by checkboxes, the grid can fit two variables side-by-side,
        one in each column.

        The results of the user input after clicking 'ok' can be read in two ways, either
        a) Using the tk.Variables in the fieldvars dict (requires you to use tk Variables)
        b) Using the values in dialog.result, which are updated when the user presses 'ok'.

        Note that dialog.result is a dict of
            key: value
        pairs, where the value is obtained by invoking tkVar.get(). The key is the same as that of the fieldvars input.

        """
        idx = self.Experiment.getNewSubentryIdx()
        props = dict(self.Experiment.Props)
        props['subentry_idx'] = idx
        props['subentry_titledesc'] = ""
        props['subentry_date'] = "{:%Y%m%d}".format(datetime.now())
        props['makefolder'] = True
        props['makewikientry'] = True
        #items are: variable, description, entry widget, kwargs for widget
        entries = ( ('expid', "Experiment ID"),
                    ('subentry_idx', "Subentry index"),
                    ('subentry_titledesc', "Subentry title desc"),
                    ('makefolder', "Make local folder"),
                    ('makewikientry', "Make wiki entry"),
                    ('subentry_date', "Subentry date")
                    )
        fieldvars = OrderedDict( (key, [props[key], desc, dict()] ) for key, desc in entries )
        for items in fieldvars.values():
            if isinstance(items[0], bool):
                items[0] = tk.BooleanVar(value=items[0])
            else:
                items[0] = tk.StringVar(value=items[0])
        fieldvars['expid'][2]['state'] = 'disabled'  # This is the third element, the dict.
        dia = Dialog(self, "Create new subentry", fieldvars)
        logger.debug("Dialog result: %s", dia.result)
        if dia.result:
            # will be None if the 'ok' button was not pressed.
            dia.result.pop('expid')
            self.Experiment.addNewSubentry(**dia.result)

        # I'm not sure how much clean-up should be done? Do I need to e.g. destroy the dialog completely when I'm done?
        self.Parent.updatewidgets() # will also invoke self.updatewidgets()



    def insert_section_for_selected_subentry(self):
        """
        Inserts a new subentry section on the wiki page,
        and update the required widgets to reflect the
        update to the wiki page.
        """
        current_subentry_idx = self.Experiment.JournalAssistant.Current_subentry_idx
        if not current_subentry_idx:
            logger.info("insert_section_for_selected_subentry() invoked, but the registered Current_subentry_idx in JournalAssistant is: %s", current_subentry_idx)
            return
        res = self.Experiment.JournalAssistant.newExpSubentry(current_subentry_idx)
        if res:
            logger.debug("Updated page to version %s", res['version'])
            self.update_wikiview()
            if hasattr(self.Parent, 'update_info'):
                self.Parent.update_info()
        else:
            logger.info("self.Experiment.JournalAssistant.newExpSubentry(current_subentry_idx) returned '%s", res)

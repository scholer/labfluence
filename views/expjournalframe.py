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
import Tix # Lots of widgets, but tix is not being developed anymore, so only use if you really must.

import htmllib, formatter

from subentrieslistbox import SubentriesListbox
from shared_ui_utils import HyperLink
from rspysol.rstkhtml import tkHTMLParser, tkHTMLWriter

class ExpJournalFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        self.grid(row=1, column=1, sticky="nesw")#, padx=50, pady=30)
        self.Experiment = experiment
        self.Confighandler = confighandler or dict() # Not sure this will ever be needed, probably better to always go through the experiment object...
        #self.PropVariables = dict()
        self.App = self.Confighandler.Singletons['app']
        self.Fonts = self.App.CustomFonts
        v = ('wiki','cache','input', 'autoflush_interval', 'wiki_titledesc')
        self.Variables = dict( (k, tk.StringVar()) for k in v )
        self.Variables['autoflush_interval'].set(self.Confighandler.get('app_autoflush_interval', '10'))
        v = ('autoflush',)
        self.Boolvars = dict()# (k, tk.BooleanVar(value=False)) for k in v )
        self.Boolvars['autoflush'] = tk.BooleanVar( value=self.Confighandler.get('app_autoflush_on', False) )
        self.Labels = dict()
        self.Entries = dict()
        self.AutoflushAfterIdentifiers = list()
        self.init_widgets()
        self.init_layout()
        self.init_bindings()
        self.updatewidgets()


    def init_widgets(self, ):
        # sub-frames:
        self.controlframe = ttk.Frame(self)
        #self.textframe = ttk.Frame(self)
        self.journalwikiframe = tk.Frame(self)#, bg='white')
        self.journalcacheframe = tk.Frame(self)#, bg='white')
        self.journalinputframe = ttk.Frame(self)
        self.cachecontrolsframe = ttk.Frame(self)

        # Other widgets:
        self.subentries_listbox = SubentriesListbox(self.controlframe, self.Experiment, self.Confighandler)
        #self.journalwiki_view = tk.Text(self.journalwikiframe, state='disabled', height=14)
        #self.journalcache_view = tk.Text(self.journalcacheframe, state='disabled', height=10)
        self.journalwiki_view  = JournalViewer(self.journalwikiframe, self.Experiment, state='disabled', height=10)
        self.journalcache_view = JournalViewer(self.journalcacheframe, self.Experiment, state='disabled', height=10)
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
        self.wikiview_description = HyperLink(self.journalwikiframe, textvariable=self.Variables['wiki_titledesc'],
                                              #uri=self.Experiment.Props.get('url', None) )
                                              experiment=self.Experiment)

        # Buttons:
        self.flush_btn = ttk.Button(self.cachecontrolsframe, text="Flush cache!", command=self.flushcache)
        self.flushall_btn = ttk.Button(self.controlframe, text="Flush cache for all subentries", command=self.flushallcaches)

        # Other option input:
        self.autoflushall_chkbtn = ttk.Checkbutton(self.controlframe, text="Autoflush every x mins:",
                                                   command=self.autoflush_reset, variable=self.Boolvars['autoflush'])
        self.autoflushinterval_spinbox = tk.Spinbox(self.controlframe, from_=3, to=120, width=3,
                                                    command=self.autoflush_reset, textvariable=self.Variables['autoflush_interval'])
        #self.autoflushinterval_spinbox.configure()

        # scrollbars:
        self.journalwiki_scrollbar = ttk.Scrollbar(self.journalwikiframe)
        self.journalcache_scrollbar = ttk.Scrollbar(self.journalcacheframe)


    def init_layout(self):

        self.columnconfigure(1, weight=1, minsize=200)
        self.columnconfigure(2, weight=2)
        self.rowconfigure((1,3), weight=2)
        self.rowconfigure(4, weight=1)

        # Direct children:
        self.controlframe.grid(row=1, column=1, rowspan=2, sticky="nesw", padx=5)
        self.journalwikiframe.grid(row=1, column=2, sticky="nesw")
        self.cachecontrolsframe.grid(row=2, column=2, sticky="nesw")
        self.journalcacheframe.grid(row=3, column=2, sticky="nesw")
        self.journalinputframe.grid(row=4, column=2, sticky="nesw")

        # Make the sub-frames expand:
        self.controlframe.columnconfigure(1, weight=1)
        self.controlframe.rowconfigure(3, weight=1)
        self.journalwikiframe.columnconfigure(3, weight=1)
        self.journalwikiframe.rowconfigure(1, weight=1)
        self.cachecontrolsframe.columnconfigure(2, weight=1)
        self.cachecontrolsframe.rowconfigure(1, weight=1)
        self.journalcacheframe.columnconfigure(1, weight=1)
        self.journalcacheframe.rowconfigure(1, weight=1)
        self.journalinputframe.columnconfigure(1, weight=1)
        self.journalinputframe.rowconfigure(1, weight=1)


        # Control-frame widgets:
        self.subentries_header.grid(row=1, column=1, sticky="nw")
        self.subentries_listbox.grid(row=3, column=1, sticky="news")
        self.flushall_btn.grid(row=4, column=1, sticky="nwe")
        self.autoflushall_chkbtn.grid(row=6, column=1, sticky="w")
        self.autoflushinterval_spinbox.grid(row=6, column=1, sticky="e")

        # wiki-frame widgets:
        self.wikiview_header.grid(row=0, column=1, sticky="nw")
        self.wikiview_description.grid(row=0, column=2)
        self.journalwiki_view.grid(row=1, column=1, columnspan=3, sticky="nesw")
        self.journalwiki_scrollbar.grid(row=1, column=4, sticky="nes")

        # cache-controls frame widgets:
        self.cacheview_header.grid(row=1, column=1)
        self.flush_btn.grid(row=1, column=3)#, sticky="nsew")

        # cacheframe widgets:
        self.journalcache_view.grid(row=1, column=1, sticky="nesw")
        self.journalcache_scrollbar.grid(row=1, column=2, sticky="nes")

        # Journalentry widgets:
        self.journalentry_input.grid(row=1, column=1, sticky="nsew")


    def init_bindings(self):
        # Cross-widget dependencies/bindings:
        self.journalwiki_view.config(yscrollcommand=self.journalwiki_scrollbar.set)
        self.journalwiki_scrollbar.config(command=self.journalwiki_view.yview)
        self.journalcache_view.config(yscrollcommand=self.journalcache_scrollbar.set)
        self.journalcache_scrollbar.config(command=self.journalcache_view.yview)

        # Input / keypresses:
        self.subentries_listbox.bind('<<ListboxSelect>>', self.on_subentry_select)
        self.journalentry_input.bind('<Return>', self.add_entry)
        #self.autoflushinterval_spinbox.bind('<Return>', self.autoflush_reset)
        self.autoflushinterval_spinbox.bind('<<Modified>>', self.autoflush_reset)

    def updatewidgets(self):
        self.subentries_listbox.updatelist()
        self.update_cacheview()
        self.update_wikititledesc()
        self.update_wikiview()

    def update_wikiview(self):
        print "Not implemented"
        self.journalwiki_view.update_wiki()

    def update_cacheview(self):
        # Label-like view with variable:
        #ja = self.Experiment.JournalAssistant
        #cache = ja.getCacheContent()
        #self.Variables['cache'].set(cache)
        self.journalcache_view.update_cache()

    def update_wikititledesc(self, ):
        v = self.Variables['wiki_titledesc']
        ja = self.Experiment.JournalAssistant
        titledesc = self.Experiment.getSubentryRepr(subentry_idx=ja.Current_subentry_idx, default="exp")
        print "Title desc: '{}'".format(titledesc)
        v.set(titledesc)


    def on_subentry_select(self, event):
        selectedsubentries = self.subentries_listbox.getSelectedSubentryIdxs()
        if not selectedsubentries:
            print "No subentries selected: {}".format(selectedsubentries)
            return
        subentry = selectedsubentries[0]
        print "Switching to subentry '{}'".format(subentry)
        ja = self.Experiment.JournalAssistant
        ja.Current_subentry_idx = subentry
        self.update_cacheview()
        self.update_wikiview()
        self.update_wikititledesc()

    def add_entry(self, event):
        print "ExpJournalFrame.add_entry() invoked."
        new_entry = self.journalentry_input.get()
        ja = self.Experiment.JournalAssistant
        res = ja.addEntry(new_entry)
        print "ExpJournalFrame.add_entry() :: res = '{}'".format(res)
        if res:
            self.journalentry_input.delete(0, tk.END)
        self.update_cacheview()

    def flushcache(self, event=None):
        print "ExpJournalFrame.flushcache() invoked."
        res = self.Experiment.JournalAssistant.flush()
        print "ExpJournalFrame.flushcache() :: res = '{}'".format(res)
        self.update_cacheview()
        self.update_wikiview()

    def flushallcaches(self):
        ja = self.Experiment.JournalAssistant
        res = ja.flushAll()
        self.autoflush_reset()
        self.update_cacheview()
        self.update_wikiview()


    def autoflush_reset(self):
        for identifier in self.AutoflushAfterIdentifiers:
            self.after_cancel(identifier)
            print "afterTimer with id '{}' cancelled...".format(identifier)
        del self.AutoflushAfterIdentifiers[:]
        if not self.Boolvars['autoflush'].get():
            print "Autoflush not active (due to checkbox...)"
            return
        mins = int(self.Variables['autoflush_interval'].get())
        after_identifier = self.after(mins*60*1000, self.flushallcaches)
        self.AutoflushAfterIdentifiers.append(after_identifier)
        print "New afterTimer with id {} added for self.flushallcaches in {} ms".format(after_identifier, mins*60*1000)
        self.Confighandler.setkey('app_autoflush_interval', self.Variables['autoflush_interval'].get() )
        self.Confighandler.setkey('app_autoflush_on', bool(self.Boolvars['autoflush'].get()))


class JournalViewer(tk.Text):

    def __init__(self, parent, experiment, scrollbar=None, **options):
        opts = dict(state='disabled', width=60)
        opts.update(options)
        tk.Text.__init__(self, parent, **opts)
        self.Experiment = experiment
        self.JA = experiment.JournalAssistant
        self.Parent = parent


    def update_cache(self):
        """
        Sets the value of the text widget to the journal-assistant cache for the currently selected subentry:
        """
        cache = self.JA.getCacheContent()
        self.set_value(cache)

    def update_wiki(self):
        """
        Sets the value of the text widget to the journal-assistant cache for the currently selected subentry:
        """
        print "JournalViewer.update_wiki() - Not implemented..."
        #html = self.Experiment.getWikiSubentryXhtml(self)
        html = "<h1>This is a header 1</h1><h4>RSNNN header</h4><p>Here is a description of RSNNN</p><h6>journal, date</h6><p>More text</p>"
        print 'self["font"] is: {}'.format(self["font"])
        print "html is:"
        print html

        # prepare the text widget:
        self.config(state="normal")
        self.delete("1.0", "end")
        self.update_idletasks()

        # Write the html to the text widget:
        writer = tkHTMLWriter(self)
        fmt = formatter.AbstractFormatter(writer)
        parser = tkHTMLParser(fmt)
        parser.feed(html)
        parser.close()

        self.config(state="disabled")


    def set_value(self, value):
        #initial_state = self.configure()['state'][4]
        initial_state = self.cget('state')
        self.configure(state='normal')
        if self.get('1.0', tk.END):
            self.delete('1.0', tk.END)
        if value:
            self.insert('1.0', value)
        self.configure(state='disabled')
        self.see(tk.END)

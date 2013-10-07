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



class ExpOverviewFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        self.grid(row=1, column=1, sticky="nesw")#, padx=50, pady=30)
        self.Experiment = experiment
        #self.Confighandler = confighandler # Not sure this will ever be needed, probably better to always go through the experiment object...
        self.PropVariables = dict()
        self.DynamicVariables = dict()
        self.Labels = dict()
        self.Entries = dict()

        entries = ( ('expid', 'Experiment ID'),
                    ('exp_titledesc', 'Title desciption'),
                    ('wiki_pageId', 'Wiki PageId'),
                    ('wiki_pagetitle', 'Wiki PageTitle')
                    ,('lastsaved', 'Info last saved')
                    #,('', '')
                  )

        startrow = 2

        for r,(key,desc) in enumerate(entries, startrow):
            var = self.PropVariables[key] = tk.StringVar()
            self.Labels[key] = label = ttk.Label( self, text=desc+":", justify=tk.LEFT)
            label.grid(column=1, row=r, sticky="nsew")
            self.Entries[key] = entry = ttk.Entry(self, textvariable=var, state='readonly', justify=tk.RIGHT)
            entry.grid(column=2, row=r)

        r = startrow + len(entries) + 1
        # Subentries:
        self.DynamicVariables['subentries'] = var = tk.StringVar()
        self.update_subentries()
        label = ttk.Label(self, text="Experiment subentries:", justify=tk.LEFT)
        label.grid(column=1, row=r, columnspan=2, sticky="nsew")
        r += 1
        label = ttk.Label(self, textvariable=var, justify=tk.LEFT, state='readonly')
        label.grid(column=1, row=r, columnspan=2, rowspan=2, sticky="nsew")

        self.update_properties()

    def update_subentries(self):
        var = self.DynamicVariables['subentries']
        expid = self.Experiment.Props.get('expid', "")
        subentries = self.Experiment.Props.get('exp_subentries', None)
        if subentries:
            var.set('\n'.join("- {expid}{subentry_idx} {subentry_titledesc}".format(**dict(dict(expid=expid,
                subentry_idx='', subentry_titledesc=''), **subentry)) for idx,subentry in subentries.items() ))

    def update_properties(self):
        for key, tkvar in self.PropVariables.items():
            new_val = self.Experiment.Props.get(key)
            if new_val:
                tkvar.set(new_val)

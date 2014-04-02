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
#import Tix # Lots of widgets, but tix is not being developed anymore, so only use if you really must.
import logging
logger = logging.getLogger(__name__)


from shared_ui_utils import ExpFrame


class ExpOverviewFrame(ExpFrame):
    """
    """
    #def __init__(self, parent, experiment)#, confighandler=None):
    #    ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
    #    self.Parent = parent
    #    self.Experiment = experiment
    #    # Edit: widgets should not have access to confighandler.
    #    # If they need a config entry, they should use experiment.getConfigEntry(key).
    #    self.Labels = dict()
    #    self.Entries = dict()
    #    self.Frames = dict()
    #    self.init_layout()

    def before_init(self, kwargs):
        self.NoWikipageFound = None

    def frame_defaults(self, ):
        return dict(borderwidth=10)

    def init_layout(self):
        currow = 2
        f = self.ControlFrame = ttk.Frame(self)
        f.grid(row=currow, column=1, sticky="news")
        currow += 1
        curcol = 1
        b = self.closebtn = ttk.Button(f, command=self.closeAndArchive, text="Close and archive experiment", state=self.statebyisactive() )
        b.grid(row=1, column=curcol, sticky="nw")
        curcol += 1
        b = self.hidenotebookbtn = ttk.Button(f, command=self.hidenotebook, text="Close notebook")
        b.grid(row=1, column=curcol, sticky="nw")
        curcol += 1
        b = self.updatebtn = ttk.Button(f, command=self.update_variables, text="Update info")
        b.grid(row=1, column=curcol, sticky="nw")
        curcol += 1
        b = self.savepropsbtn = ttk.Button(f, command=self.saveprops, text="Save props now!")
        b.grid(row=1, column=curcol, sticky="nw")
        curcol += 1
        b = self.wikipagebtn = ttk.Button(f, command=self.wikipage_lookup, text="Look up wikipage", state=self.statebynowikipageid() )
        b.grid(row=1, column=curcol, sticky="nw")
        curcol += 1
        b = self.createwikipagebtn = ttk.Button(f, command=self.create_wikipage, text="Create wikipage", state=self.statebywikipagecreate() )
        b.grid(row=1, column=curcol, sticky="nw")
        curcol += 1


        self.AttrFrame = self.Frames['attr'] = f = ExpAttrFrame(self, self.Experiment)
        f.grid(row=currow, column=1, sticky="nesw")
        currow += 1

        self.PropsFrame = self.Frames['props'] = f = ExpPropsFrame(self, self.Experiment)
        f.grid(row=currow, column=1, sticky="nesw")
        currow += 1

        self.SubentriesFrame = self.Frames['subentries'] = f = ExpSubentriesFrame(self, self.Experiment)
        f.grid(row=currow, column=1, sticky="nesw")
        currow += 1

        self.WikiPageInfoFrame = self.Frames['wikipageinfo'] = f = ExpWikiPageStructFrame(self, self.Experiment)
        f.grid(row=currow, column=1, sticky="nesw")
        currow += 1

        self.columnconfigure(1, weight=1)

    def init_bindings(self):
        ch = self.getConfighandler()
        if ch:
            ch.registerEntryChangeCallback('app_active_experiments', self.activeExpsChange)

    def update_variables(self):
        for frame in self.Frames.values():
            frame.update_variables()

    def updatewidgets(self, ):
        # alias for update_variables...
        self.update_variables()


    def hidenotebook(self, event=None):
        #self.Parent.hide(event) # nope, Notebook.hide takes a <tab-id> and hides the corresponding tab.
        self.Parent.lower()

    def closeAndArchive(self, event=None):
        self.Parent.lower()
        self.Experiment.archive()

    def wikipage_lookup(self):
        wikipage = self.Experiment.attachWikiPage(dosearch=4)
        if wikipage:
            self.update_variables()
            self.saveprops()
            return wikipage
        # else, perhaps do a broader search, allowing the user to select from a list of possible matches.
        self.NoWikipageFound = True
        self.createwikipagebtn['state'] = self.statebywikipagecreate()


    def create_wikipage(self):
        logger.info("Creating new wikipage for experiment '%s'", self)
        page = self.Experiment.makeWikiPage()
        if page:
            logger.info("New wikipage created: %s", page)
            self.update_variables()
            # perhaps do self.Parent.update_frames instead?
        else:
            logger.error("makeWikiPage returned false: %s", page)


    def saveprops(self):
        self.Experiment.saveAll()

    def statebyisactive(self):
        return 'normal' if self.Experiment.isactive() else 'disabled'

    def statebynowikipageid(self):
        return 'normal' if self.Experiment.PageId is None else 'disabled'

    def statebywikipagecreate(self):
        if self.NoWikipageFound and not self.Experiment.PageId:
            return 'normal'
        else:
            return 'disabled'

    def activeExpsChange(self, event=None):
        self.closebtn['state'] = 'normal' if self.Experiment.isactive() else 'disabled'
        logger.debug("closebtn['state'] set to %s", self.closebtn.cget('state'))


class ExpPropsFrame(ExpFrame):
    """
    A frame to show properties of an experiment (Experiment.Props)
    This frame is designed to show properties from only a single entity.
    E.g., showing values from Experiment.Props.
    This class can be repurposed by overriding getValue() and getEntries() methods,
    and optionally also init_layout() method.
    """
    #def __init__(self, parent, experiment):
    #    ttk.Frame.__init__(self, parent)
    #    self.Experiment = experiment
    #    #self.Variables = dict()
    #    self.Labels = dict()
    #    self.Entries = dict()
    #    self.init_variables()
    #    self.init_layout()

    def init_variables(self):
        self.Variables = dict( ( k, tk.StringVar(value=self.getValue(k)) )  for (k, desc) in self.getEntries() )
        logger.debug("%s.Variables: %s", self.__class__.__name__, self.Variables)

    def update_variables(self):
        for key, tkvar in self.Variables.items():
            new_val = self.getValue(key)
            if new_val:
                tkvar.set(new_val)

    def getValue(self, key):
        return self.Experiment.Props.get(key)

    def getEntries(self, ):
        entries = ( ('expid', 'Experiment ID'),
                    ('exp_titledesc', 'Title desciption'),
                    ('wiki_pageId', 'Wiki PageId'),
                    ('wiki_pagetitle', 'Wiki PageTitle')
                    ,('lastsaved', 'Props last saved')
                    #,('', '')
                  )
        return entries

    def init_layout(self):
        # The property entries to use (key, description):
        entries = self.getEntries()
        self.columnconfigure(2, weight=2)#, minsize=80)
        startrow = 1
        for r, (key, desc) in enumerate(entries, startrow):
            var = self.Variables[key]
            if desc:
                self.Labels[key] = label = ttk.Label( self, text=desc+":", justify=tk.LEFT)
                label.grid(column=1, row=r, sticky="nsew")
                self.Entries[key] = entry = ttk.Entry(self, textvariable=var, state='readonly', justify=tk.LEFT)
                entry.grid(column=2, row=r, sticky="nsew")
            else:
                self.Entries[key] = entry = ttk.Label(self, textvariable=var, state='readonly', justify=tk.LEFT, anchor="e")
                #self.Entries[key] = entry = ttk.Entry(self, textvariable=var, state='readonly', justify=tk.LEFT)
                entry.grid(column=1, row=r, sticky="nsw", columnspan=2)



class ExpAttrFrame(ExpPropsFrame):
    def getValue(self, key):
        val = getattr(self.Experiment, key, None)
        if val and len(val)>80:
            #val = "(...) "+val[-80:]
            logger.debug("attr val: %s", val)
        return val
    def getEntries(self, ):
        return ( ('Localdirpath', ''),
                    #,('', '')
                  )


class ExpSubentriesFrame(ExpPropsFrame):
    def getValue(self, key):
        #return self.Experiment.Props.get(key)
        expid = self.Experiment.Props.get('expid', "")
        subentries = self.Experiment.Props.get(key, None)
        if subentries:
            return u'\n'.join("- {expid}{subentry_idx} {subentry_titledesc}".format(**dict(dict(expid=expid,
                subentry_idx='', subentry_titledesc=''), **subentry)) for idx, subentry in subentries.items() )
        else:
            return None

    def getEntries(self):
        return ( ('exp_subentries', 'Subentries'),
                )

    def init_layout(self):
        # The property entries to use (key, description):
        entries = self.getEntries()
        #self.columnconfigure(2, weight=2)#, minsize=80)
        r = 1
        for (key, desc) in entries:
            var = self.Variables[key]
            if desc:
                self.Labels[key] = label = ttk.Label(self, text=desc+":", justify=tk.LEFT)
                label.grid(column=1, row=r, sticky="nsw")
                r += 1
            self.Entries[key] = entry = ttk.Label(self, textvariable=var, state='readonly', justify=tk.LEFT, wraplength=500)
            entry.grid(column=1, row=r, sticky="nsew", columnspan=2)
            r += 1



class ExpWikiPageStructFrame(ExpSubentriesFrame):
    def getValue(self, key):
        """
        Overriding getValue method to provide custom vars.
        Note: \xa0 unicode character (non-breaking space) may be encountered
        when retrieving page structs from the server.
        And, unlike other operators, format does not simply convert
        the output to unicode.
        >>> "hej"+u"\xa0" = u'hej '
        >>> ".".join(["hej", u"\xa0"]) = u'hej. '
        >>> "hej{}".format(u"\xa0") ---> UnicodeEncodeError!
        """
        page = getattr(self.Experiment, key, None)
        if not page:
            logger.info("ExpOverviewFrame.update_wikipageinfo() > Experiment '%s' has no attribute '%s', aborting.",
                        self.Experiment, key)
            return None
        struct = page.Struct #.get('exp_subentries', None)
        def makevalstr(val):
            val = u"{}".format(val)
            if len(val) > 100:
                return val[:100]+" (...)"
            return val
        if struct:
            return '\n'.join(u"- {}: {}".format(k, makevalstr(v)) for k, v in struct.items() )
        else:
            return u"{}".format(struct)

    def getEntries(self, ):
        return ( ('WikiPage', 'Wiki page struct'),
                )

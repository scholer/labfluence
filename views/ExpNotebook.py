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


class BackgroundFrame(ttk.Frame):

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        #self.grid(row=0, column=0, sticky="nesw") # No, ui elements should rarely configure this themselves, it should be the parent that decides this.
        startinfo = """
Open an experiment in the list to the left.
Click "Select" to add experiments to the active experiments list.
Click "New" to create a new experiment.
"""
        self.label = ttk.Label(self, text=startinfo, justify=tk.CENTER)
        self.label.grid(row=0, column=0) # without sticky, it should be center-aligned vertically and horizontally.
        self.rowconfigure(0, minsize=600)
        self.columnconfigure(0, minsize=600)


class ExpNotebook(ttk.Notebook):

    def __init__(self, parent, experiment=None):
        # init super:
        #self.notebook = super(ttk.Notebook, self).__init__(parent) # only works for
        # for old-type classes, use:
        ttk.Notebook.__init__(self, parent)#, padding=(5,5,5,5)) # returns None...
        self.grid(row=1, column=1, sticky="nesw", ipadx=50, ipady=10)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(1, weight=1)#, pad=50)
        #self.columnconfigure(1, minsize=30)
        self.overviewframe = ExpOverviewFrame(self, experiment=experiment)
        self.filemanagerframe = ExpFilemanagerFrame(self, experiment=experiment)
        self.journalframe = ExpJournalFrame(self, experiment=experiment)
        # Adding tabs (pages) to notebook
        self.add(self.overviewframe, text="Overview")
        self.add(self.filemanagerframe, text="File management")
        self.add(self.journalframe, text="Journal assistent")


    def update_info(self):
        self.overviewframe.update_properties()


class ExpFilemanagerFrame(ttk.Frame):
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

        self.filelistfilterframe = FilelistFilterFrame(self)
        self.filelistfilterframe.grid(row=1, column=0, rowspan=3, sticky="nesw")

        self.localfilelistframe = LocalFilelistFrame(self, experiment) # Does not work; probably only if Tix.Tk() is root.
        #self.localfilelistframe = LocalFileTreeFrame(self, experiment)
        self.localfilelistframe.grid(row=1, column=1, sticky="nesw")
        self.wikifilelistframe = WikiFilelistFrame(self, experiment)
        self.wikifilelistframe.grid(row=3, column=1, sticky="nesw")
        self.fileinfoframe = ttk.Frame(self)
        self.fileinfoframe.grid(row=1, column=3, rowspan=3, sticky="nesw")


        self.columnconfigure(0, weight=0, minsize=200)
        self.columnconfigure(1, weight=2, minsize=200)
        self.columnconfigure(3, weight=1, minsize=200)
        self.rowconfigure(1, weight=4)
        self.rowconfigure(3, weight=2)
        #self.columnconfigure(2, weight=1, minsize=200)


class FilelistFilterFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10, relief='solid')
        self.Experiment = experiment
        #self.regexfilter_label = ttk.Label(self, text="Use regex:")
        #self.regexfilter_label.grid(row=3,column=0)
        self.Filterdict = dict()
        self.Filterdict['fn_pattern'] = fn_pat = tk.StringVar(master=parent, value="")
        self.Filterdict['fn_is_regex'] = fn_isregex = tk.BoolVar(master=parent, value=False)
        # letting subentries be a regular (complex) python variable... I need to have None, True and list/tuple
        # (although the first could be "" and the last be a string with comma-separated values.)
        #self.Filterdict['subentries'] = subentries = tk.

        self.Header_label = ttk.Label(self, text="Filelist filters:")
        self.Header_label.grid(row=1,column=1, sticky="nw")
        self.fnpattern_entry = ttk.Entry(self, textvariable=fn_pat)
        self.fnpattern_entry.grid(row=2, column=1, sticky="w")
        self.regexfnfilter_checkbox = ttk.Checkbox(self, text="Use regex:", justify=tk.LEFT)
        self.regexfnfilter_checkbox.grid(row=3, column=1)#, sticky="w")

        self.subentries_list = SubentriesListFrame(self, experiment=experiment)
        self.subentries_list.grid(row=7, column=1, sticky="nesw")



class FilelistFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10, relief='solid')
        self.Experiment = experiment

        self.listbox = tk.Listbox(self)
        #self.listbox.configure(height=self.getheight()) # No reason to hardcode; should be dynamic.
        self.listbox.grid(row=10, column=0, columnspan=2, sticky="news")
        self.rowconfigure(10, weight=1)
        self.columnconfigure(0, weight=1)
        self.Fileslist = list()
        self.updatelist()

    # ttk.Frame is old-style object in python2, so I use a getter method rather than a property idiom.
    def getheight(self):
        return 10

    # alternatively, there is also the Tkinter.tix.DirList / DirTree
    # http://docs.python.org/3/library/tkinter.tix.html
    # or maybe ttk.Treeview
    def updatelist(self, filterdict):
        lst = self.getlist(filterdict)
        if lst:
            self.Fileslist = zip(*lst)
            self.listbox.delete(0, tk.END)
            self.listbox.insert(tk.END, *self.Fileslist[0])

    def getlist(self, filterdict):
        # override this method; must return a list of two-tuple items.
        return list()


class LocalFilelistFrame(FilelistFrame):
    """
    """
    def getlist(self, filterdict):
        return self.Experiment.getLocalFilelist(**filterdict)

    def getheight(self):
        return 18



class LocalFileTreeFrame(ttk.Frame):
    """
    Only works if using Tix.Tk as root, not standard Tk, I believe.
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        self.Experiment = experiment
        self.DirTree = Tix.DirTree(self)
        self.updatedir()
    def updatedir():
        localdir = self.Experiment.Localdirpath
        if localdir:
            self.DirTree.chdir(localdir)



class WikiFilelistFrame(FilelistFrame):

    def getlist(self, filterdict):
        return self.Experiment.listAttachments()







class SubentriesListFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        self.Experiment = experiment
        self.subentrieslistbox = tk.Listbox(self)
        self.subentrieslistbox.grid(row=0, column=0, sticky="news")
        self.rowconfigure(0, weight=1)


    def updatelist(self):
        if self.




class ExpJournalFrame(ttk.Frame):
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

        self.listframe = SubentriesListFrame(self, experiment)
        self.listframe.grid(row=1, column=0)
        self.journalframe = ttk.Frame(self)
        self.journalframe.grid(row=1, column=1, sticky="nesw")
        self.columnconfigure(1, weight=1)
        label = tk.Label(self, text="hej der")
        label.grid(row=0, column=0, sticky="e")




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
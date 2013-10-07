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
from collections import OrderedDict

from subentrieslistbox import SubentriesListbox


class ExpFilemanagerFrame(tk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler):
        tk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
        # widgets should rarely invoke .grid(...) them selves. Leave it to the widget's parent.
        self.Experiment = experiment
        #self.Confighandler = confighandler # Not sure this will ever be needed, probably better to always go through the experiment object...
        self.PropVariables = dict()
        self.DynamicVariables = dict()
        self.Labels = dict()
        self.Entries = dict()

        self.filelistfilterframe = filterframe = FilelistFilterFrame(self, experiment, confighandler)
        self.subentriesfilterlist = subentrieslist = filterframe.subentries_list
        self.filelistfilterframe.grid(row=1, column=0, rowspan=1, sticky="nesw")

        self.fileinfoframe = FileInfoFrame(self, experiment, confighandler)
        self.fileinfoframe.grid(row=2, column=0, rowspan=2, sticky="nesw")

        self.localfilelistframe = LocalFilelistFrame(self, experiment, confighandler)
        self.localfilelistframe.grid(row=1, column=1, sticky="nesw", rowspan=2)

        self.wikifilelistframe = WikiFilelistFrame(self, experiment, confighandler)
        self.wikifilelistframe.grid(row=3, column=1, sticky="nesw")

        self.columnconfigure(0, weight=0, minsize=150)
        self.columnconfigure(1, weight=2, minsize=300)
        #self.columnconfigure(3, weight=1, minsize=200)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=2)
        self.rowconfigure(3, weight=2)
        #self.columnconfigure(2, weight=1, minsize=200)

        # Event bindings:
        self.filelistfilterframe.subentries_list.bind('<<ListboxSelect>>', self.on_filter_change) # self.on_subentry_select )


    def on_filter_change(self):
        filterdict = self.FilelistFilterFrame.getFilterDict()
        self.localfilelistframe.updatelist(filterdict)
        self.wikifilelistframe.updatelist(filterdict, src='cache')


class FileOperationsFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler, **options):
        classopt = dict(borderwidth=10, relief='solid')
        options.update(classopt)
        ttk.Frame.__init__(self, parent, **options)
        self.Experiment = experiment
        self.Confighandler = confighandler
        app = self.Confighandler.Singletons.get('app')


class FileInfoFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler, **options):
        classopt = dict(borderwidth=10, relief='solid')
        options.update(classopt)
        ttk.Frame.__init__(self, parent, **options)
        self.Experiment = experiment
        self.Confighandler = confighandler
        app = self.Confighandler.Singletons.get('app')

        self.headerlabel = ttk.Label(self, text="File info:", font=app.CustomFonts['header3'])
        self.headerlabel.grid(row=1, column=1, columnspan=2, sticky="w")

        self.FileinfoTkvars = OrderedDict()
        self.FileinfoTkvars['filename'] = filename = tk.StringVar(master=parent, value="No file selected")
        self.FileinfoTkvars['filesize'] = filesize = tk.StringVar(master=parent, value="")
        self.FileinfoTkvars['contentType'] = contentType = tk.StringVar(master=parent)
        self.FileinfoTkvars['date_modified'] = date_modified = tk.StringVar(master=parent)
        self.FileinfoTkvars['date_created'] = date_created = tk.StringVar(master=parent)
        self.FileinfoTkvars['creator'] = creator = tk.StringVar(master=parent)
        self.FileinfoTkvars['wiki_attachmentId'] = wiki_attachmentId = tk.StringVar(master=parent)
        self.FileinfoTkvars['wiki_comment'] = wiki_comment = tk.StringVar(master=parent)

        self.FileinfoEntries = dict()

        row = 2
        expandrow = None
        for name,tkvar in self.FileinfoTkvars.items():
            if name in ('filename'):
                label = ttk.Label(self, textvariable=tkvar)
                label.grid(row=row, column=1, columnspan=2, sticky="w")
            elif name in ('wiki_comment'):
                label = ttk.Label(self, text="{}:".format(name))
                label.grid(row=row, column=1, sticky="w")
                row += 1
                entry = ttk.Entry(self, textvariable=tkvar) # The tk.Text widget is overkill and does not support variables...
                self.FileinfoEntries[name] = entry
                entry.grid(row=row, column=1, columnspan=2, sticky="we")
                expandrow = row
            else:
                label = ttk.Label(self, text="{}:".format(name))
                label.grid(row=row, column=1, sticky="w")
                entry = ttk.Entry(self, textvariable=tkvar, state='readonly')
                self.FileinfoEntries[name] = entry
                entry.grid(row=row, column=2, sticky="we")
            row += 1
        #self.rowconfigure(expandrow, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)


class FilelistFilterFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler):
        ttk.Frame.__init__(self, parent, borderwidth=10, relief='solid')
        self.Experiment = experiment
        self.Confighandler = confighandler
        app = self.Confighandler.Singletons.get('app')
        #self.regexfilter_label = ttk.Label(self, text="Use regex:")
        #self.regexfilter_label.grid(row=3,column=0)

        # VARIABLES:
        self.Filterdict = dict()
        self.Filterdict['fn_pattern'] = fn_pat = tk.StringVar(master=parent, value="")
        self.Filterdict['fn_is_regex'] = fn_isregex = tk.BooleanVar(master=parent, value=False)
        self.Filterdict['subentries_only'] = fn_isregex = tk.BooleanVar(master=parent, value=False)
        # letting subentries be a regular (complex) python variable... I need to have None, True and list/tuple
        # (although the first could be "" and the last be a string with comma-separated values.)
        #self.Filterdict['subentries'] = subentries = tk.

        # Layout:
        headerfont = app.CustomFonts['header3']
        self.Header_label = ttk.Label(self, text="Filelist filters:", font=headerfont)
        self.Header_label.grid(row=1,column=1, columnspan=1)#, sticky="nw")
        label = ttk.Label(self, text="Filter filenames:")
        label.grid(row=2,column=1, sticky="w")
        self.regexfnfilter_checkbox = ttk.Checkbutton(self, text="(check for regex)", variable=fn_isregex)
        #self.regexfnfilter_checkbox.configure(justify=tk.LEFT)
        self.regexfnfilter_checkbox.grid(row=2, column=2, sticky="e")
        self.fnpattern_entry = ttk.Entry(self, textvariable=fn_pat)
        self.fnpattern_entry.grid(row=3, column=1, columnspan=2, sticky="ew")

        label = ttk.Label(self, text="Subentries:")
        label.grid(row=6, column=1)#, sticky="w")
        self.subentries_list = SubentriesListbox(self, experiment=experiment, confighandler=confighandler)
        self.subentries_list.grid(row=7, column=1, columnspan=2, sticky="nesw")


    def getSelectedSubentryIdxs(self):
        return self.subentries_list.getSelectedSubentryIdxs()

    def getFilterdict(self):
        self.Filterdict['subentry_idxs'] = self.getSelectedSubentryIdxs()
        return self.Filterdict



class FilelistFrame(ttk.Frame):
    """
    """
    def __init__(self, parent, experiment, confighandler=None):
        ttk.Frame.__init__(self, parent, borderwidth=10, relief='solid')
        self.Experiment = experiment
        self.Fileslist = list()
        self.init_layout()
        self.updatelist()


    def init_layout(self):
        self.headerlabel = ttk.Label(self, text=self.getheader())
        self.headerlabel.grid(row=1, column=1)#, sticky="nw")
        self.listbox = tk.Listbox(self)
        #self.listbox.configure(height=self.getheight()) # No reason to hardcode; should be dynamic.
        self.listbox.grid(row=10, column=1, columnspan=2, sticky="news")
        self.rowconfigure(10, weight=1)
        self.columnconfigure(1, weight=1)

    # ttk.Frame is old-style object in python2, so I use a getter method rather than a property idiom.
    def getheight(self):
        return 10

    def getheader(self):
        return "Local files:"

    # alternatively, there is also the Tkinter.tix.DirList / DirTree
    # http://docs.python.org/3/library/tkinter.tix.html
    # or maybe ttk.Treeview
    # I should make a convention as to what is display and what is reference
    # in tuples used in list, e.g. (<filename-displayed>, <real-file-path>)
    # same goes for (subentry-display-format, subentry_idx)
    def updatelist(self, filterdict=None, src=None):
        if filterdict is None:
            filterdict = dict()
        lst = self.getlist(filterdict, src)
        if lst:
            self.Fileslist = zip(*lst)
            self.listbox.delete(0, tk.END)
            self.listbox.insert(tk.END, *self.Fileslist[0])

    def getlist(self, filterdict, src=None):
        # override this method; must return a list of two-tuple items.
        return list()


class LocalFilelistFrame(FilelistFrame):
    """
    """
    def getlist(self, filterdict, src=None):
        return self.Experiment.getLocalFilelist(**filterdict)

    def getheight(self):
        return 18

#class LocalFileTreeFrame(ttk.Frame):
#    """
#    Only works if using Tix.Tk as root, not standard Tk, I believe.
#    """
#    def __init__(self, parent, experiment, confighandler=None):
#        ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
#        self.Experiment = experiment
#        self.DirTree = Tix.DirTree(self)
#        self.updatedir()
#    def updatedir():
#        localdir = self.Experiment.Localdirpath
#        if localdir:
#            self.DirTree.chdir(localdir)

class WikiFilelistFrame(FilelistFrame):

    def getlist(self, filterdict, src=None):
        # getlist feeds into updatelist() method.
        #return self.Experiment.listAttachments()
        return self.Experiment.getAttachmentList(src=src, **filterdict)
        return "Wiki page attachments:"
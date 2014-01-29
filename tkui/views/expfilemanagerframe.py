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
import os
import time
import logging
logger = logging.getLogger(__name__)

#from subentrieslistbox import SubentriesListbox
from explistboxes import SubentriesListbox, FilelistListbox, LocalFilelistListbox, WikiFilelistListbox
from shared_ui_utils import HyperLink, ExpFrame


class ExpFilemanagerFrame(ExpFrame):
    """
    """
    #def __init__(self, parent, experiment, confighandler, **options):
    #    classopt = dict(borderwidth=5, relief='solid')
    #    classopt.update(options)
    #    ttk.Frame.__init__(self, parent, **classopt)
    #    #tk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
    #    # widgets should rarely invoke .grid(...) them selves. Leave it to the widget's parent.
    #    self.Experiment = experiment
    #    #self.Confighandler = confighandler # Not sure this will ever be needed, probably better to always go through the experiment object...
    #    self.PropVariables = dict()
    #    self.DynamicVariables = dict()
    #    self.Labels = dict()
    #    self.Entries = dict()

    def frame_defaults(self, ):
        return dict(borderwidth=5)#, relief='solid')
        #return dict()


    def init_widgets(self, ):
        experiment = self.Experiment
        self.filelistfilterframe = filterframe = FilelistFilterFrame(self, experiment)
        self.subentriesfilterlist = subentrieslist = filterframe.subentries_list
        self.filelistfilterframe.grid(row=1, column=0, rowspan=1, sticky="nesw")

        self.fileoperationsframe = FileOperationsFrame(self, experiment)
        self.fileoperationsframe.grid(row=2, column=0, rowspan=1, sticky="nesw")

        self.fileinfoframe = FileInfoFrame(self, experiment)
        self.fileinfoframe.grid(row=3, column=0, rowspan=2, sticky="nesw")

        self.localfilelistframe = LocalFilelistFrame(self, experiment)
        self.localfilelistframe.grid(row=1, column=1, sticky="nesw", rowspan=3)

        self.wikifilelistframe = WikiFilelistFrame(self, experiment)
        self.wikifilelistframe.grid(row=4, column=1, sticky="nesw")


    def init_layout(self, ):

        self.columnconfigure(0, weight=1, minsize=200)
        self.columnconfigure(1, weight=3, minsize=300)
        #self.columnconfigure(3, weight=1, minsize=200)
        #self.rowconfigure(1, weight=1)
        self.rowconfigure(3, weight=2)
        self.rowconfigure(4, weight=1)
        #self.columnconfigure(2, weight=1, minsize=200)


    def init_bindings(self):
        # Event bindings:
        self.filelistfilterframe.subentries_list.bind('<<ListboxSelect>>', self.on_filter_change) # self.on_subentry_select )
        #self.filelistfilterframe.fnpattern_entry.bind('<<Modified>>', self.on_filter_change) # The widget is changed.
        self.filelistfilterframe.fnpattern_entry.bind('<Return>', self.on_filter_change) # User presses 'Return' (enter)
        #self.filelistfilterframe.fnpattern_entry.bind('<Key>', self.on_filter_change) # User presses any key

        # Filelists:
        self.localfilelistframe.listbox.bind('<<ListboxSelect>>', self.on_file_select)
        self.wikifilelistframe.listbox.bind('<<ListboxSelect>>', self.on_file_select)


    def on_filter_change(self, event):
        changed_widget = event.widget
        filterdict = self.filelistfilterframe.getFilterdict()
        logger.debug("Filterdict: %s", filterdict)
        self.localfilelistframe.updatelist(filterdict)
        self.wikifilelistframe.updatelist(filterdict)

    def on_file_select(self, event):
        listbox = event.widget
        logger.debug("on_file_select: curselection: %s", listbox.curselection())
        # file_repr, file_identifier, info_struct
        file_tuples = listbox.getSelection()
        # easy way to check if selection is local or wiki file: if 'pageId' in info_struct
        self.fileinfoframe.update_info_tuples(file_tuples)


    def updatewidgets(self, ):
        self.wikifilelistframe.updatelist()



class FilelistFilterFrame(ExpFrame):
    """
    """
    #def __init__(self, parent, experiment, confighandler, **options):
    #    classopt = dict(borderwidth=5, relief='solid')
    #    classopt.update(options)
    #    ttk.Frame.__init__(self, parent, **classopt)
    #    self.Experiment = experiment
    #    self.Confighandler = confighandler
    #    app = self.Confighandler.Singletons.get('app')
    #    #self.regexfilter_label = ttk.Label(self, text="Use regex:")
    #    #self.regexfilter_label.grid(row=3,column=0)

    def init_variables(self):
        # Attributes:
        self.Fonts = self.getFonts()
        # VARIABLES:
        self.Filterdict = dict()
        self.Filterdict['fn_pattern'] = tk.StringVar( value="")
        self.Filterdict['fn_is_regex'] = tk.BooleanVar( value=False)
        self.Filterdict['subentries_only'] = tk.BooleanVar( value=False)
        # letting subentries be a regular (complex) python variable... I need to have None, True and list/tuple
        # (although the first could be "" and the last be a string with comma-separated values.)
        #self.Filterdict['subentries'] = subentries = tk.


    def init_layout(self, ):
        experiment = self.Experiment
        # Layout:
        def cb():
            """ NOT sure this was ever implemented... ? """
            #logger.debug("fn_isregex is : {}".format(fn_isregex.get()) )
            logger.debug("self.Filterdict['fn_is_regex'] is : %s", self.Filterdict['fn_is_regex'].get())

        headerfont = self.Fonts['header3']
        self.Header_label = ttk.Label(self, text="Filelist filters:", font=headerfont)
        self.Header_label.grid(row=1, column=1, sticky="nw")
        label = ttk.Label(self, text="Filter filenames:")
        label.grid(row=2, column=1, sticky="w")
        self.regexfnfilter_checkbox = ttk.Checkbutton(self, text="(check for regex)", variable=self.Filterdict['fn_is_regex'], command=cb)
        #self.regexfnfilter_checkbox.configure(justify=tk.LEFT)
        self.regexfnfilter_checkbox.grid(row=2, column=2, sticky="e")
        self.fnpattern_entry = ttk.Entry(self, textvariable=self.Filterdict['fn_pattern'])
        self.fnpattern_entry.grid(row=3, column=1, columnspan=2, sticky="ew")

        label = ttk.Label(self, text="Subentries: (use ctrl+click to deselect)")
        label.grid(row=6, column=1, columnspan=2, sticky="w")
        self.subentries_list = SubentriesListbox(self, experiment=experiment)
        self.subentries_list.grid(row=7, column=1, columnspan=2, sticky="ew")
        self.subentries_list.configure(height=8, selectmode=tk.EXTENDED)
        self.subentries_list.updatelist() # invoked explicitly? Why?
        self.columnconfigure(1, weight=1) # Remember to add these, otherwise sticky does not help expanding...
        self.columnconfigure(2, weight=1)


    def getSelectedSubentryIdxs(self):
        """ Returns the selected subentry indices from the subentry list... """
        return self.subentries_list.getSelectedSubentryIdxs()

    def getFilterdict(self):
        """
        Returns a proper filter dict, extracting values from self.Filterdict (tk vars).
        Also adds a proper subentry_idxs entry.
        """
        filterdict = { key : tkvar.get() for key, tkvar in self.Filterdict.items() }
        filterdict['subentry_idxs'] = self.getSelectedSubentryIdxs()
        #self.Filterdict['subentry_idxs'] = self.getSelectedSubentryIdxs()
        return filterdict


class FileOperationsFrame(ExpFrame):
    """
    """
    #def __init__(self, parent, experiment, **options):
    #    classopt = dict(borderwidth=5, relief='solid')
    #    classopt.update(options)
    #    ttk.Frame.__init__(self, parent, **classopt)
    #    self.Experiment = experiment
    #    self.Confighandler = confighandler
    #    app = self.Confighandler.Singletons.get('app')

    #def frame_defaults(self, ):
    #    return dict(borderwidth=5)#, relief='solid')

    def init_layout(self):
        self.rename_btn = ttk.Button(self, text="Rename file...", command=self.renamefile)#, width=12)
        self.rename_btn.grid(row=1,column=1, sticky="we")
        self.other_btn = ttk.Button(self, text="Something else", command=self.renamefile)#, width=12)
        self.other_btn.grid(row=1,column=2, sticky="we")
        self.upload_btn = ttk.Button(self, text="Upload to wiki", command=self.renamefile)#, width=12)
        self.upload_btn.grid(row=1,column=3, sticky="we")
        self.download_btn = ttk.Button(self, text="Download", command=self.renamefile)#, width=12)
        self.download_btn.grid(row=1,column=3, sticky="we")
        self.columnconfigure((1,2,3), weight=1)


    def renamefile(self):
        print "How?"


class FileInfoFrame(ExpFrame):
    """
    """
    #def __init__(self, parent, experiment, confighandler, **options):
    #    classopt = dict(borderwidth=5, relief='solid')
    #    classopt.update(options)
    #    ttk.Frame.__init__(self, parent, **classopt)
    #    self.Experiment = experiment
    #    self.Confighandler = confighandler
    #    app = self.Confighandler.Singletons.get('app')

    #def frame_defaults(self):
    #    return dict(borderwidth=5)#, relief='solid')

    def init_layout(self, ):

        self.headerlabel = ttk.Label(self, text="File info:", font=self.getFonts()['header3'])
        self.headerlabel.grid(row=1, column=1, columnspan=2, sticky="w")

        self.FileinfoTkvars = OrderedDict()
        self.FileinfoTkvars['fileName'] = filename = tk.StringVar( value="No file selected")
        self.FileinfoTkvars['fileSize'] = filesize = tk.StringVar( value="")
        self.FileinfoTkvars['contentType'] = contentType = tk.StringVar()
        self.FileinfoTkvars['modified'] = date_modified = tk.StringVar()
        self.FileinfoTkvars['created'] = date_created = tk.StringVar()
        self.FileinfoTkvars['creator'] = creator = tk.StringVar()
        self.FileinfoTkvars['id'] = wiki_attachmentId = tk.StringVar()
        self.FileinfoTkvars['title'] = wiki_attachmentId = tk.StringVar()
        self.FileinfoTkvars['comment'] = wiki_comment = tk.StringVar()

        self.FileinfoEntries = dict()

        row = 2
        expandrow = None
        for name, tkvar in self.FileinfoTkvars.items():
            if name in ('fileName', ):
                label = ttk.Label(self, textvariable=tkvar)
                label.grid(row=row, column=1, columnspan=2, sticky="w")
            elif name in ('comment', ):
                label = ttk.Label(self, text=u"{}:".format(name))
                label.grid(row=row, column=1, sticky="w")
                row += 1
                entry = ttk.Entry(self, textvariable=tkvar) # The tk.Text widget is overkill and does not support variables...
                self.FileinfoEntries[name] = entry
                entry.grid(row=row, column=1, columnspan=2, sticky="we")
                expandrow = row
            else:
                label = ttk.Label(self, text=u"{}:".format(name))
                label.grid(row=row, column=1, sticky="w")
                entry = ttk.Entry(self, textvariable=tkvar, state='readonly')
                self.FileinfoEntries[name] = entry
                entry.grid(row=row, column=2, sticky="we")
            row += 1
        #self.rowconfigure(expandrow, weight=1)
        self.columnconfigure(1, weight=0, pad=5)
        self.columnconfigure(2, weight=1)

    #self.fileinfoframe.update_info_tuples(file_tuples)
    def update_info_tuples(self, file_tuples):
        """
        Receives a list of file_tuples (file_repr, file_identifier, metadata_struct)
        Wiki attachment-struct has fields:
        - comment (string, required)
        - contentType (string, required)
        - created (date)
        - creator (string username)
        - fileName (string, required)
        - fileSize (string, number of bytes)
        - id (string, attachmentId)
        - pageId (string)
        - title (string)
        - url (string)
        LocalFile starts out only having field 'filename' and 'filepath'
        """
        if file_tuples:
            file_repr, file_identifier, metadata = file_tuples[0]
            # most fields does not require mapping, e.g. fileName, fileSize, contentType, created, creator, title, url, id and comment.
            # However, for the fields that might require something, insert here:
            if 'pageId' not in metadata: # Assume local file
                if 'date_modified' not in metadata:
                    try:
                        metadata['modified'] = time.ctime(os.path.getmtime(file_identifier))
                    except WindowsError as e: # MS Windows-specific error:
                        logger.exception(e)
                if 'fileSize' not in metadata:
                    try:
                        metadata['fileSize'] = os.path.getsize(file_identifier)
                    except WindowsError as e:
                        logger.exception(e)
                if 'fileName' not in metadata:
                    metadata['fileName'] = os.path.basename(file_repr)
        else:
            metadata = dict()

        logger.debug("update_info_tuples(), metadata: %s", metadata)
        for key, tkvar in self.FileinfoTkvars.items():
            logger.debug("Setting '%s' to value: '%s'", key, metadata.get(key, ""))
            tkvar.set(metadata.get(key, ""))




class FilelistFrame(ExpFrame):
    """
    # alternatively, there is also the Tkinter.tix.DirList / DirTree
    # http://docs.python.org/3/library/tkinter.tix.html
    # or maybe ttk.Treeview
    # I should make a convention as to what is display and what is reference
    # in tuples used in list, e.g. (<filename-displayed>, <real-file-path>)
    # same goes for (subentry-display-format, subentry_idx)
    """
    #def __init__(self, parent, experiment, confighandler=None, **options):
    #    frameopt = dict(borderwidth=5, relief='solid')
    #    frameopt.update(options)
    #    ttk.Frame.__init__(self, parent, **frameopt)
    #    self.Experiment = experiment
    #    self.Confighandler = confighandler
    #    self.init_widgets()
    #    self.init_grid()

    def after_init(self, ):
        self.updatelist()

    #def frame_defaults(self):
    #    return dict(borderwidth=5)#, relief='solid')

    def init_widgets(self):
        self.headerlabel = ttk.Label(self, text=self.getheader())
        self.listbox = FilelistListbox(self, self.Experiment)

    def init_layout(self):
        self.headerlabel.grid(row=1, column=1)
        self.listbox.grid(row=10, column=1, columnspan=2, sticky="news")
        self.rowconfigure(10, weight=1)
        self.columnconfigure(1, weight=1)

    # Regarding properties: ttk.Frame is old-style object in python2, so I use a getter method rather than a property idiom.
    def getheight(self):
        return 10

    def getheader(self):
        return "Local files:"

    def updatelist(self, filterdict=None):
        self.listbox.updatelist()
        if filterdict is None:
            filterdict = dict()
        lst = self.getlist(filterdict)
        self.Filetuples = lst
        self.Fileslist = zip(*lst)
        self.listbox.delete(0, tk.END)
        if lst:
            self.listbox.insert(tk.END, *self.Fileslist[0])

    def getlist(self, filterdict):
        # override this method; must return a list of two-tuple items.
        return self.listbox.getlist(filterdict)

    def getSelection(self):
        # Returning the complete file tuple with metadata -- makes it more useful.
        return self.listbox.getSelection()



class LocalFilelistFrame(FilelistFrame):

    def init_widgets(self):
        self.headerlabel = ttk.Label(self, text="Local experiment files:")
        self.listbox = LocalFilelistListbox(self, self.Experiment)



class WikiFilelistFrame(FilelistFrame):

    def init_widgets(self):
        self.headerlabel = ttk.Label(self, text="Wiki attachments:")
        self.listbox = WikiFilelistListbox(self, self.Experiment)





"""
Cut out parts:



#class LocalFileTreeFrame(ttk.Frame):
#
#    #Only works if using Tix.Tk as root, not standard Tk, I believe.
#
#    def __init__(self, parent, experiment, confighandler=None):
#        ttk.Frame.__init__(self, parent, borderwidth=10)#, relief='flat')
#        self.Experiment = experiment
#        self.DirTree = Tix.DirTree(self)
#        self.updatedir()
#    def updatedir():
#        localdir = self.Experiment.Localdirpath
#        if localdir:
#            self.DirTree.chdir(localdir)

"""
if __name__ == '__main__':
    pass

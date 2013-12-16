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
"""

I refactored the long labfluence_gui module to the following UI specific
tkui/labfluence_tkapp   - Contains "app" level items, has properties (which tk.Tk
                        objects can't because they are not new-style objects)
                        This should be suffiently abstract that it can theoretically be substituted
                        with e.g. a qt app class and most calls will work ok.
tkui/labfluence_tkroot  - Derives from tkinter.Tk, acts as the "tkroot".
tkui/mainwindow         - Does all the widget layout, etc.

Left, we have:
labfluence_gui          - Main script for the main labfluence application.

Optionally:
tkui/labfluence_app     - Could provide a base class that could be derived in
                        tkui/labfluence_tkapp with tk-specific things.


"""


# python 3.x:
#from tkinter import ttk
# python 2.7:
import Tkinter as tk

# Other standard lib modules:
import socket
from datetime import datetime
from collections import OrderedDict
import logging
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)

# Labfluence modules and classes:

#from model.confighandler import ExpConfigHandler
#from model.experimentmanager import ExperimentManager
#from model.experiment import Experiment
#from model.server import ConfluenceXmlRpcServer
from model.utils import getmimetype, findFieldByHint
from model.limspage import WikiLimsPage

### GUI elements ###
from tkui.lims_tkroot import LimsTkRoot




class LimsApp(object):
    """
    Main app for the lims prompt.
    """


    def __init__(self, confighandler):
        self.Confighandler = confighandler

        #self.Fields = OrderedDict( (key, key.capitalize())
        #        for key in (
        #            'date',
        #            'type',
        #            'product',
        #            'amount',
        #            'price',
        #            'manufacturer',
        #            'cat. no.',
        #            'contact_person',
        #            'location',
        #            'storage temperature',
        #            'remaining',
        #            'comment',
        #            'file'
        #            ) )
        #self.Fields['contact_person'] = 'Ordered for whom (by whom)'
        #self.Fields['price'] = 'Price (dkk)'
        #self.Fields['manufacturer'] = 'Manufacturer / distributor'

        # edit: Fields is now a dict consisting of
        #    <key/label/header> = default value  pairs.

        self.PromptResults = list()
        # pageId, server, confighandler=None, pagestruct=None
        server, limspageid = self.Server, self.LimsPageId
        if server is None or not limspageid:
            logger.error("Server is: %s; limspageid is: %s", server, limspageid)
        self.WikiLimsPage = WikiLimsPage(limspageid, server)

    @property
    def Fields(self, ):
        headers = self.WikiLimsPage.getTableHeaders()
        fields = OrderedDict.fromkeys(headers, "")
        df = findFieldByHint(headers, 'date')
        if df:
            fields[df] = datetime.now().strftime("%Y%m%d")



    @property
    def Server(self):
        """Experiment manager, obtained from confighandler if possible.
        Edit: Not 'if possible'. Having a well-behaved confighandler is now a requirement as this significantly simplifies a lot of code.
        """
        return self.Confighandler.Singletons.get('server', None)

    @property
    def LimsPageId(self, ):
        return self.Confighandler.get('lims_pageid', None)


    def lims_entry_prompt(self, filepath):
        """
        Opens a tk window and asks for user input.
        """
        results = list()
        # So, when using a dialog from within a tk app, I could throw in a
        # dict/list with tk variables.
        # Similarly, from within a non-tk app, I figured I could use the same
        # approach, throwing in a "storage" variable, resultslist, and have the
        # dialog persist its result in this before being destroyed.
        lims_tkroot = LimsTkRoot(self.Confighandler, fields=self.Fields,
                                 resultslist=results, filepath=filepath)
        lims_tkroot.mainloop()
        logger.debug("results : %s", results)
        if results:
            # use input to do something...
            return results[0]


    def add_entry(self, filepath=None, persist=False):

        lims_info = self.lims_entry_prompt(filepath)
        logger.debug("lims info: %s", lims_info)
        if not lims_info:
            return False
        if filepath:
            fp = lims_info.pop('filepath')
            fn = lims_info.pop('filename')
            #fcomment = fn = lims_info.pop('file_comment') # Auto generated...
            # attachmentInfo dict must include fields 'comment', 'contentType', 'fileName'
            attachmentInfo = dict( fileName=fn, contentType=getmimetype(fp) )
            att_info = self.WikiLimsPage.addAttachment(attachmentInfo, attachmentData)
            # update lims_info...
            lims_info['Attachment(s)'] = "some xhtml code"

        self.WikiLimsPage.addEntry(lims_info, persistToServer=persist)
        return lims_info, att_info


    def addEntriesForFiles(self, files):
        """
        Add multiple files/orders to the LIMS page,
        one file per order.
        """
        products = list()
        results = [self.add_entry(fp, persist=False) for fp in files]
        products = [res[0]['product'] for res in results if res]
        versionComment = "Labfluence LIMS, added " + ", ".join(products)
        self.WikiLimsPage.updatePage(struct_from='cache', versionComment=versionComment, minorEdit=False)

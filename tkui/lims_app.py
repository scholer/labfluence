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

Implementation alternatives:

1) Main script, creates a tk root which prompts for user input when required.
    After user input, the tk root is destroyed and the main app loop continues.
    - Requires instantiating a new tkroot for every user input prompt...

2) Main script, has a permanent tk root which is displayed when user input is required, then continues.
--- app -> prompt
        -> app.add_entry (hides tk ui, adds entry;
                if more files:
                    clear prompt to make it available for new,
                    returns to tk ui,
                otherwise kills tk)
        -> prompt (...?)


3) Tk root is main, with tk events driving the script forward and methods


"""


# python 3.x:
#from tkinter import ttk
# python 2.7:
#import Tkinter as tk

# Other standard lib modules:
#import socket
import os
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
from model.utils import findFieldByHint
from model.limspage import WikiLimsPage
from model.utils import attachmentTupFromFilepath

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

        #self.PromptResults = list()
        # pageId, server, confighandler=None, pagestruct=None
        server, limspageid = self.Server, self.LimsPageId
        if server is None or not limspageid:
            logger.error("Server is: %s; limspageid is: %s", server, limspageid)
            raise ValueError("Server is: {}; limspageid is: {}".format( server, limspageid ) )
        logger.debug("Making WikiLimsPage...")
        self.WikiLimsPage = WikiLimsPage(limspageid, server)
        logger.debug("WikiLimsPage created.")
        self.FilesToAdd = list()
        self.FilesAdded = list()
        self._filegenerator = None # Created when needed. self.nextFileGenerator()
        self.PersistForEveryFile = False
        self.AddedEntries = list()
        # These fields does not correspond to the LIMS table, but only fields for the UI prompt.
        self.FilepathField = 'Path to order file'
        self.AttachmentNameField = 'Attachment name'
        # This is needed specifically, since we need to generate a xhtml link for this field.
        self.AttachmentField = None
        # If this is set to true, the lims page is requested to persist the xhtml content
        # after each add_entry invokation.
        # Default (False) is to only persist limspage after all entries are added.
        logger.debug("Making LimsTkRoot...")
        self.Tkroot = LimsTkRoot(self, self.Confighandler)
        self.Confighandler.Singletons['ui'] = self.Tkroot
        logger.debug("LimsTkRoot created and registrered in the singletons, creating fields...")
        # ugh... calling e.g. the prompt before the main loop has started causes some weird issues.
        # Maybe I can defer this to the start() method?
        fields = self.Tkroot.Fields = self.getLimsFields()
        if fields:
            logger.debug("Fields obtained: %s - initiating ui...", fields)
            self.Tkroot.init_ui()
        else:
            logger.warning("Fields NOT obtained: %s - cannot initialize UI...", fields)



    def nextfile(self):
        """ Returns the next file in the files list """
        if self._filegenerator is None:
            self._filegenerator = (filepath for filepath in self.FilesToAdd)
        return next(self._filegenerator, None)


    @property
    def Server(self):
        """Experiment manager, obtained from confighandler if possible.
        Edit: Not 'if possible'. Having a well-behaved confighandler is now a requirement as this significantly simplifies a lot of code.
        """
        return self.Confighandler.Singletons.get('server', None)

    @property
    def LimsPageId(self, ):
        """ Returns the LIMS page id from the confighandler. """
        return self.Confighandler.get('lims_pageid', None)


    def getLimsFields(self):
        """
        Queries the LIMS page for table headers list,
        does some processing of this list,
        and returns it.
        """
        self.Headers = headers = self.WikiLimsPage.getTableHeaders()
        if not headers:
            print "No headers returned by WikiLimsPage.getTableHeaders(), aborting..."
            return

        # Remove the "attachments" header, replace by a field for inputting file path and fileName.
        self.AttachmentField = findFieldByHint(headers, ('attachment', 'order file'))
        if self.AttachmentField:
            logger.debug("Removing field from header list: %s", self.AttachmentField)
            headers.remove(self.AttachmentField)
        headers.append(self.FilepathField)
        headers.append(self.AttachmentNameField)

        # Create fields dict
        fields = OrderedDict.fromkeys(headers, "")

        # Insert default values (date, person, etc)
        df = findFieldByHint(headers, 'date')
        if df:
            fields[df] = datetime.now().strftime("%Y%m%d")
        personfield = findFieldByHint(headers, ('ordered by', 'person'))
        if personfield:
            default_person = self.Confighandler.get('lims_default_name', None) or 'Rita'
            fields[personfield] = "For {} by {}".format('', default_person)

        # Collect entries to clear on each submission.
        # All other entries are keps per default (except file-related ones...)
        self.ResetEntryFields = dict()
        self.ResetEntryFields['productname'] = findFieldByHint(headers, ('product name', 'product', 'name'))
        self.ResetEntryFields['comment'] = findFieldByHint(headers, ('comment'))
        self.ResetEntryFields['amount'] = findFieldByHint(headers, ('amount'))
        logger.debug("fields dict is: %s", fields)
        return fields


    #def lims_entry_prompt(self, filepath):
    #    """
    #    Opens a tk window and asks for user input.
    #    Only used in the "open a new tk root for every input" implementation.
    #    """
    #    results = list()
    #    # So, when using a dialog from within a tk app, I could throw in a
    #    # dict/list with tk variables.
    #    # Similarly, from within a non-tk app, I figured I could use the same
    #    # approach, throwing in a "storage" variable, resultslist, and have the
    #    # dialog persist its result in this before being destroyed.
    #    lims_tkroot = LimsTkRoot(self.Confighandler, fields=self.Fields,
    #                             resultslist=results, filepath=filepath)
    #    lims_tkroot.mainloop()
    #    logger.debug("results : %s", results)
    #    if results:
    #        # use input to do something...
    #        return results[0]
    #
    #def prompt_and_add_entry(self, filepath=None, persist=False):
    #    """
    #    Note: filepath may be changed by the lims_entry_prompt dialog.
    #
    #    """
    #
    #    lims_info = self.lims_entry_prompt(filepath)
    #    logger.debug("lims info: %s", lims_info)
    #    if not lims_info:
    #        return False
    #    fp = lims_info.pop('filepath', None)
    #    if fp:
    #        fn = lims_info.pop('filename', None)
    #        #fcomment = fn = lims_info.pop('file_comment') # Auto generated...
    #        # attachmentInfo dict must include fields 'comment', 'contentType', 'fileName'
    #        #attachmentInfo = dict( fileName=fn, contentType=getmimetype(fp) )
    #        attachmentInfo, attachmentData = attachmentTupFromFilepath(fp)
    #        if fn:
    #            attachmentInfo['fileName'] = fn # If not specified in form, use the file's actual name.
    #        # xmlrpc API addAttachment(token, contentId, attachment_struct, attachmentData)
    #        att_info = self.WikiLimsPage.addAttachment(attachmentInfo, attachmentData)
    #        attachementsheader = findFieldByHint(headers, ('attachment', 'order file'))
    #        # update lims_info...
    #        lims_info['Attachment(s)'] = "some xhtml code with link functionality..."
    #
    #    self.WikiLimsPage.addEntry(lims_info, persistToServer=persist)
    #    return lims_info, att_info
    #
    #def addEntriesForFiles(self, files):
    #    """
    #    Add multiple files/orders to the LIMS page,
    #    one file per order.
    #    This was the main driving loop for the
    #        "app -> prompt dialog (closes) -> app continues"
    #    implementation.
    #    """
    #    products = list()
    #    results = [self.add_entry(fp, persist=False) for fp in files]
    #    products = [res[0]['product'] for res in results if res]
    #    versionComment = "Labfluence LIMS, added " + ", ".join(products)
    #    self.WikiLimsPage.updatePage(struct_from='cache', versionComment=versionComment, minorEdit=False)






    def add_entry(self, addNewEntryWithSameFile=False):
        """
        Takes the current info from the tkroot prompt and adds a table entry
        with this.
        If addNewEntryWithSameFile is set to true, instead of proceeding to next file
        on completion, this method will call repeat_entry.
        """
        entry_info = self.Tkroot.get_result()
        logger.debug("entry_info : %s", entry_info)
        if not entry_info:
            #return False
            self.next_entry()
            return
        fp = entry_info.pop(self.FilepathField, None)
        # if a filepath is given, try to upload the file.
        if fp:
            fn = entry_info.pop(self.AttachmentNameField, None)
            # attachmentInfo dict must include fields 'comment', 'contentType', 'fileName'
            attachmentInfo, attachmentData = attachmentTupFromFilepath(fp)
            if fn:
                # If fn is specified in the form, use that, otherwise the file's actual filename is kept.
                attachmentInfo['fileName'] = fn
            # xmlrpc API addAttachment(token, contentId, attachment_struct, attachmentData)
            logger.debug("Adding attachment '%s' with base64 encoded attData of length %s", attachmentInfo, len(str(attachmentData)))
            att_info = self.WikiLimsPage.addAttachment(attachmentInfo, attachmentData)
            # update lims_info...
            entry_info[self.AttachmentField] = "some xhtml code with link functionality..."
            self.FilesAdded.append(fp)
        else:
            logger.debug("No filepath provided...")
            att_info = None

        # Add entry:
        logger.debug("Adding entry to limspage content, persistToServer=%s...", self.PersistForEveryFile)
        self.WikiLimsPage.addEntry(entry_info, persistToServer=self.PersistForEveryFile)
        self.AddedEntries.append(entry_info[self.ResetEntryFields['productname']] if 'productname' in self.ResetEntryFields
                                    else len(self.AddedEntries)+1)
        logger.debug("Added entries: %s", ", ".join(str(item) for item in self.AddedEntries))

        # Inform the user:
        self.set_entry_added_message(entry_info, att_info)

        # If addNewEntryWithSameFile:
        if addNewEntryWithSameFile:
            self.Tkroot.deiconify()
            logger.debug("add_entry complete (addNewEntryWithSameFile=%s", addNewEntryWithSameFile)
            return #?

        self.next_entry()
        logger.debug("add_entry complete")


    def set_entry_added_message(self, entry_info, att_info):
        """
        Call this to display a message to the user that the entry was added.
        """
        self.Tkroot.Message.set('Entry {} added; add new...'.format(
                                entry_info.get(self.ResetEntryFields['productname'])))
        logger.debug("set_entry_added_message complete .")


    def next_entry(self):
        """
        Takes the next file in self.FilesToAdd.
        If there is a next file:
        1) Prepare the tkroot ui prompt for a new entry.
        2) Returns to the tk ui prompt.
        (the tk ui will then either call add_entry, which will call this after completion.)

        If there are no more files: persist the LimsPage, close tk root and exits.
        """

        nextfp = self.nextfile()
        if nextfp:
            self.repopulatePrompt(nextfp)
            self.Tkroot.deiconify()
            logger.debug("Next entry, filepath is '%s', returning to tk root (form/prompt).", nextfp)
            return
        else:
            # Persist limspage
            if not self.PersistForEveryFile:
                versionComment = "Added entries: " + ", ".join(str(item) for item in self.AddedEntries)
                minorEdit = False
                logger.debug("Persisting LIMS page, versionComment is: %s", versionComment)
                #self.WikiLimsPage.updatePage(struct_from='cache', versionComment=versionComment, minorEdit=minorEdit)
            # close tk root:
            logger.debug("Destroying tk root")
            self.Tkroot.destroy()
            # exit:
            logger.debug("Exiting application loop.")
            return


    def repopulatePrompt(self, filepath=None):
        """
        Re-populates the tk form.
        """
        logger.debug("Re-populating form")
        fieldvars = self.Tkroot.Fieldvars
        if filepath:
            fieldvars[self.FilepathField][0].set(filepath)
            fieldvars[self.AttachmentNameField][0].set(os.path.basename(filepath))
        for header in self.ResetEntryFields.values():
            fieldvars[header][0].set('')
        logger.debug("repopulatePrompt complete.")


    def main(self):
        """
        Starts the application UI.
        """
        #if self.Tkroot is None:
        #    self.Tkroot = LimsTkRoot(self, self.Confighandler, fields=self.getLimsFields())
        ########
        # Uh, ok, I thought that using after and ensuring that the mainloop was
        # running would prevent the issue where the tk ui "collapses".
        # However that just has the effect of the form ALWAYS collapsing
        # even when the login prompt is not needed...!
        # grr..
        logger.info("\n\nApp main() invoked!\n")
        #self.Tkroot.after(500, self.start)
        self.start()
        logger.info("\nApp main() complete!\n")


    def start(self):
        logger.info("\n\nApp start() invoked...\n\n\n")
        if not self.WikiLimsPage.PageId:
            logger.error("WikiLimsPage does not have a pageId")
            return
        if not self.WikiLimsPage.Content:
            logger.error("WikiLimsPage does not have any Content! (is: %s)", self.WikiLimsPage.Content)
            logger.info("self.WikiLimsPage is: %s", self.WikiLimsPage)
            logger.info("self.Confighandler is: %s", self.Confighandler)
            logger.info("server is: %s", self.Confighandler.Singletons['server'])
            logger.info("server._connectionok is: %s", self.Confighandler.Singletons['server']._connectionok)
            return
        if self.FilesToAdd:
            logger.debug("Calling next_entry to populate for first file...")
            self.next_entry()
        logger.info("\nStarting tkroot mainloop()...\n")
        self.Tkroot.mainloop()
        logger.info("\nTkroot mainloop() complete - (and App start() ) \n")

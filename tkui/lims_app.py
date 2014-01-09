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
# pylint: disable-msg=W0212
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
import Tkinter as tk

# Other standard lib modules:
#import socket
import os
from datetime import datetime
from collections import OrderedDict
import xmlrpclib
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
from model.utils import attachmentTupFromFilepath, getNewFilename
from model.decorators.cache_decorator import cached_property

### GUI elements ###
from tkui.lims_tkroot import LimsTkRoot




class LimsApp(object):
    """
    Main app for the lims prompt.
    """


    def __init__(self, confighandler, pageId=None, filestoadd=None):
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
        self._pageid = pageId
        server, limspageid = self.Server, self.LimsPageId
        if server is None or not limspageid:
            logger.error("Server is: %s; limspageid is: %s. If limspage is None, \
you should probably set the wiki_lims_pageid config entry, in one of the config files:\n\
   %s", server, limspageid,
                         "\n   ".join("{}: {}".format(t, p) for t, p in self.Confighandler.ConfigPaths.items())
                        )
            raise ValueError("Server is: {}; limspageid is: {}".format( server, limspageid ) )
        logger.debug("Making WikiLimsPage...")
        self.WikiLimsPage = WikiLimsPage(limspageid, server)
        self._newAttachments = list()
        logger.debug("WikiLimsPage created.")
        title = "Labfluence LIMS (pageId: {})".format(limspageid)
        self.FilesToAdd = filestoadd or list()
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
        self.Tkroot = LimsTkRoot(self, self.Confighandler, title=title)
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
        return self._pageid or self.Confighandler.get('wiki_lims_pageid', None)

    @cached_property(ttl=120)
    def Attachments(self):
        """ Returns all attachment structs """
        self._newAttachments = list()
        return self.WikiLimsPage.getAttachments() or list()

    @cached_property(ttl=120)
    def AttachmentNames(self):
        """ Returns all used attachment names. """
        attachmentstructs = self.Attachments + self._newAttachments
        return {attachment['fileName'] for attachment in attachmentstructs}

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

        # Remove the "attachments" header (parsed from the xhtml),
        # replace with fields for inputting file path and optionally provide new fileName.
        self.AttachmentField = findFieldByHint(headers, ('attachment', 'order file'))
        if self.AttachmentField:
            logger.debug("Removing attachment field from header list: %s", self.AttachmentField)
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
            default_person = self.Confighandler.get('lims_default_name', 'Rita')
            fields[personfield] = "For {} by {}".format('', default_person)

        # Collect entries to clear on each submission.
        # All other entries are keps per default (except file-related ones...)
        self.ResetEntryFields = dict()
        self.ResetEntryFields['productname'] = findFieldByHint(headers, ('product name', 'product', 'name'))
        self.ResetEntryFields['comment'] = findFieldByHint(headers, ('comment'))
        self.ResetEntryFields['amount'] = findFieldByHint(headers, ('amount'))
        self.ResetEntryFields['price'] = findFieldByHint(headers, ('amount'))
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





    def set_entry_added_message(self, entry_info, att_info):
        """
        Call this to display a message to the user that the entry was added.
        """
        msg = 'Entry {} added{}; add new...'.format(
                                entry_info.get(self.ResetEntryFields['productname']),
                                "with attachment '{}'".format(att_info['fileName']) if att_info else ""
                                )
        self.Tkroot.Message.set(msg)
        logger.debug("set_entry_added_message complete .")



    def add_entry(self, addNewEntryWithSameFile=False):
        """
        Takes the current info from the tkroot prompt and adds a table entry
        with this.
        If addNewEntryWithSameFile is set to true, instead of proceeding to next file
        on completion, this method will call repeat_entry.

        Note regarding attachments: The attachments API has a lot of flaws:
        - It is not possible to edit an the info of an existing attachment.
        - It is not possible to set comment or title for an attachment.
        Essentially, this makes it impossible to do any advanced stuff (like hash
        checking -- unless you feel like downloading all attachments every time.)
        """
        entry_info = self.Tkroot.get_result()
        logger.debug("entry_info : %s", entry_info)
        if not entry_info:
            #return False
            logger.debug("No entry_info from self.Tkroot.get_result, calling next_entry and returning...")
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
            try:
                att_info = self.WikiLimsPage.addAttachment(attachmentInfo, attachmentData)
                self._newAttachments.append(att_info)
            except xmlrpclib.Fault as e:
                logger.error("Error uploading file: %s\nattachmentInfo is: %s\nattachmentData has length: %s\nError is: %s",
                             fp, attachmentInfo, len(str(attachmentData)), e)
                raise e
            # update lims_info...
            if self.AttachmentField:
                entry_info[self.AttachmentField] = self.WikiLimsPage.getAttachmentLinkXhtml(att_info['fileName'])
                logger.debug("entry_info updated with attachment link xhtml; is now: %s", entry_info)
            self.FilesAdded.append(fp)
        else:
            logger.debug("No filepath provided...")
            att_info = None

        # Add entry:
        logger.debug("Adding entry to limspage content, persistToServer=%s...", self.PersistForEveryFile)
        self.WikiLimsPage.addEntry(entry_info, persistToServer=self.PersistForEveryFile)
        # list of product names... if no product name, use list index...
        self.AddedEntries.append(entry_info[self.ResetEntryFields['productname']] if 'productname' in self.ResetEntryFields
                                    else len(self.AddedEntries)+1)
        logger.debug("Added entries: %s", ", ".join(str(item) for item in self.AddedEntries))

        # Inform the user:
        # form disappear already here.
        self.set_entry_added_message(entry_info, att_info)

        # If addNewEntryWithSameFile:
        if addNewEntryWithSameFile:
            #self.Tkroot.deiconify()
            logger.debug("add_entry complete (addNewEntryWithSameFile=%s", addNewEntryWithSameFile)
            return #?

        self.next_entry()
        logger.debug("add_entry complete")


    def next_entry(self):
        """
        Takes the next file in self.FilesToAdd.
        If there is a next file:
        1) Prepare the tkroot ui prompt for a new entry.
        2) Returns to the tk ui prompt.
        (the tk ui will then either call add_entry, which will call this after completion.)

        If there are no more files: persist the LimsPage, close tk root and exits.
        """
        # Notice: The tkroot mainloop might not have been started yet!
        nextfp = self.nextfile()
        if nextfp:
            # pressing 'ok' makes the form disappear, already at this point...
            self.repopulatePrompt(nextfp)
            #self.Tkroot.deiconify()
            logger.debug("Next entry, filepath is '%s', returning to tk root (form/prompt).", nextfp)
            return
        else:
            # Persist limspage if an entry has been added.
            if not self.PersistForEveryFile and self.AddedEntries:
                versionComment = "Added entries: " + ", ".join(str(item) for item in self.AddedEntries)
                minorEdit = False
                logger.debug("Persisting LIMS page, versionComment is: %s", versionComment)
                self.WikiLimsPage.updatePage(struct_from='cache', versionComment=versionComment, minorEdit=minorEdit)
            # close tk root:
            self.destroy_tkroot()
            # exit:
            logger.debug("Exiting application loop.")
            return

    def destroy_tkroot(self):
        """
        Destroy the tk root (closes the ui).
        Note: tkroot.destroy = close the tk root.
              tkroot.quit = quit the tcl interpreter.
        """
        geometry = self.Tkroot.geometry()
        if geometry:
            logger.debug("Persisting tk window geometry: %s", geometry)
            # perhaps save winfo_x, winfo_y instead?
            self.Confighandler.setkey('limsapp_tk_window_geometry', geometry, autosave=True)
        else:
            logger.debug("No tk geometry??? - Is: %s", geometry)
        logger.debug("Destroying tk root")
        try:
            self.Tkroot.destroy()
        except tk.TclError as e:
            logger.debug("Error while destroying self.Tkroot: %s", e)


    def repopulatePrompt(self, filepath=None):
        """
        Re-populates the tk form.
        """
        logger.debug("Re-populating form, filepath is: %s", filepath)
        fieldvars = self.Tkroot.Fieldvars
        if filepath:
            fieldvars[self.FilepathField][0].set(filepath or "")
            fn = getNewFilename(os.path.basename(filepath), self.AttachmentNames)
            fieldvars[self.AttachmentNameField][0].set(fn)
        for header in self.ResetEntryFields.values():
            fieldvars[header][0].set('')
        logger.debug("repopulatePrompt complete.")


    def attachmentNameExists(self, fn=None):
        """
        Returns whether an attachment with fileName
        is already attached to the page.
        If it is, returns that fileName,
        and returns False otherwise.
        If no <fn> argument is provided, obtains fn from the form.
        """
        if fn is None:
            fields = self.Tkroot.get_result()
            fn = fields[self.AttachmentNameField]
        if fn and fn in self.WikiLimsPage.getAttachmentFilenames():
            return fn
        else:
            return False


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
        """ Bootstraps application and initiates UI mainloop. """
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

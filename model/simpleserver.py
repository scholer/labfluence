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


import xmlrpclib
import socket
import os.path
import itertools
import string
from Crypto.Cipher import AES
#import Crypto.Random
from Crypto.Random import random as crypt_random
import logging
logger = logging.getLogger(__name__)

# Labfluence modules and classes:
from confighandler import ConfigHandler, ExpConfigHandler
from server import login_prompt

class SimpleConfluenceXmlRpcServer(object):
    """
    Simpler, feature-less version of the Confluence server connector.
    This version does not use a confighandler object (or any other persistance),
    it is not able to report a "connection status", and most importantly
    it is not able to conduct automatic login if a failed login is encountered.
    """
    def __init__(self, appurl, username=None, password=None, logintoken=None, autologin=True, prompt='auto', ui=None):
        self.UI = ui
        self.AppUrl = appurl
        self.Username = username
        self.Password = password
        self.Logintoken = logintoken
        self.Autologin = autologin
        self.Doprompt = prompt
        logger.debug( "Making server with url: {}".format(self.AppUrl) )
        self.RpcServer = xmlrpclib.Server(appurl)
        socket.setdefaulttimeout(1.0) # without this there is no timeout, and this may block the requests
        if autologin and not logintoken and (username and password) or prompt:
            try:
                if self.Username and self.Password and self.login():
                    print 'Connected to server at {} using provided username and password...'.format(self.AppUrl)
                elif prompt is True or prompt in ('auto'):
                    self.login(prompt=True)
            except socket.error as e:
                print "Server > Unable to login, probably timeout: {}".format(e)



    def test_token(self, logintoken=None, doset=True):
        """
        Test a login token; must be decrypted.
        If token=None, will test self.Logintoken
        If doset=True (default), and the token proves valid, this method will store the token in self.
        Returns:
        - True if token is valid.
        - False if token is not valid (or if otherwise failed to connect to server <-- should be fixed...)
        - None if no valid token was provided.
        """
        if logintoken is None:
            logintoken = getattr(self, 'Logintoken', None)
        if not logintoken:
            print "ConfluenceXmlRpcServer.test_token() :: No token provided, aborting..."
            return None
        try:
            serverinfo = self.getServerInfo(logintoken)
            if doset:
                self.Logintoken = logintoken
            return True
        except xmlrpclib.Fault as err:
            print "ConfluenceXmlRpcServer.test_token() : tested token '{}' did not work; {}: {}".format( logintoken, err.faultCode, err.faultString)
            return False

    def login(self, username=None, password=None, prompt=False, retry=3, dopersist=True, msg=None):
        if username is None: username=self.Username
        if password is None: password=self.Password
        if prompt is True:
            if self.UI and hasattr(self.UI, 'login_prompt'):
                username, password = self.UI.login_prompt(username=username, msg=msg)
            else: # use command line login prompt:
                username, password = login_prompt(username)
        if not (username and password):
            logger.info( "ConfluenceXmlRpcServer.login() :: Username or password is boolean False; retrying..." )
            newmsg = "Empty username or password; please try again. Use Ctrl+C (or cancel) to cancel."
            token = self.login(username, doset=doset, prompt=prompt, retry=retry-1, msg=newmsg)
            return token
        try:
            logger.debug("Attempting server login with username: {}".format(username))
            self.Logintoken = token = self._login(username,password)
            logger.info("Logged in as '{}', received token of length {}".format(username, len(token)))
            return token
        except xmlrpclib.Fault as err:
            err_msg = "Login error: {}: {}".format( err.faultCode, err.faultString)
            #print "%d: %s" % ( err.faultCode, err.faultString)
            if prompt and retry:
                token = self.login(username, doset=doset, prompt=prompt, retry=retry-1, msg=err_msg)
            else:
                return None
        return token

    ##################################
    #### AUTHENTICATION methods ######
    ##################################

    def _login(self, username,password):
        """
        Returns a login token.
        Raises xmlrpclib.Fauls on auth error/failure.
        """
        return self.RpcServer.confluence2.login(username,password)

    def logout(self, token=None):
        """
        Returns True if token was present (and now removed), False if token was not present.
        Returns None if no token could be found.
        """
        if token is None:
            token = self.Logintoken
        if token is None:
            print "Error, login token is None."
            return
        return self.RpcServer.confluence2.logout(token)


    ################################
    #### SERVER-level methods ######
    ################################

    def getServerInfo(self, token=None):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        if token is None:
            token = self.Logintoken
        if token is None:
            print "Error, login token is None."
            return
        return self.RpcServer.confluence2.getServerInfo(token)

    def getSpaces(self, token=None):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        if token is None:
            token = self.Logintoken
        if token is None:
            print "Error, login token is None."
            return
        return self.RpcServer.confluence2.getSpaces(token)


    ################################
    #### USER methods       ########
    ################################

    def getUser(self, username, token=None):
        """
        returns a dict with name, email, fullname, url and key.
        """
        if token is None:
            token = self.Logintoken
        if token is None:
            print "Error, login token is None."
            return
        return self.RpcServer.confluence2.getUser(token, username)

    def createUser(self, newuserinfo, newuserpasswd):
        self.RpcServer.confluence2.addUser(self.Logintoken, newuserinfo, newuserpasswd)

    def getGroups(self):
        # returns a list of all groups. Requires admin priviledges.
        return self.RpcServer.confluence2.getGroups(self.Logintoken)

    def getGroup(self, group):
        # returns a single group. Requires admin priviledges.
        return self.RpcServer.confluence2.getSpaces(self.Logintoken, group)


    def getActiveUsers(self, viewAll):
        # returns a list of all active users.
        return self.RpcServer.confluence2.getActiveUsers(self.Logintoken, viewAll)




    ################################
    #### PAGE-level methods ########
    ################################

    def getPages(self, spaceKey):
        return self.RpcServer.confluence2.getPages(self.Logintoken, spaceKey)

    def getPage(self, pageId=None, spaceKey=None, pageTitle=None):
        """
        Wrapper for xmlrpc getPage method.
        Takes pageId as long (not int but string!).
        Edit: xmlrpc only supports 32-bit long ints and confluence uses 64-bit, all long integers should
        be transmitted as strings, not native ints.
        """
        if pageId:
            pageId = str(pageId) # getPage method takes a long int.
            return self.RpcServer.confluence2.getPage(self.Logintoken, pageId)
        elif spaceKey and pageTitle:
            return self.RpcServer.confluence2.getPage(self.Logintoken, spaceKey, pageTitle)
        else:
            raise("Must specify either pageId or spaceKey/pageTitle.")

    def removePage(self, pageId):
        """
        Removes a page, returns None.
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.RpcServer.confluence2.removePage(self.Logintoken, pageId)

    def movePage(self, sourcePageId, targetPageId, position='append'):
        """
        moves a page's position in the hierarchy.
        takes pageIds as strings.
        Arguments:
        * sourcePageId - the id of the page to be moved.
        * targetPageId - the id of the page that is relative to the sourcePageId page being moved.
        * position - "above", "below", or "append". (Note that the terms 'above' and 'below' refer to the relative vertical position of the pages in the page tree.)
        Details for position:
        * above -> source and target become/remain sibling pages and the source is moved above the target in the page tree.
        * below -> source and target become/remain sibling pages and the source is moved below the target in the page tree.
        * append-> source becomes a child of the target.
        """
        sourcePageId, targetPageId = str(sourcePageId), str(targetPageId)
        return self.RpcServer.confluence2.movePage(self.Logintoken, sourcePageId, targetPageId, position)

    def getPageHistory(self, pageId):
        """
        Returns all the PageHistorySummaries
         - useful for looking up the previous versions of a page, and who changed them.
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.RpcServer.confluence2.getPageHistory(self.Logintoken, pageId)

    def getAttachments(self, pageId):
        """
        Returns list of page attachments,
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.RpcServer.confluence2.getAttachments(self.Logintoken, pageId)

    def getAncestors(self, pageId):
        """
        # Returns list of page attachments
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.RpcServer.confluence2.getAncestors(self.Logintoken, pageId)

    def getChildren(self, pageId):
        """
        # Returns all the direct children of this page.
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.RpcServer.confluence2.getChildren(self.Logintoken, pageId)

    def getDescendents(self, pageId):
        """
        # Returns all the descendants of this page (children, children's children etc).
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.RpcServer.confluence2.getDescendents(self.Logintoken, pageId)

    def getComments(self, pageId):
        """
        # Returns all the comments for this page.
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.RpcServer.confluence2.getComments(self.Logintoken, pageId)

    def getComment(self, commentId):
        """
        # Returns an individual comment.
        takes commentId as string.
        """
        commentId = str(commentId)
        return self.RpcServer.confluence2.getComment(self.Logintoken, commentId)

    def removeComment(self, commentId):
        """
        # Returns an individual comment.
        takes commentId as string.
        """
        commentId = str(commentId)
        return self.RpcServer.confluence2.removeComment(self.Logintoken, commentId)

    def addComment(self, comment_struct):
        # adds a comment to the page.
        return self.RpcServer.confluence2.addComment(self.Logintoken, comment_struct)

    def editComment(self, comment_struct):
        # Updates an existing comment on the page.
        return self.RpcServer.confluence2.editComment(self.Logintoken, comment_struct)



    ######################################
    #### Attachment-level methods   ######
    ######################################

    def getAttachment(self, pageId, fileName, versionNumber=0):
        # Returns get information about an attachment.
        # versionNumber=0 is the current version.
        return self.RpcServer.confluence2.getAttachment(self.Logintoken, pageId, fileName, versionNumber)

    def getAttachmentData(self, pageId, fileName, versionNumber=0):
        # Returns the contents of an attachment. (bytes)
        return self.RpcServer.confluence2.getAttachmentData(self.Logintoken, pageId, fileName, versionNumber)

    def addAttachment(self, contentId, attachment_struct, attachmentData):
        """
        Add a new attachment to a content entity object.
        Note that this uses a lot of memory - about 4 times the size of the attachment.
        The 'long contentId' is actually a String pageId for XML-RPC.

        Note: The Experiment class' uploadAttachment() method can take a filpath.
        """
        # Uh, how to determine if attachmentData is actually a filename?
        # If attachmentData is read from a text file, it will still be a basestring...
        # Perhaps real attachmentData must be base64 encoded or something?
        #if isinstance(attachmentData, basestring):
        #    try:
        #        data = open(attachmentData, 'rb').read()
        #        attachmentData = data
        #    except IOError:
        #        pass
        return self.RpcServer.confluence2.addAttachment(self.Logintoken, contentId, attachment_struct, attachmentData)

    def removeAttachment(self, contentId, fileName):
        """remove an attachment from a content entity object.
        """
        return self.RpcServer.confluence2.removeAttachment(self.Logintoken, contentId, fileName)

    def moveAttachment(self, originalContentId, originalName, newContentEntityId, newName):
        """move an attachment to a different content entity object and/or give it a new name."""
        return self.RpcServer.confluence2.moveAttachment(self.Logintoken, originalContentId, originalName, newContentEntityId, newName)


    ####################################
    #### Content-level methods   #######
    ####################################


    def storePage(self, page_struct):
        """ adds or updates a page.
For adding, the Page given as an argument should have space, title and content fields at a minimum.
For updating, the Page given should have id, space, title, content and version fields at a minimum.
The parentId field is always optional. All other fields will be ignored.
The content is in storage format.
Note: the return value can be null, if an error that did not throw an exception occurred.
Operates exactly like updatePage() if the page already exists.
"""
        if self.VERBOSE:
            print "server.storePage() :: Storing page:"
            print page_struct
        return self.RpcServer.confluence2.storePage(self.Logintoken, page_struct)

    def updatePage(self, page_struct, pageUpdateOptions):
        """ updates a page.
The Page given should have id, space, title, content and version fields at a minimum.
The parentId field is always optional. All other fields will be ignored.
Note: the return value can be null, if an error that did not throw an exception occurred.
"""
        return self.RpcServer.confluence2.updatePage(self.Logintoken, page_struct, pageUpdateOptions)


    def convertWikiToStorageFormat(self, wikitext):
        return self.RpcServer.confluence2.convertWikiToStorageFormat(self.Logintoken, wikitext)


    def renderContent(self, spaceKey=None, pageId=None, content=None):
        """
        Returns the HTML rendered content for this page. The behaviour depends on which arguments are passed:
        * If only pageId is passed then the current content of the page will be rendered.
        * If a pageId and content are passed then the content will be rendered as if it were the body of that page.
        * If a spaceKey and content are passed then the content will be rendered as if it were on a new page in that space.
        * Whenever a spaceKey and pageId are passed the spaceKey is ignored.
        * If neither spaceKey nor pageId are passed then an error will be returned.
        takes pageId as string.
        """
        if pageId:
            pageId = str(pageId)
            if content:
                return self.RpcServer.confluence2.renderContent(self.Logintoken, pageId=pageId, content=content)
            else:
                return self.RpcServer.confluence2.renderContent(self.Logintoken, pageId=pageId, content=content)
        elif spaceKey and content:
            return self.RpcServer.confluence2.renderContent(self.Logintoken, spaceKey=pageId, content=content)
        print "server.renderContent() :: Error, must pass either pageId (with optional content) or spaceKey and content."
        return None



    ##############################
    #### Search methods      #####
    ##############################

    def search(self, query, maxResults, parameters=None):
        """search
String token, String query, int maxResults, map parameters
 return a list of results which match a given search query (including pages and other content types). This is the same as a performing a parameterised search (see below) with an empty parameter map.
 with paramters argument:
  (since 1.3) like the previous search, but you can optionally limit your search by adding parameters to the parameter map. If you do not include a parameter, the default is used instead.
Parameters for Limiting Search Results
spaceKey
* search a single space
* Values: (any valid space key)
* Default: Search all spaces
type
* Limit the content types of the items to be returned in the search results.
* Values: page, blogpost, mail, comment, attachment, spacedescription, personalinformation
* Default: Search all types
modified
* Search recently modified content
* Valus: TODAY, YESTERDAY, LASTWEEK, LASTMONTH
* Default: No limit
contributor:
* The original creator or any editor of Confluence content. For mail, this is the person who imported the mail, not the person who sent the email message.
* values: Username of a Confluence user.
* default: Results are not filtered by contributor
        """
        if parameters:
            return self.RpcServer.confluence2.search(self.Logintoken, query, parameters, maxResults)
        else:
            return self.RpcServer.confluence2.search(self.Logintoken, query, maxResults)



    ####################################
    #### Easier assist methods   #######
    ####################################

    def getPageAttachments(self, pageId):
        return self.getAttachments(self.Logintoken, pageId)

    def storePageContent(self, pageId, spaceKey, newContent, contentformat='xml'):
        """
        Modifies the content of a Confluence page.
        :param page:
        :param space:
        :param content:
        :return: bool: True if succeeded
        """
        page_struct = self.getPage(pageId, spaceKey)
        #print data
        if contentformat == 'wiki':
            newContent = self.convertWikiToStorageFormat(newContent)
        page_struct['content'] = newContent
        page = self._server.confluence2.storePage(self.Logintoken, page_struct)
        return True

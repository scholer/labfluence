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
# pylint: disable-msg=C0103,C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0201,W0221,W0621
# pylint: disable-msg=C0111,W0613
# messages:
#   C0301: Line too long (max 80), R0902: Too many instance attributes (includes dict())
#   C0302: too many lines in module; R0201: Method could be a function; W0142: Used * or ** magic
#   R0904: Too many public methods (20 max); R0913: Too many arguments;
#   W0221: Arguments differ from overridden method,
#   W0402: Use of deprechated module (e.g. string)
#   E1101: Instance of <object> has no <dynamically obtained attribute> member.
#   R0921: Abstract class not referenced. Pylint thinks any class that raises a NotImplementedError somewhere is abstract.
#   E0102: method already defined in line <...> (pylint doesn't understand properties well...)
#   E0202: An attribute affected in <...> hide this method (pylint doesn't understand properties well...)
#   C0303: Trailing whitespace (happens if you have windows-style \r\n newlines)
#   C0111: Missing method docstring (pylint insists on docstrings, even for one-liner inline functions and properties)
#   W0201: Attribute "_underscore_first_marks_insternal" defined outside __init__ -- yes, I use it in my properties.
# Regarding pylint failure of python properties: should be fixed in newer versions of pylint.

# Special for this (and other) fake modules:
# W0613 unused argument
# C0111 missing method docstring
"""
This module provides a fake confluence server which can be used for testing (and offline access, I guess).

This alternative is ubiqutously used as a server mock.

In general, to mock a server, use either of the following alternatives:
a) Use fake_server.FakeConfluenceServer in place of a normal ConfluenceXmlRpcServer(proxy) object.
b) Replace the server.RpcServer attribute of a normal ConfluenceXmlRpcServerProxy server
    with fake_xmlrpclib.FakeXmlRpcServerProxy.
c) Replace the server.RpcServer.confluence2 attribute of a normal ConfluenceXmlRpcServerProxy server
    with a FakeConfluence2Api object.

"""


import os
import yaml
import random
from datetime import datetime
import copy
import logging
from xmlrpclib import Fault, Binary
logger = logging.getLogger(__name__)

from model.utils import login_prompt, display_message


moduledir = os.path.dirname(os.path.realpath(__file__))
testdatadir = os.path.join(moduledir, "testdouble_data")
attachmentsdir = os.path.join(testdatadir, "attachments")

# Load test data-set; loading once increases test-speed by a factor 10.
def load_testdata():
    try:
        datafp = os.path.join(testdatadir, "fakeserver_testdata_large.yml")
        logger.debug("Attempting to load data from: %s", datafp)
        with open(datafp) as fd:
            testdata = yaml.load(fd)
        logger.debug("Data loaded, %s items", len(testdata))
    except IOError as e:
        logger.warning("Error while reading testdata: %r", e)
        testdata = dict()
    # Just create attachment data once - improves test run speed.
    attachmentfps = (os.path.join(attachmentsdir, fn) for fn in os.listdir(attachmentsdir))
    attachmentfps = (fp for fp in attachmentfps if os.path.isfile(fp))
    try:
        attachments = { os.path.basename(fp) : Binary(open(fp).read())
                            for fp in attachmentfps }
    except (OSError, IOError) as e:
        logger.warning("%r while loading attachments")
    return testdata, attachments
testdata, attachments = load_testdata()



class FakeConfluenceServer(object):
    """
    A fake confluence server which can be used for testing.
    Can also work as a mimic for the persistance layer of a faked confluence RPC API.
    """

    def __init__(self, confighandler=None, **kwargs):
        """
        _workdata_copy dict has items:
        - pages[pageId] = page-struct dict
        - comments[pageId] = list of comment-struct dicts for page with pageId
        - attachments[pageId] = list of attachment-struct dicts for page with pageId
        - serverinfo = serverinfo dict
        - spaces = list of space-struct dicts
        General pagestruct fields:
        - content
        - id
        - parentId
        - space
        - created
        - creator
        - modifier
        - version
        - url
        - contentStatus
        - permissions

        """
        self.Confighandler = confighandler
        logger.debug("FakeConfluenceServer initiated with kwargs (will not be used): %s", kwargs)
        self._loaded_data = testdata
        self._workdata = copy.deepcopy(self._loaded_data)
        self._attachmentsData = self._attachmentsData_org = copy.deepcopy(attachments)
        self.BaseUrl = "http://localhost:8090/"
        self._the_right_token = 'the_right_token'
        self._is_logged_in = True
        self.Username = 'fake_testusername'
        self._connectionok = True
        #self._serverparams = serverparams
        #self._username = username
        #self._password = password
        #self._logintoken = logintoken
        #self._autologin = autologin
        #self._url = url

    @property
    def UI(self, ):
        if self.Confighandler:
            return self.Confighandler.getSingleton("ui")

    def __nonzero__(self):
        return bool(self._connectionok)


    def _resetworkdata(self, ):
        del self._workdata
        self._workdata = copy.deepcopy(self._loaded_data)
        self._attachmentsData = copy.deepcopy(self._attachmentsData_org)

    def autologin(self, prompt='auto'):
        self.login()

    def find_and_test_tokens(self, doset=False):
        return 'the_right_token'

    def test_token(self, logintoken=None, doset=True):
        return True

    def clearToken(self, ):
        self._the_right_token = None

    def login(self, username=None, password=None, doset=True,
              prompt=False, retry=3, dopersist=True, msg=None):
        """
        Simulates calling server.login()
        Alternatively, simulates calling the login() method of the confluence2 API
        """
        self._is_logged_in = True
        self._connectionok = True

    def promptForUserPass(self, username=None, msg=None):
        """
        Prompts for user credentials, using either the registrered UI,
        if it has an attribute login_prompt, or else using standard
        terminal prompt.
        """
        promptopts = None
        if self.UI and hasattr(self.UI, 'login_prompt'):
            logger.debug("Using login_prompt method registrered with self.UI.")
            promptfun = self.UI.login_prompt
        else: # use command line login prompt, defined above.
            promptfun = login_prompt
        username, password = promptfun(username=username, msg=msg, options=promptopts)
        return username, password

    def logout(self):
        """
        Returns True if token was present (and now removed), False if token was not present.
        Returns None if no token could be found.
        """
        self._is_logged_in = False
        self._connectionok = False


    def getServerInfo(self):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        logger.debug("self._workdata.keys() = %s", self._workdata.keys())
        return self._workdata.get('serverinfo')
        #return self.RpcServer.confluence2.getServerInfo(token)


    def getSpaces(self):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        return self._workdata.get('spaces', list())

    ################################
    #### USER methods       ########
    ################################

    def getUser(self, username):
        """
        returns a dict with name, email, fullname, url and key.
        """
        return None
    def createUser(self, newuserinfo, newuserpasswd):
        return None
    def getGroups(self):
        # returns a list of all groups. Requires admin priviledges.
        return self._workdata.get('usergroups')

    def getGroup(self, group):
        # returns a single group. Requires admin priviledges.
        return None


    def getActiveUsers(self, viewAll):
        # returns a list of all active users.
        return None




    ################################
    #### PAGE-level methods ########
    ################################

    def getPages(self, spaceKey):
        #return filter(lambda page: page['space']==spaceKey, self._workdata.get('pages', dict()).values() )
        return [ page for page in self._workdata.get('pages', dict()).values() if page['space'] == spaceKey ]

    def getPage(self, pageId=None, spaceKey=None, pageTitle=None):
        """
        Wrapper for xmlrpc getPage method.
        Takes pageId as long (not int but string!).
        Edit: xmlrpc only supports 32-bit long ints and confluence uses 64-bit, all long integers should
        be transmitted as strings, not native ints.
        If spaceKey and pageTitle are given, but no page found, then this method
        will raise xmlrpclib.Fault, just like ConfluenceXmlRpcServer.
        """
        if pageId:
            pageId = str(pageId) # getPage method takes a long int.
            return self._workdata.get('pages', dict()).get(pageId)
        elif spaceKey and pageTitle:
            for page in self._workdata.get('pages', dict()).values():
                if page['space'] == spaceKey and page['title'] == pageTitle:
                    return page
        else:
            logger.error("getPage called with: pageId=%s, spaceKey=%s, pageTitle=%s", pageId, spaceKey, pageTitle)
            raise Fault(0, "Must specify either pageId or spaceKey/pageTitle.")

    def removePage(self, pageId):
        """
        Removes a page, returns None.
        takes pageId as string.

        Not sure what happens if pageId does not exist?
        I think it would make sense to return True if successful and False otherwise.
        """
        pageId = str(pageId)
        try:
            _ = self._workdata.get('pages', dict()).pop(pageId)
            return True
        except KeyError:
            return False

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
        return None

    def getPageHistory(self, pageId):
        """
        Returns all the PageHistorySummaries
         - useful for looking up the previous versions of a page, and who changed them.
        takes pageId as string.
        """
        pageId = str(pageId)
        return None

    def getAncestors(self, pageId):
        """
        # Returns list of page attachments
        takes pageId as string.
        """
        pageId = str(pageId)
        return None

    def getChildren(self, pageId):
        """
        # Returns all the direct children of this page.
        takes pageId as string.
        """
        pageId = str(pageId)
        childpages = [page for page in self._workdata.get('pages', dict()).values() if page['parentId'] == pageId]
        return childpages

    def getDescendents(self, pageId):
        pass


    ##############################
    #### Comment  methods   ######
    ##############################

    def getComments(self, pageId):
        pageId = str(pageId)
        return self._workdata.get('comments', dict()).get(pageId)

    def getComment(self, commentId):
        commentId = str(commentId)
        # alternative, based on http://stackoverflow.com/questions/1658505/searching-within-nested-list-in-python
        return next( (comment for pagecomments in self._workdata.get('comments', dict()).values() for comment in pagecomments if comment['id'] == commentId), None )
        # old version:
        #for pagecomments in self._workdata.get('comments', dict()).values():
        #    for comment in pagecomments :
        #        if comment['id'] == commentId:
        #            return comment

    def removeComment(self, commentId):
        """
        Based on the docs, I'd say this should return True upon successful removal
        and False otherwise.
        """
        commentId = str(commentId)
        for pid, pagecomments in self._workdata.get('comments', dict()).items():
            for i, comment in enumerate(pagecomments):
                if comment['id'] == commentId:
                    logger.debug("Deleting comment with id '%s' for pageId '%s': %s", commentId, pid, comment)
                    del pagecomments[i]
                    return True
                    #del comment # This didn't work...
        return False

    def addComment(self, comment_struct):
        """
        Should return the added comment struct.
        """
        pid = str(comment_struct['pageId'])
        self._workdata.setdefault('comments', dict()).setdefault(pid, list()).append(comment_struct)
        return comment_struct

    def editComment(self, comment_struct):
        """
        Should return the updated comment struct.
        """
        try:
            logger.debug("Updating with comment_struct: %s ", comment_struct)
            commentId = comment_struct['id']
            comment_to_edit = next( (comment for pagecomments in self._workdata.get('comments', dict()).values() for comment in pagecomments if comment['id'] == commentId) )
            comment_to_edit.update(comment_struct)
            return comment_to_edit
        except StopIteration:
            logger.debug("No comment matching comment_struct['id'] could be found, aborting...")


    ######################################
    #### Attachment-level methods   ######
    ######################################

    def getAttachments(self, pageId):
        """
        Returns list of page attachments,
        takes pageId as string.
        """
        pageId = str(pageId)
        return self._workdata.get('attachments', dict()).get(pageId)

    def getAttachment(self, pageId, fileName, versionNumber=0):
        """
        For FakeConfluenceServer, the test data only includes file/attachment info for the most recent versions.
        Thus, the versionNumber argument does not work.
        """
        return next( (attachment for pageattachments in self._workdata.get('attachments', dict()).values()
                        for attachment in pageattachments
                            if attachment['pageId'] == pageId and attachment['fileName'] == fileName), None )

    def getAttachmentData(self, pageId, fileName, versionNumber=0):
        if fileName in self._attachmentsData:
            logger.debug("Returning attachmentdata for fileName %s", fileName)
            return self._attachmentsData[fileName]
        logger.info("Could not find attachmentdata for fileName %s, keys are: %s",
                     fileName, self._attachmentsData.keys())
        #return self._attachmentsData['testdata.pdf']

    def addAttachment(self, contentId, attachment_struct, attachmentData):
        attachment = attachment_struct
        try:
            filename = attachment_struct['fileName']
            self._workdata.setdefault('attachments', dict).setdefault(contentId, list()).append(attachment_struct)
            self._attachmentsData[filename] = attachmentData
        except KeyError as e:
            logger.warning("%r while saving attachment, contentId=%s, attachment_struct=%s",
                           e, contentId, attachment_struct)
            return False
        attachment.setdefault('id', random.randint(1, 1000000))
        attachment.setdefault('pageId', contentId)
        attachment.setdefault('title', filename)
        attachment.setdefault('fileSize', len(attachmentData.data))
        attachment.setdefault('created', datetime.now())
        attachment.setdefault('creator', self.Username)
        attachment.setdefault('url', self.BaseUrl)
        attachment.setdefault('comment', "")
        return attachment

    def removeAttachment(self, contentId, fileName):
        try:
            del self._attachmentsData[fileName]
        except KeyError as e:
            logger.info("Could not remove data, %r", e)
            #return False # currently, there might not be a file for every attachment.
        structs = self._workdata.setdefault('attachments', dict).setdefault(contentId, list())
        try:
            struct = next(i for i, s in enumerate(structs) if s['fileName'] == fileName)
            structs.pop(struct)
        except StopIteration:
            logger.info("Could not remove attachment struct, no fileName '%s' for contentId %s",
                        fileName, contentId)
            return False
        return True

    def moveAttachment(self, originalContentId, originalName, newContentEntityId, newName):
        try:
            structs = self._workdata['attachments'][originalContentId]
            struct = next(s for s in structs if s['fileName'] == originalName)
        except KeyError as e:
            logger.warning("%r while locating structs for page %s", e, originalContentId)
            return False
        except StopIteration as e:
            logger.info("%r while locating struct with filename '%s' on page %s",
                        e, originalName, originalContentId)
            return False
        newpagestructs = self._workdata['attachments'].setdefault(newContentEntityId, list())
        if any(s['fileName'] == newName for s in newpagestructs):
            logger.warning("fileName %s already exist for page %s",
                           newName, newContentEntityId)
            return False
        newpagestructs.append(struct)
        structs.remove(struct)
        struct['fileName'] = newName
        return True



    ####################################
    #### Content-level methods   #######
    ####################################


    def storePage(self, page_struct):
        """
        Should be re-designed so not to raise KeyError and ValueError,
        but correct xmlrpc errors.
        """
        pages = self._workdata.get('pages', dict())
        # required keys:
        for key in ('space', 'title', 'content'):
            if key not in page_struct:
                raise KeyError("key '%s' not in page_struct '%s'", key, page_struct)
        #space = page_struct['space']
        #title = page_struct['title']
        #content = page_struct['content']
        logger.debug("Attempting to store page ")

        if 'id' in page_struct:
            logger.debug("page_struct specifies 'id' field with value %s, will UPDTATE existing page with matching pageId.", page_struct['id'])
            # update scenario: id and version required
            pageid = page_struct['id']
            version = page_struct['version']
            if pageid not in pages:
                raise KeyError("page id %s not in existing pages.", pageid)
            existing_page = pages[pageid]
            if version != existing_page['version']:
                raise ValueError("version of new page_struct, %s, does not match the version of the existing page, %s.", pageid, existing_page['version'])
            page_struct = dict(existing_page, **page_struct)
            page_struct['version'] = str(int(page_struct['version']) + 1)
        else:
            logger.debug("'id' field not found in page_struct, will add page_struct as a new page with title '%s'.", page_struct['title'])
            # addition of new page scenario. Nothing extra required, pageid and version will be set manually.
            # Make sure title does not exist in space:
            if any( page['title'] == page_struct['title'] and page['space'] == page_struct['space']
                        for page in pages.values() ):
                raise ValueError("space and title for page_struct are identical to an existing page: %s:%s.", page_struct['space'], page_struct['title'])
            pageid = page_struct['id'] = next( i for i in xrange(10000) if i not in pages )
            version = page_struct['version'] = '1'
            page_struct['created'] = datetime.now().strftime("%Y%m%dT%H:%M:%S") # currently, datetimes are stored as strings.
            page_struct['creator'] = self.Username
            page_struct['current'] = 'true'
            page_struct['contentStatus'] = 'current'
            page_struct['homePage'] = 'false'
        page_struct['modified'] = datetime.now().strftime("%Y%m%dT%H:%M:%S")
        page_struct['modifier'] = self.Username

        self._workdata.get('pages', dict())[pageid] = page_struct
        return page_struct


    def updatePage(self, page_struct, pageUpdateOptions):
        """
        Not sure how to handle PageUpdateOptions here in FakeConfluenceServer.
        It is probably only relevant if I extend the test data to include historical informations.

        """
        keys = 'id', 'space', 'title', 'content', 'version'
        for k in keys:
            if k not in page_struct:
                raise KeyError
        pageid = page_struct['id']
        server_page = self._workdata.get('pages', dict())[pageid]
        if page_struct['version'] != server_page['version']:
            raise ValueError("""Version of edited page_struct does not match the current version on the server side.
It is likely that the page has been updated on the server since it was last retrieved by you, the client.""")
        server_page.update(page_struct)


    def convertWikiToStorageFormat(self, wikitext):
        pass


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
        pass



    def search(self, query, maxResults, parameters=None):
        """
Parameters for Limiting Search Results
spaceKey:   search a single space, Values: (any valid space key), Default: Search all spaces
type:       Limit the content types of the items to be returned in the search results.
            Values: page, blogpost, mail, comment, attachment, spacedescription, personalinformation, Default: Search all types
modified:   Search recently modified content, Values: TODAY, YESTERDAY, LASTWEEK, LASTMONTH, Default: No limit
contributor:The original creator or any editor of Confluence content. For mail, this is the person who imported the mail, not the person who sent the email message.
            * values: Username of a Confluence user, default: Results are not filtered by contributor
        """
        #parameterToPageKeyMap = dict(spaceKey='space', ')
        def includepage(page):
            for k, v in parameters:
                if k == 'spaceKey' and page['space'] != v:
                    return False
                elif k == 'contributor' and v not in (page['creator'], page['modifier']):
                    return False
                elif k == 'type':
                    logger.debug("'type' included as parameter in search, but FakeConfluenceServer only supports searching pages, ignoring...")
                elif k == 'modified':
                    logger.debug("'modified' included as parameter in search, but this is not supported by FakeConfluenceServer, ignoring...")
            if query and not query.lower() in page['content'].lower():
                return False
            return True
        #pages = filter(includepage, self._workdata.get('pages', dict()).values())
        # using list comprehension to please the BDFL (and pylint):
        pages = [ page for page in self._workdata.get('pages', dict()).values()
                        if includepage(page) ]
        return pages


    def storePageContent(self, pageId, spaceKey, newContent, contentformat='xml'):
        """
        Modifies the content of a Confluence page.
        :param page:
        :param space:
        :param content:
        :return: bool: True if succeeded
        """
        return True

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
# pylint: disable-msg=C0103,C0301,C0302,R0902,R0201,R0904,R0913,W0221,W0142
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

This alternative is used for testing the ConfluenceXmlRpcServerProxy class.

In general, to mock a server, use either of the following alternatives:
a) Use fake_server.FakeConfluenceServer in place of a normal ConfluenceXmlRpcServer(proxy) object.
b) Replace the server.RpcServer attribute of a normal ConfluenceXmlRpcServerProxy server
    with fake_xmlrpclib.FakeXmlRpcServerProxy.
c) Replace the server.RpcServer.confluence2 attribute of a normal ConfluenceXmlRpcServerProxy server
    with a FakeConfluence2Api object.

In otherwords, a fake object can be inserted any place in the chain:

Normal use:     Server          ---->   xmlrpclib.ServerProxy   ---->  (confluence2 xmlrpc API) ---->   (Java server)

Replace with:   fake_server             fake_xmlrpclib                  fake_confluence2api
                .FakeConfluenceServer   .FakeXmlRpcServerProxy          .FakeConfluence2Api
"""


from datetime import datetime
import logging
from xmlrpclib import Fault
logger = logging.getLogger(__name__)

from fake_server import FakeConfluenceServer


class FakeConfluence2Api(FakeConfluenceServer):
    """
    A fake confluence API which can be used for testing.
    Can also work as a mimic for the persistance layer of a faked confluence RPC API.

    The methods here are almost identical to those in fake_server. However,
    I had to subclass this from the FakeConfluenceServer
    because the API generally takes a token as first argument.
    The server(proxy) does not do that.
    So, generally, I need to make new 'API' methods for all methods that
    the real ConfluenceXmlRpcServer routes through execute().
    I.e. all, except login().

    # TODO: Investigate whether the you can use a class decorator on fake_server.FakeConfluenceServer
            to inject the 'token' parameter.

    One other thing is the login() method:
    - The API login() is quite different from server.login()
        and the API login() is really closer to the existing server._login()
    """

    def __init__(self, **kwargs):
        FakeConfluenceServer.__init__(self, **kwargs)
        self._users = {'fakeuser':'fakepassword'}
        self._tokens = dict()



    def login(self, username, password):
        """
        Simulates calling server.login()
        Alternatively, simulates calling the login() method of the confluence2 API
        From 1.3 onwards, you can supply an empty string as the token to be treated
        as being the anonymous user.
        Raises xmlrpclib.Fault on error.
        """
        if username in self._users and self._users[username] == password:
            logger.debug('username and password accepted, returning new login token...')
            self._is_logged_in = True
            newtoken = 'very_random_token'
            self._tokens[newtoken] = username
            return newtoken
        else:
            raise Fault(0, "java.lang.Exception: com.atlassian.confluence.rpc.AuthenticationFailedException: \
Attempt to log in user '%s' failed - incorrect username/password combination." % username)



    def logout(self, token):
        """
        Returns True if token was present (and now removed), False if token was not present.
        Returns None if no token could be found.
        """
        self._is_logged_in = False
        self._connectionok = False


    def getServerInfo(self, token):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        logger.debug("self._workdata.keys() = %s", self._workdata.keys())
        return self._workdata.get('serverinfo')


    def getSpaces(self, token):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        return self._workdata.get('spaces', list())

    ################################
    #### USER methods       ########
    ################################

    def getUser(self, token, username):
        """
        returns a dict with name, email, fullname, url and key.
        """
        return None
    def createUser(self, token, newuserinfo, newuserpasswd):
        return None
    def getGroups(self, token):
        # returns a list of all groups. Requires admin priviledges.
        return self._workdata.get('usergroups')

    def getGroup(self, token, group):
        # returns a single group. Requires admin priviledges.
        return None


    def getActiveUsers(self, token, viewAll):
        # returns a list of all active users.
        return None




    ################################
    #### PAGE-level methods ########
    ################################

    def getPages(self, token, spaceKey):
        #return filter(lambda page: page['space']==spaceKey, self._workdata.get('pages', dict()).values() )
        return [ page for page in self._workdata.get('pages', dict()).values() if page['space'] == spaceKey ]

    def getPage(self, token, pageId_or_spaceKey, pageTitle=None):
        """
        Wrapper for xmlrpc getPage method.
        Takes pageId as long (not int but string!).
        Edit: xmlrpc only supports 32-bit long ints and confluence uses 64-bit, all long integers should
        be transmitted as strings, not native ints.
        If spaceKey and pageTitle are given, but no page found, then this method
        will raise xmlrpclib.Fault, just like ConfluenceXmlRpcServer.

        Emulating API function signatures: (as positional arguments only!)
            Page getPage(String token, Long pageId)
            Page getPage(String token, String spaceKey, String pageTitle)

        """
        if pageTitle:
            spaceKey = pageId_or_spaceKey
            pageId = None
        else:
            pageId = pageId_or_spaceKey
            spaceKey = None
        logger.debug("Trying to find page, pageId='%s', spaceKey='%s', pageTitle='%s'",
                     pageId, spaceKey, pageTitle)
        if pageId:
            pageId = str(pageId) # getPage method takes a long int.
            try:
                return self._workdata.get('pages', dict())[pageId]
            except KeyError:
                logger.debug("No page with pageId '%s'", pageId)
        elif spaceKey and pageTitle:
            logger.debug("Trying to find a page matching for spaceKey: '%s' and pageTitle '%s'",
                         spaceKey, pageTitle)
            pages = (page for page in self._workdata.get('pages', dict()).values()
                     if page['space'] == spaceKey and page['title'] == pageTitle)
            try:
                return next(pages)
            except StopIteration:
                pass
            #for page in self._workdata.get('pages', dict()).values():
            #    if page['space'] == spaceKey and page['title'] == pageTitle:
            #        return page
        logger.debug("No page found, raising xmlrpclib.Fault!")
        raise Fault(0, "Must specify either pageId or spaceKey/pageTitle.")

    def removePage(self, token, pageId):
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

    def movePage(self, token, sourcePageId, targetPageId, position='append'):
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

    def getPageHistory(self, token, pageId):
        """
        Returns all the PageHistorySummaries
         - useful for looking up the previous versions of a page, and who changed them.
        takes pageId as string.
        """
        pageId = str(pageId)
        return None

    def getAncestors(self, token, pageId):
        """
        # Returns list of page attachments
        takes pageId as string.
        """
        pageId = str(pageId)
        return None

    def getChildren(self, token, pageId):
        """
        # Returns all the direct children of this page.
        takes pageId as string.
        """
        pageId = str(pageId)
        childpages = [page for page in self._workdata.get('pages', dict()).values() if page['parentId'] == pageId]
        return childpages

    def getDescendents(self, token, pageId):
        pass


    ##############################
    #### Comment  methods   ######
    ##############################

    def getComments(self, token, pageId):
        pageId = str(pageId)
        return self._workdata.get('comments', dict()).get(pageId)

    def getComment(self, token, commentId):
        commentId = str(commentId)
        # alternative, based on http://stackoverflow.com/questions/1658505/searching-within-nested-list-in-python
        return next( (comment for pagecomments in self._workdata.get('comments', dict()).values() for comment in pagecomments if comment['id'] == commentId), None )
        # old version:
        #for pagecomments in self._workdata.get('comments', dict()).values():
        #    for comment in pagecomments :
        #        if comment['id'] == commentId:
        #            return comment

    def removeComment(self, token, commentId):
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

    def addComment(self, token, comment_struct):
        """
        Should return the added comment struct.
        """
        pid = str(comment_struct['pageId'])
        self._workdata.setdefault('comments', dict()).setdefault(pid, list()).append(comment_struct)
        return comment_struct

    def editComment(self, token, comment_struct):
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

    def getAttachments(self, token, pageId):
        """
        Returns list of page attachments,
        takes pageId as string.
        """
        pageId = str(pageId)
        return self._workdata.get('attachments', dict()).get(pageId)

    def getAttachment(self, token, pageId, fileName, versionNumber=0):
        """
        For FakeConfluenceServer, the test data only includes file/attachment info for the most recent versions.
        Thus, the versionNumber argument does not work.
        """
        return next( (attachment for pageattachments in self._workdata.get('attachments', dict()).values()
                        for attachment in pageattachments
                            if attachment['pageId'] == pageId and attachment['fileName'] == fileName), None )

    def getAttachmentData(self, token, pageId, fileName, versionNumber=0):
        pass

    def addAttachment(self, token, contentId, attachment_struct, attachmentData):
        pass

    def removeAttachment(self, token, contentId, fileName):
        pass

    def moveAttachment(self, token, originalContentId, originalName, newContentEntityId, newName):
        pass


    ####################################
    #### Content-level methods   #######
    ####################################


    def storePage(self, token, page_struct):
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


    def updatePage(self, token, page_struct, pageUpdateOptions):
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


    def convertWikiToStorageFormat(self, token, wikitext):
        pass


    def renderContent(self, token, spaceKey=None, pageId=None, content=None):
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



    def search(self, token, query, *args):
        """
Parameters for Limiting Search Results
spaceKey:   search a single space, Values: (any valid space key), Default: Search all spaces
type:       Limit the content types of the items to be returned in the search results.
            Values: page, blogpost, mail, comment, attachment, spacedescription, personalinformation, Default: Search all types
modified:   Search recently modified content, Values: TODAY, YESTERDAY, LASTWEEK, LASTMONTH, Default: No limit
contributor:The original creator or any editor of Confluence content. For mail, this is the person who imported the mail, not the person who sent the email message.
            * values: Username of a Confluence user, default: Results are not filtered by contributor

        Note that the xmlrpc API does not allow keyword arguments, hence the use of *args
        in place of parameters=None, maxResults=None
        # Important note: The call profile looks as:
        # Vector<SearchResult> search(String token, String query, int maxResults)
        # Vector<SearchResult> search(String token, String query, Map parameters, int maxResults)
        # Thus, the xmlrpc api makes use of java overloading. It is hard to achieve the same effect.
        #parameterToPageKeyMap = dict(spaceKey='space', ')
        """
        if len(args) == 1:
            parameters, maxResults = None, args[0]
        else:
            parameters, maxResults = args
        if parameters:
            if 'type' in parameters:
                logger.debug("'type' included as parameter in search, but FakeConfluenceServer only supports searching pages, ignoring...")
            if 'modified' in parameters:
                logger.debug("'modified' included as parameter in search, but this is not supported by FakeConfluenceServer, ignoring...")
        def includepage(page):
            if parameters:
                for k, v in parameters.items():
                    if k == 'spaceKey' and page['space'] != v:
                        return False
                    elif k == 'contributor' and v not in page['contributors']:
                        return False
                    elif k in ('type', 'modified'):
                        pass
            if query:
                if not (query.lower() in page['excerpt'].lower() or query.lower() in page['title'].lower()):
                    return False
            return True
        def makesearchresult(page):
            """
            A search result includes even less than a page summary, only:
            title, url, excerpt, type, id.
            """
            return {'space' : page['space'],
                    'id'    : page['id'],
                    'title' : page['title'],
                    'url'   : page['url'],
                    'type'  : 'page',
                    'excerpt': page['content'],
                    'contributors': [page['creator'], page['modifier']],
                    }
        #pages = filter(includepage, self._workdata.get('pages', dict()).values())
        # using list comprehension to please the BDFL (and pylint):
        searchresults = (makesearchresult(page) for page in self._workdata.get('pages', dict()).values())
        pages = [ result for result in searchresults if includepage(result) ][:maxResults]
        return pages


    def storePageContent(self, token, pageId, spaceKey, newContent, contentformat='xml'):
        """
        Modifies the content of a Confluence page.
        :param page:
        :param space:
        :param content:
        :return: bool: True if succeeded
        """
        return True

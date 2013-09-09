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
from confighandler import ConfigHandler, ExpConfigHandler



def error_out(error_message):
    print("Error: ")
    print(error_message)
    exit()

class AbstractServer(object):
    def __init__(self, host=None, url=None, port=None, username=None, password=None, logintoken=None, protocol=None, urlpostfix=None, globalconfighandler=None, VERBOSE=0):
        """
        Using a lot of hasattr checks to make sure not to override in case this is set by class descendants.
        However, this could also be simplified using getattr...
        """
        local_vars = locals()
        self.VERBOSE = local_vars.get('VERBOSE', 0)
        self.ConfigEntries = getattr(self, 'ConfigEntries', dict( (key, "server_{}".format(key.lower()) ) for key in ['Host', 'Port', 'Protocol', 'Urlpostfix', 'Url', 'Username', 'Password', 'Logintoken'] ) )
        self.GlobalConfighandler = globalconfighandler or getattr(self, 'GlobalConfighandler', dict())
        if not hasattr(self, '_defaultopts'):
            self._defaultopts = dict(host="localhost", port='80', protocol='http', urlpostfix='', username='', logintoken='')
        
        for key, cfgkey in self.ConfigEntries.items():
            # first try locals, then try self, then try GlobalConfighandler, then try _defaultopts...
            # key is uppercase (attribute name), but _defaultopts is lower.
            cfgentry = self.ConfigEntries[key]
            val = local_vars.get(key.lower(), None)
            if val is None:
                print "getattr(self, {})                returns: {}".format(key, getattr(self, key, 'not-found-default'))
                print "GlobalConfighandler.get({}) returns: {}".format(cfgentry, self.GlobalConfighandler.get(cfgentry, 'not-found-default'))
                print "self._defaultopts.get({})        returns: {}".format(key.lower(), self._defaultopts.get(key.lower(), 'not-found-default'))
                val = getattr(self, key, self.GlobalConfighandler.get(cfgentry, self._defaultopts.get(key.lower(), None) ) )
            print "--Init: setting attr '{}' to '{}' ({})".format(key, val, cfgentry)
            setattr(self, key, val)
        
        if not self.Url:
            self.Url = self.makeUrl()
            
        
#        if host:
#            self.Host = host
#        elif not hasattr(self, 'Host'):
#            # if host is already set (e.g. by child class), do not overwrite it.
#            self.Host = self.GlobalConfighandler.get('server_host', self._defaultopts.get('host'))
#        if port is not None:
#            self.Port = port # do not use the " = port or <default value" trick; input might be something that is interpreted as boolean False e.g. ""
#        elif not hasattr(self, 'Port'):
#            # if port is already set (e.g. by child class), do not overwrite it.
#            self.Port = self.GlobalConfighandler.get('server_port', self._defaultopts.get('port', '80'))
#        if protocol is not None:
#            self.Protocol = protocol # do not use the " = port or <default value" trick; input might be boolean False e.g. ""
#        elif not hasattr(self, 'Protocol'):
#            # if port is already set (e.g. by child class), do not overwrite it.
#            self.Protocol = self.GlobalConfighandler.get('server_urlpostfix', self._defaultopts.get('protocol', 'http'))
#        if urlpostfix is not None:
#            self.Urlpostfix = urlpostfix # do not use the " = port or <default value" trick; input might be boolean False e.g. ""
#        elif not hasattr(self, 'Urlpostfix'):
#            # if port is already set (e.g. by child class), do not overwrite it.
#            self.Urlpostfix = self.GlobalConfighandler.get('server_urlpostfix', self._defaultopts.get('urlpostfix', ''))
#        self.Url = url or self.makeUrl()
#        self.Username = username or self.GlobalConfighandler.get('server_username', self._defaultopts.get('username', ''))
#        self.Password = password
#        self.Logintoken = logintoken or self.GlobalConfighandler.get('server_logintoken', self._defaultopts.get('logintoken', ''))


    def makeUrl(self):#host, port, protocol='http', urlpostfix=None)
        urlfmtstr = "{protocol}://{host}:{port}{postfix}" if self.Port else "{protocol}://{host}{postfix}"
        if self.Host and self.Protocol and self.Urlpostfix:
            return urlfmtstr.format(host=self.Host, port=self.Port, protocol=self.Protocol, postfix=self.Urlpostfix)







class ConfluenceXmlRpcServer(AbstractServer):
    """
https://developer.atlassian.com/display/CONFDEV/Confluence+XML-RPC+and+SOAP+APIs
https://developer.atlassian.com/display/CONFDEV/Remote+Confluence+Methods
https://developer.atlassian.com/display/CONFDEV/Remote+Confluence+Data+Objects
    """

    def __init__(self, host=None, url=None, port=None, username=None, password=None, logintoken=None, autologin=True, protocol=None, urlpostfix=None, globalconfighandler=None, VERBOSE=0):
        #self._urlformat = "{}:{}/rpc/xmlrpc" if port else "{}/rpc/xmlrpc"
        self._defaultopts = dict(port='8090', urlpostfix='/rpc/xmlrpc', protocol='https')
#        super(AbstractServer, self).__init__(self, host=host, url=url, port=port, username=username, password=password, logintoken=logintoken, globalconfighandler=globalconfighandler)
        self.ConfigEntries = dict( (key, "wiki_{}".format(key.lower()) ) for key in ['Host', 'Port', 'Protocol', 'Urlpostfix', 'Url', 'Username', 'Password', 'Logintoken'] )
        AbstractServer.__init__(self, host=host, url=url, port=port, username=username, password=password, logintoken=logintoken, globalconfighandler=globalconfighandler, VERBOSE=VERBOSE)
        print "Making server with url: {}".format(self.Url)
        if self.Url is None:
            return None
        self.RpcServer = xmlrpclib.Server(self.Url)
        if autologin:
            if self.Logintoken and self.test_token(self.Logintoken, doset=True):
                print 'Connected to server using provided login token...'
            elif self.Username and self.Password and self.login(doset=True):
                print 'Connected to server using provided username and password...'
            elif self.find_and_test_tokens(doset=True):
                print 'Found token by magic, login ok...'
            elif getattr(self, 'Username', None) and getattr(self, 'Password', None):
                self.login()
            else:
                self.login(prompt=True)


    def find_and_test_tokens(self, doset=False):
        #print "ERROR: find_and_test_tokens() | finding login tokens is not implemented..."
        return None
        raise NotImplementedError("finding login tokens is not implemented...")

    def test_token(self, logintoken=None, doset=True):
        if logintoken is None:
            logintoken=self.Logintoken
        try:
            serverinfo = self.RpcServer.confluence2.getServerInfo(logintoken)
            if doset:
                self.Logintoken = logintoken
            return True
        except xmlrpclib.Fault as err:
            print "(tested token did not work; {}: {})".format( err.faultCode, err.faultString)
            return False

    def login(self, username=None, password=None, logintoken=None, doset=True, prompt=False, retry=3):
        if username is None: username=self.Username
        if password is None: password=self.Password
        if prompt is True:
            username, password = login_prompt(username)
        socket.setdefaulttimeout(120) # without this there is no timeout, and this may block the requests
        try:
            token = self.RpcServer.confluence2.login(username,password)
            if doset:
                self.Logintoken = token
            if self.VERBOSE > 3:
                print "Logged in as '{}', received token '{}'".format(username, token)
        except xmlrpclib.Fault as err:
            print "Login error: "
            print "%d: %s" % ( err.faultCode, err.faultString)
            if prompt and retry:
                token = self.login(username, doset=doset, prompt=prompt, retry=retry-1)
            else:
                return None
        return token


    ################################
    #### SERVER-level methods ######
    ################################

    def getServerInfo(self):
        # returns a list of dicts with space info for spaces that the user can see.
        return self.RpcServer.confluence2.getServerInfo(self.Logintoken)

    def getSpaces(self):
        # returns a list of dicts with space info for spaces that the user can see.
        return self.RpcServer.confluence2.getSpaces(self.Logintoken)


    ################################
    #### USER methods       ########
    ################################

    def getUser(self, username):
        # returns a dict with name, email, fullname, url and key.
        return self.RpcServer.confluence2.getUser(self.Logintoken, username)

    def createUser(self, newuserinfo, newuserpasswd):
        self.RpcServer.confluence2.addUser(self.Logintoken, newuserinfo, newuserpasswd)

    def getGroups(self):
        # returns a list of all groups. Requires admin priviledges.
        return self.RpcServer.confluence2.getGroups(self.Logintoken)

    def getGroup(self, group):
        # returns a single group. Requires admin priviledges.
        return self.RpcServer.confluence2.getSpaces(self.Logintoken, group)




    ################################
    #### PAGE-level methods ########
    ################################

    def getPages(self, spaceKey):
        return self.RpcServer.confluence2.getPages(self.Logintoken, spaceKey)

    def getPage(self, pageId=None, spaceKey=None, pageTitle=None):
        
        if pageId:
            return self.RpcServer.confluence2.getPage(self.Logintoken, pageId)
        elif spaceKey and pageTitle:
            return self.RpcServer.confluence2.getPage(self.Logintoken, spaceKey, pageTitle)
        else:
            raise("Must specify either pageId or spaceKey/pageTitle.")

    def removePage(self, pageId):
        return self.RpcServer.confluence2.removePage(self.Logintoken, pageId)

    def movePage(self, sourcePageId, targetPageId, position='append'):
        """moves a page to the top level of the target space. This corresponds to PageManager - movePageToTopLevel.
position either of above, below or append.
above -> source and target become/remain sibling pages and the source is moved above the target in the page tree.
below -> source and target become/remain sibling pages and the source is moved below the target in the page tree.
append-> source becomes a child of the target.
"""
        return self.RpcServer.confluence2.movePage(self.Logintoken, sourcePageId, targetPageId, position)

    def getPageHistory(self, pageId):
        return self.RpcServer.confluence2.getPageHistory(self.Logintoken, pageId)

    def getAttachments(self, pageId):
        # Returns list of page attachments
        return self.RpcServer.confluence2.getAttachments(self.Logintoken, pageId)

    def getAncestors(self, pageId):
        # Returns list of page attachments
        return self.RpcServer.confluence2.getAncestors(self.Logintoken, pageId)

    def getChildren(self, pageId):
        # Returns all the direct children of this page.
        return self.RpcServer.confluence2.getChildren(self.Logintoken, pageId)

    def getDescendents(self, pageId):
        # Returns all the descendants of this page (children, children's children etc).
        return self.RpcServer.confluence2.getDescendents(self.Logintoken, pageId)

    def getComments(self, pageId):
        # Returns all the comments for this page.
        return self.RpcServer.confluence2.getComments(self.Logintoken, pageId)

    def getComment(self, commentId):
        # Returns all the comments for this page.
        return self.RpcServer.confluence2.getComment(self.Logintoken, commentId)

    def removeComment(self, commentId):
        # Returns an individual comment.
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
        """add a new attachment to a content entity object. 
Note that this uses a lot of memory - about 4 times the size of the attachment. 
The 'long contentId' is actually a String pageId for XML-RPC.
"""
        return self.RpcServer.confluence2.getAttachmentData(self.Logintoken, contentId, attachment_struct, attachmentData)

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
        return self.RpcServer.confluence2.storePage(self.Logintoken, page_struct)

    def updatePage(self, page_struct, pageUpdateOptions):
        """ updates a page. 
The Page given should have id, space, title, content and version fields at a minimum. 
The parentId field is always optional. All other fields will be ignored. 
Note: the return value can be null, if an error that did not throw an exception occurred.
"""
        return self.RpcServer.confluence2.updatePage(self.Logintoken, page_struct, pageUpdateOptions)



    ##############################
    #### Search methods      #####
    ##############################

    def search(query, maxResults, parameters=None):
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
            newContent = self._server.confluence2.convertWikiToStorageFormat(self._token2, newContent)
        page_struct['content'] = newContent
        page = self._server.confluence2.storePage(self.Logintoken, page_struct)
        return True



def login_prompt(username=None):
    import getpass
    if username is None:
        username = getpass.getuser()
    username = raw_input('Username (enter={}):'.format(username)) or username
    #username = username_input if username_input
    password = getpass.getpass()
    return username, password

# init: (host=None, url=None, port=None, username=None, password=None, logintoken=None, autologin=True, protocol=None, urlpostfix=None)



if __name__ == "__main__":
    
    def test1():
        username = 'scholer'
        username, password = login_prompt()
        url = 'http://10.14.40.245:8090/rpc/xmlrpc'
        server = ConfluenceXmlRpcServer(url=url, username=username, password=password)


    def test_login():
        username = 'scholer'
        url = 'http://10.14.40.245:8090/rpc/xmlrpc'
        server = ConfluenceXmlRpcServer(url=url, username=username)
        #server.login(username, prompt=True, retry=4)

    def test_config1():
        paths = [ os.path.join(os.path.dirname(os.path.abspath(__file__)), '../test/config', cfg) for cfg in ('system_config.yml', 'user_config.yml', 'exp_config.yml') ]
        ch = ExpConfigHandler(*paths, VERBOSE=5)
        ch.setdefault('user', 'scholer') # set defaults only sets if not already set.
        ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc') # setkey overrides.
        print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
        server = ConfluenceXmlRpcServer(globalconfighandler=ch, VERBOSE=5)
        if server.test_token():
            print "Succesfully connected to server (retrieved serverinfo)!"
        else:
            print "Failed to obtain valid token from server !!"
        if server.Logintoken:
            ch.setkey('wiki_logintoken', server.Logintoken)
        ch.saveConfigs()


    #test_login()
    server = test_config1()




    print "TEST RUN COMPLETE!"


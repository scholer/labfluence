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


import random
import string
from datetime import datetime

from confighandler import ExpConfigHandler
from server import ConfluenceXmlRpcServer




class WikiPage(object):
    """
    In theory, WikiPage objects should be fairly oblivious.
    Try to restrain their dependency to just include a WikiServer, and rely
    on the parent object to deal with other logic, e.g. keep track of 
    a confighandler with page-tokens, etc...
    
    Page Struct entries:
Key           Type    Value                                                                                  
-------------------------------------------------------------------------------------------------------------
id            long    the id of the page                                                                     
space         String  the key of the space that this page belongs to                                         
parentId      long    the id of the parent page                                                              
title         String  the title of the page                                                                  
url           String  the url to view this page online                                                       
version       int     the version number of this page                                                        
content       String  the page content                                                                       
created       Date    timestamp page was created                                                             
creator       String  username of the creator                                                                
modified      Date    timestamp page was modified                                                            
modifier      String  username of the page's last modifier                                                   
homePage      Boolean whether or not this page is the space's homepage                                       
permissions   int     the number of permissions on this page (deprecated: may be removed in a future version)
contentStatus String  status of the page (eg. current or deleted)                                            
current       Boolean whether the page is current and not deleted                                            

PageUpdateOptions:
Key            Type    Value                                                
----------------------------------------------------------------------------
versionComment String  Edit comment for the updated page                    
minorEdit      Boolean Is this update a 'minor edit'? (default value: false)

    """


    def __init__(self, pageId, server, pageStruct=None):#, localdir=None, experiment=None):
        """
        Experiment and localdir currently not implemented.
        These are mostly intended to provide local-dir-aware config items, e.g. string formats and regexs.
        However, it might also be better to keep this logic at the Experiment(Manager) and Factory levels.
        """
        self.PageId = pageId
        self.Server = server
        #self.Experiment = experiment # Experiment object, mostly used to get local-dir-aware config items, e.g. string formats and regexs.
        #self.Localdir = localdir     # localdir; only used if no experiment is available.
        if pageStruct is None:
            self.reloadFromServer()
        else:
            self.Struct = pageStruct # Cached struct.


    def reloadFromServer(self):
        struct = self.Server.getPage(pageId=self.PageId)
        if not struct:
            print "Something went wrong retrieving Page struct from server...!"
            return False
        self.Struct = struct
        return True

    def minimumStruct(self):
        """
        Returns a minimum struct, used for updating, etc.
        """
        keys = ('id', 'space', 'title', 'content', 'version')
        struct = self.Struct
        new_struct = dict(filter(lambda t: t[0] in keys, struct.items() ) )
        return new_struct

    def updatePage(self, content=None, title=None, versionComment="", minorEdit=True, struct_from='cache', base='minimal'):
        """
        Easier wrapper for Server.updatePage; 
        If you have page_struct and pageUpdateOptions as struct, use the server method directly...
        updates a page. 
        Parameters:
        - struct_from: can be either 'cache' or 'server'. If server, will invoke reloadFromServer() before updating page.
        - base may either be 'minimal' (string) or a struct-dict, e.g. self.Struct to use cache.
        
        The Page given should have id, space, title, content and version fields at a minimum. 
        (id, space stored; provide content and optionally title.
        The parentId field is always optional. All other fields will be ignored. 
        Note: the return value can be null, if an error that did not throw an exception occurred.
        """
        if struct_from == 'server':
            if not self.reloadFromServer():
                print "Could not retrieve updated version from server, aborting..."
                return False
        if base == 'minimal':
            new_struct = self.minimumStruct()
        else:
            new_struct = base
        if content:
            new_struct['content'] = content
        if title:
            new_struct['title'] = title
        new_struct['version'] += 1
        pageUpdateOptions = dict(versionComment=versionComment, minorEdit=minorEdit)
        page_stuct = self.Server.updatePage(new_struct, pageUpdateOptions)
        if page_struct:
            self.Struct = page_struct
        return page_struct

    def movePage(self, parentId, position="append"): #struct_from='cache', base='minimal'):
        """
Position Key Effect                                                                                                  
above        source and target become/remain sibling pages and the source is moved above the target in the page tree.
append       source becomes a child of the target                                                                    
below        source and target become/remain sibling pages and the source is moved below the target in the page tree.

        """
#        if struct_from == 'server':
#            if not self.reloadFromServer():
#                print "Could not retrieve updated version from server, aborting..."
#                return False
#        if base == 'minimal':
#            new_struct = self.minimumStruct()
#        else:
#            new_struct = base
#        new_struct['parentId'] = parentId
#        page_stuct = self.Server.updatePage(self, new_struct, pageUpdateOptions)
#        if page_struct:
#            print "Page moved to parent page: {}".format(parentId)
#            self.Struct = page_struct
        self.Server.movePage(self.PageId, targetPageId, position=position)
        return page_struct


    def count(self, search_string, updateFromServer=False):
        """
        Wrapper to self.Struct; works like str.count()
        """
        if updateFromServer:
            if not self.reloadFromServer():
                print "Could not retrieve updated version from server, aborting..."
                return False
        return self.Struct['content'].count(search_string)


    def search_replace(self, search_string, replace_string, replaceLastOccurence=True, updateFromServer=True, persistToServer=True, 
                       versionComment="labfluence search-and-replace", minorEdit=True):
        """
        Does simple search-and-replace.
        Will update from server before and persist to server afterwards 
        if updateFromServer and persistToServer are True (default).
        Useful for e.g. journal assistant.
        """
        if updateFromServer:
            if not self.reloadFromServer():
                print "Could not retrieve updated version from server, aborting..."
                return False

        content = self.Struct['content']
        count = content.count(search_string)
        if count != 1:
            print "Page.search_replace() :: Warning, count of search_string '{}' is '{}' (should only be exactly 1).".format(search_string, count)
            if count < 1:
                print "search_string not found; aborting..."
                return False
        if replaceLastOccurence:
            parts = content.rsplit(search_string, 1)
            self.Struct['content'] = replace_string.join(parts)
        else:
            # alternative, but does this will replace the first-encountered rather than the last-encountered occurence.
            self.Struct['content'] = content.replace(search_string, replace_string, 1)
        if persistToServer:
            self.updatePage(struct_from='cache', versionComment=versionComment, minorEdit=minorEdit)
        return True


    def append(self, text, appendBefore=False, updateFromServer=True, persistToServer=True):
        """
        JournalAssistant should invoke with appendBefore=True.
        # Removed appendAtToken operation; is really a search_replace operation...
        """
        if updateFromServer:
            if not self.reloadFromServer():
                print "Could not retrieve updated version from server, aborting..."
                return False
        if appendBefore:
            self.Struct['content'] = text + self.Struct['content']
        else:
            self.Struct['content'] += text
        if persistToServer:
            self.updatePage(struct_from='cache', versionComment=versionComment, minorEdit=minorEdit)
        return True



    def appendAtToken(self, text, token, appendBefore=False, replaceLastOccurence=True, 
                      updateFromServer=True, persistToServer=True, 
                      versionComment="labfluence appendAtToken", minorEdit=True):
        """
        JournalAssistant should invoke with appendBefore=True.
        """
        search_string = token
        replace_string = text + token if appendBefore else text + token
        return self.search_replace(search_string, replace_string, updateFromServer=updateFromServer, 
                    persistToServer=persistToServer, versionComment=versionComment, minorEdit=minorEdit)


#    def appendAtTokenAlternatives(self, text, tokens, appendBefore=True, ifFailedAppendAtEnd=False, 
#                persistToServer=True, versionComment="labfluence appendAtTokenControlled", minorEdit=True):
#        """
#        """
#        for token in tokens:
#            search_string = token
#            if self.count(search_string) > 0:
#                replace_string = text + token if appendBefore else text + token
#                
#                return True
#        return False



    def getRenderedHTML(self, content=None):
        if content:
            html = self.Server.renderContent(self.PageId, content)
        else:
            html = self.Server.renderContent(self.PageId)

    def getAttachmentInfo(self, fileName, versionNumber=0):
        info = self.Server.getAttachment(self.PageId, filename, versionNumber)

    def getAttachmentData(self, fileName, versionNumber=0):
        data = self.Server.getAttachment(self.PageId, filename, versionNumber)

    def addAttachment(self, attachmentInfo, attachmentData):
        info = self.Server.getAttachment(self.PageId, attachmentInfo, attachmentData)

    def getAttachments(self):
        return self.Server.getAttachment(self.PageId)

    def getAncestors(self):
        return self.Server.getAncestors(self.PageId)

    def getChildren(self):
        return self.Server.getAncestors(self.PageId)

    def getDescendents(self):
        return self.Server.getAncestors(self.PageId)

    def getComments(self):
        return self.Server.getAncestors(self.PageId)


    def watchPage(self):
        return self.Server.watchPage(self.PageId)
    def removePageWatch(self):
        return self.Server.removePageWatch(self.PageId)
    def isWatchingPage(self):
        return self.Server.removePageWatch(self.PageId)

    def getPagePermissions(self):
        return self.Server.getPagePermissions(self.PageId)




class WikiPageFactory(object):
    """
    This is in charge of making new pages.
    Note: This is not for making new WikiPage objects for existing wiki pages, 
    but for creating new pages on the wiki.
    """
    def __init__(self, server, confighandler, defaulttemplate='exp_page'):
        self.Server = server
        self.Confighandler = confighandler
        self.DefaultTemplateType = defaulttemplate
        self.TemplatePagesIds = self.Confighandler.get('wiki_templates_pageIds') #{'experiment': 41746489}
        self.OverrideSpaceKeyRoot = True # Not sure this is ever used...


    def makeMinimalStruct(self, struct):
        """
        Returns a minimal page struct required for new pages.
        """
        keys = ('space', 'title', 'content', 'version')
        # alternatively:
        new_struct = dict( (k, struct.get(k)) for k in keys)
#        new_struct = dict(filter(lambda t: t[0] in keys, struct.items() ) )


    def getTemplate(self, templatetype=None):
        """
        Returns a template (text string); 
        """
        if templatetype is None:
            templatetype = self.DefaultTemplateType
        template = self.Confighandler.get(templatetype+'_template')
        if template:
            return template
        if self.TemplatePagesIds:
            print self.TemplatePagesIds
            templatePageId = self.TemplatePagesIds.get(templatetype)
            print "templatePageId: type={}, value={}".format(type(templatePageId), templatePageId)
            if templatePageId:
                templatestruct = self.Server.getPage(pageId=templatePageId)
                print "\nstruct:"
                print templatestruct
                #new_struct = self.makeMinimalStruct(struct)
                if templatestruct:
                    return templatestruct['content']
        print "No matching pageId for given template '{}', aborting...".format(templatetype)
        return


    def makeNewPageStruct(self, content, space=None, parentPageId=None, title=None, fmt_params=None, localdirpath=None, **kwargs):
        """
        The **kwargs is only used to catch un-needed stuff so you can throw in a **struct as argument.
        """
        if space is None:
            space = self.Confighandler.get('wiki_exp_root_spaceKey', space, path=localdirpath)
            if space is None:
                print "makeNewPageStruct() :: WARNING, space is still None, wiki_exp_root_spaceKey config key not found in config."
        if parentPageId is None:
            parentPageId = self.Confighandler.get('wiki_exp_root_pageId', parentPageId)
            if parentPageId is None:
                print "makeNewPageStruct() :: WARNING, parentPageId is still None, wiki_exp_root_pageId config key not found in config."
        if title is None:
            title_fmt = self.Confighandler.get('exp_series_dir_fmt')
            if title_fmt and fmt_params:
                title = title_fmt.format(**fmt_params)
        if fmt_params:
            content.format(fmt_params)
        # all fields should be strings, including pageIds and, yes, even 'version' should be be a string, not int.
        pagestruct = dict(content=content, space=space, title=title, version='1')
        if parentPageId:
            pagestruct['parentId'] = str(parentPageId) # pageIds in structs are normally long integers (except for e.g. in a comment struct...)
        return pagestruct


    def new(self, templatetype=None, fmt_params=None, localdirpath=None):
        """
        Used to create a new page (struct) and store it on the server.
        Returns a WikiPage object with a cached Struct (dict) of the stored page.
        Arguments:
        Server.storePage(): For adding, the Page given as an argument should have 
          space, title and content fields at a minimum.
        Pay attention that pageId and parentId are integers in the struct 
        (whereas when used outside a struct, pageIds must usually be passed as strings, 
        except for getPage, watch* and addAttachment methods!)
        
        Note: If passing any fmt_params, it is the caller's responsibility to ensure that fmt_params
        contains all required keys for the specified template.
        
        PS: Considering adding a localdirpath variable to provide local-dir-aware config items, e.g. string formats and regexs.
        """
        if templatetype is None:
            templatetype = self.DefaultTemplateType
        content_template = self.getTemplate(templatetype)
        new_struct = self.makeNewPageStruct(content=content_template, fmt_params=fmt_params, localdirpath=localdirpath)
        print "\nWikiPageFactory.new() :: new_struct:"
        print new_struct
        saved_struct = self.Server.storePage(new_struct)
        print "\nWikiPageFactory.new() :: saved_struct:"
        print saved_struct
        pageId = saved_struct['id']
        new_page = WikiPage(pageId, self.Server, saved_struct)
        return new_page
        #subentry_template_pageId = self.TemplatePagesIds.get('exp_subentry')
        #subentry_template_struct = self.Server.getPage(pageId=subentry_template_pageId)
        #print "\nsubentry_template_struct:"
        #print subentry_template_struct







if __name__ == '__main__':
    """
    Note: As an administrator, the content xml source can also be viewed by going "tools->view storage format".
    
    Common format parameters:
    expid           -> must be produced with expid_fmt.format(exp_series_index=exp_series_index)
    exp_titledesc
    subentry_idx    -> usually one of 'abcdef...'
    subentry_titledesc
    date, datetime  -> custom datetime object, should be datetime.
    
    
    """

    def test_factoryNew():
        ch = ExpConfigHandler(pathscheme='default1')
        wikiserver = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5, prompt='auto', autologin=True)
        factory = WikiPageFactory(wikiserver, ch)
        expid_index = 1
        expid = ch.get('expid_fmt').format(exp_series_index=expid_index)
        current_datetime = datetime.now()
        fmt_params = dict(expid=expid, 
                          exp_titledesc="First test page "+"".join(random.sample(string.ascii_letters, 5)),
                          datetime=current_datetime,
                          date=current_datetime)
        newpage = factory.new('exp_page', fmt_params=fmt_params)

    test_factoryNew()


"""
REFS:
* https://confluence.atlassian.com/display/DOC/Confluence+Storage+Format
* https://confluence.atlassian.com/display/DOC/Confluence+Storage+Format+for+Macros


Adding tokens:
* The confluence storage format does not seem to provide an obvious way to do this.
* I could use a <p tag:token></p> construct if I want the token to be hidden (preferred).
** http://www.w3schools.com/tags/ref_standardattributes.asp
** The tag could be either data-* tag, or just 'id'.
** data-* tags are new in HTML5; id is old and should be supported.
** I could also use e.g. <br id=token /> or <u/strong/em/i/tt/strike/etc tag. 
** Or (extended scope), <span>, <div> or similar?



"""

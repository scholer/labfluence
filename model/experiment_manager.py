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



class ExperimentManager(object):
    def __init__(self, config, server=None):
        self.Confighandler = config
        self.Server = server
#        cfg = self.Confighandler.getConfig(what='combined')
#        self.


    """ CONFIG RELATED """

    def getWikiExpRootSpaceKey(self):
        return self.Confighandler.get('wiki_exp_root_spaceKey')

    def getWikiExpRootPageId(self):
        return self.Confighandler.get('wiki_exp_root_pageId')


    def getLocalExpRootDir(self):
        return self.Confighandler.get('local_exp_rootDir')

    def getLocalExpSubDir(self):
        return self.Confighandler.get('local_exp_subDir')

    def getRealLocalExpRootDir(self):
        return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir)

    def getRealLocalExpSubDir(self):
        return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir, self.getLocalExpSubDir)









    def listCurrentWikiExperiments(self):
        if not self.Server:
            return
        self.Server.getChildren(self.getWikiExpRootPageId())

    def listLocalExperiments(self, directory=None):
        if directory is None:
            directory = self.getRealLocalExpSubDir()


    def listCurrentExperiments(self):
        pass


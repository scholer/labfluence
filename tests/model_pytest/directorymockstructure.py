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
# x-pyxxlint: disable-msg=C0103,C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,W0402,E0202,W0201
# pylint: disable-msg=C0103,C0301

from __future__ import print_function
import os
import yaml
import logging
logger = logging.getLogger(__name__)
# logger.debug("logger/file/module name: %s", __name__)


class DirectoryMockstructure(object):
    def __init__(self):
        """
        Structure is keps as a tree of dicts, where each dict represents a folder.
        Note that it is not possible to determine if the element 'up' is a file or a folder.
        However that would also be the case if you just have a flat list of paths.
            hej/der/word/up
        You could do something so that directories are dicts and files are something else, e.g. a string.
        """
        self._directorydictstructure = dict()
        self.path = os.path # Current implementation; makes it easy to overwrite if needed...

    def reloadFromYaml(self, filepath):
        with open(filepath) as f:
            self._directorydictstructure = yaml.load(f)

    def saveAsYaml(self, filepath):
        with open(filepath, 'wb') as f:
            yaml.dump(self._directorydictstructure, f)

    def loadFromFlatFile(self, filepath):
        with open(filepath) as f:
            self.loadFromFlatListOfPaths(f)

    def loadFromFlatListOfPaths(self, flatlistoffiles):
        flatlistoffiles = [elem for elem in (line.strip() for line in flatlistoffiles) if elem]
        for path in flatlistoffiles:
            pathitems = path.split('/')
            f = self._directorydictstructure
            for item in pathitems:
                # If item is e.g. an empty string or '.', from splitting 'hej//der' or hej/./der
                if not item or item == '.':
                    continue
                f = f.setdefault(item, dict())

    def getdirdict_old(self, dirpath):
        """
        Returns all nodes form the root to the 'dirpath' branch.
        Raises KeyError if dirpath does not exists.
        """
        pathitems = dirpath.split('/')
        f = self._directorydictstructure
        for item in pathitems:
            if item == ".":
                continue
            try:
                f = f[item]
            except KeyError as e:
                logger.debug("KeyError encountered: %s; f.keys() = %s", e, f.keys())
                raise ValueError("KeyError encountered: %s; f.keys() = %s", e, f.keys())
        return f

    def getdirdictnodes(self, dirpath):
        """
        Returns all nodes form the root to the 'dirpath' branch.
        Raises KeyError if dirpath does not exists.
        """
        # Edit: os.path.split will only split ONCE to yield --> head, tail items of path.
        pathitems = self.split(self.path.normpath(dirpath))
        logger.debug("Getting dirdict for path '%s', separate items = %s", dirpath, pathitems)
        dictnodes = [self._directorydictstructure]
        nodenames = ['<root>', ]
        for item in pathitems:
            #logger.debug("Fetching dict node for item '%s', current dictnode keys = %s", item, f.keys())
            if item in " .":
                #logger.debug("Item is '%s', staying in place.", item)
                continue
            elif item == '..':
                dictnodes.pop()
                nodenames.pop()
                continue
            try:
                dictnodes.append(dictnodes[-1][item])
                nodenames.append(item)
            except KeyError as e:
                logger.debug("KeyError encountered: %s; len(dictnodes) = %s, dictnodes[-1].keys() = %s; nodenames = %s",
                             e, len(dictnodes), dictnodes[-1].keys(), nodenames)
                raise ValueError("KeyError encountered: %s; len(dictnodes) = %s, dictnodes[-1].keys() = %s; nodenames = %s" \
                                 %(e, len(dictnodes), dictnodes[-1].keys(), nodenames))
        logger.debug("Returning dictnode for dirpath '%s', nodenames = %s; depth (number of dictnodes) = %s;\
last dictnode has %s child notes (subfolders/files).", dirpath, nodenames, len(dictnodes), len(dictnodes[-1]))
        return dictnodes, nodenames

    def getdirdict(self, dirpath):
        """
        Raises KeyError if dirpath does not exists.
        """
        dictnodes, _ = self.getdirdictnodes(dirpath)
        return dictnodes[-1]


    def listdir(self, dirpath):
        try:
            f = self.getdirdict(dirpath)
        except KeyError:
            print("Directory {} does not exists.".format(dirpath))
            raise OSError("Directory '{}' does not exists.".format(dirpath))
        else:
            return f.keys()

    def isdir(self, dirpath):
        """
        Criteria: If a path dict is empty and the basename of the path contains an extension,
        e.g. ".txt", then assume that it is a file.
        Otherwise, it is a directory.
        """
        fdict = self.getdirdict(dirpath)
        if not fdict and os.path.splitext(dirpath)[1]:
            #logger.debug("Dirpath '%s' is NOT a folder.", dirpath)
            return False
        #logger.debug("Dirpath '%s' IS a folder.", dirpath)
        return True

    @staticmethod
    def getRealPath(basedir=''):
        #if basedir[0] == '/':
        #    raise ValueError("During testings with this mock datastructure, all filepaths must be relative!")
        # Assume basedir is '2014_Aarhus/RS191 HCav annealing screen1', then just return if.
        # If it is anything else, there is not really anything we can do...
        return basedir

    @staticmethod
    def join(*paths):
        return os.path.join(*paths)

    @staticmethod
    def split(path):
        return path.replace('\\', '/').split('/')

    def rename(self, currentpath, newbasename):
        """
        This only works for changing the basename, not the whole tree.
        (That is also how the os.rename works -- os.renames is the super version...)
        """
        logger.info("Renaming '%s' to '%s'...", currentpath, newbasename)
        dictnodes, nodenames = self.getdirdictnodes(currentpath)
        # returns list of dicts, one dict for each node, e.g.
        #   2014/RS190_something/RS190c_much_else  --> should give nodes,
        #   [root-node, 2014-node, RS190-node, RS190c-node]
        if not dictnodes:
            # Was not found:
            raise OSError("Path '%s' does not exists", currentpath)
        parentnode = dictnodes[-2]      # second-last element
        currentbasename = nodenames[-1] # last element
        if currentbasename == newbasename:
            print("currentbasename == newbasename: ('%s' == '%s'), not doing anything..." % (currentbasename, newbasename))
            return
        if newbasename in parentnode:
            raise OSError("A node with name '%s' already exists!", newbasename)
        # pop the last path from the dictnodes tree-branch:
        logger.info("Popping node %r from parentnode with items %s, and re-inserting the node as key %r",
                    currentbasename, parentnode.keys(), newbasename)
        currentnode = parentnode.pop(currentbasename)
        # re-insert with new key name:
        parentnode[newbasename] = currentnode

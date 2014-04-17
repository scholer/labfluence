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
# pylint: disable=C0103,W0212


import os
import logging
logger = logging.getLogger(__name__)

def walkup(path, num=1):
    """
    Simple method to 'walk up a path':
    path = '/path/to/some/deep/directory'
        walkup(dirpath)  -->    '/path/to/some/deep'
        walkup(dirpath, 2)  -->    '/path/to/some'
        walkup(dirpath, num=3)  -->    '/path/to'
    Note: It doesn't matter if the path is file or directory, any walkup will go 'up', i.e.
        walkup('/path/to/some/deep/directory/myfile.txt') --> '/path/to/some/deep/directory'
    """
    if num > 0:
        path = os.path.dirname(path)
        num -= 1
        path = walkup(path, num)
    return path


def getPathParents(path, version=1, topfirst=True):
    """
    get parents list:
    e.g. for /home/scholer/Documents/, return:
     ['/', '/home', '/home/scholer', '/home/scholer/Documents']
    if topfirst is false, returns the above, reversed.
    Implemented in three different ways, determined by 'version'.
    """
    if version == 1:
        def getparents(path):
            """
            A generator, that returns the path and its parents
            """
            _, path = os.path.splitdrive(path)
            while True:
                yield path # yield first, to also return the input dir.
                parent = os.path.dirname(path)
                if parent == path:
                    break
                path = parent
        if topfirst:
            return reversed(list(getparents(path)))
        else:
            return getparents(path)
    # other implementations:
    #paths = list()
    #if version == 2:
    #    for dirname in os_path_split_asunder(path):
    #        if not paths:
    #            # Set the first element in paths.
    #            paths = [dirname]
    #        else:
    #            paths.append(os.path.join(paths[-1], dirname))
    #    if topfirst:
    #        return paths
    #    else:
    #        return reversed(paths)
    #    return paths if topfirst else reversed(paths)
    #if version == 3:
    #    while True:
    #        paths.append(path)
    #        path, tail = os.path.split(path)
    #        if not path and tail:
    #            break
    #    return reversed(paths) if topfirst else paths

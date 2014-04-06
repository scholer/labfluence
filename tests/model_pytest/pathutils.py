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

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

"""
Provides ability to interact with special LIMS (laboratory inventory
management system) pages on a server, with e.g. xhtml format.

NOTICE:
The WikiPage shouldn't really know anyting about things in the
experiment domain, such as 'subentries'. This WikiPage class should only
be small and focus on storing, retrieving page-structs, and manipulating
them in generic ways only, and additionally work as a relay to the server
for functions such as getting attachment lists, comments, etc.
"""

import re
import logging
logger = logging.getLogger(__name__)

# Models:
from page import WikiPage

class WikiLimsPage(WikiPage):
    """
    In theory, WikiPage objects should be fairly oblivious.
    Try to restrain their dependency to just include a WikiServer, and rely
    on the parent object to deal with other logic, e.g. keep track of
    a confighandler with page-tokens, etc...

    See the WikiPage class for info on pagestructs data structure/fields, etc.
    """

    #def __init__(self, pageId, server, confighandler=None, pagestruct=None):

    @property
    def LimstableRegexProg(self):
        if not getattr(self, '_limstableregexprog', None):
            regex = self.Confighandler.get('lims_table_regex')
            if not regex:
                regex = r"<table>\s*?<tbody>\s*?(P<headerrow><tr>.*?</tr>)(P<tablerows>.*)\s*?</tbody>\s*?</table>"
            self._limstableregexprog = re.compile(regex)
        return self._limstableregexprog

    def addEntry(self, entry, persistToServer=False):
        """
        Entry is dict with fields corresponding to the lims table.
        Implementation:
        1) Get table header info by using the limstable regex.
        2) Generate html row (string) looking up fields in entry.
        3) 


        """

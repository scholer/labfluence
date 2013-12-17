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
        """
        This regex is used to find a table in a xhtml string and perform
        basic parsing. Match groups must include:
         - headerrow : xhtml with the first row (expected to be the header).
         - tablerows : xhtml part of the table from the first <tr> after the headerrow to the last <tr>.
        """
        if not getattr(self, '_limstableregexprog', None):
            regex = self.Confighandler.get('xhtml_lims_table_regex')
            if not regex:
                regex = r".*<table>\s*?<tbody>\s*?(?P<headerrow><tr>.*?</tr>)(?P<tablerows>.*)\s*?</tbody>\s*?</table>"
                # <table>\s*?.*<tbody>.*\s*?(?P<headerrow><tr>.*?</tr>)?.*(?P<tablerows>.*)\s*?.*</tbody>\s*?.*</table>.*
            self._limstableregexprog = re.compile(regex, flags=re.DOTALL+re.MULTILINE)
        return self._limstableregexprog

    @property
    def TableRowRegexProg(self):
        """
        This regex is used to find rows in a table.
        match.group(1) is the content between <tr> and </tr>.
        """
        if not getattr(self, '_tablerowregexprog', None):
            regex = self.Confighandler.get('xhtml_tablerow_regex')
            if not regex:
                regex = r"<tr>(.*?)</tr>"
            self._tablerowregexprog = re.compile(regex, flags=re.DOTALL+re.MULTILINE)
        return self._tablerowregexprog

    @property
    def TableRowDataRegexProg(self):
        """
        This regex is used to parse table data.
        Returns the string between <td> and the next </td>.
        """
        if not getattr(self, '_tablerowdataregexprog', None):
            regex = self.Confighandler.get('xhtml_tablerowdata_regex')
            if not regex:
                regex = r"\s*<t[dh]>\s*(?:<p>\s*)?(.*?)\s*(?:</p>\s*)?</t[dh]>"
            self._tablerowdataregexprog = re.compile(regex, flags=re.DOTALL+re.MULTILINE)
        return self._tablerowdataregexprog



    def addEntry(self, entry, persistToServer=False, versionComment=None, minorEdit=True):
        """
        Entry is dict with keys corresponding to headers of the lims table, i.e.
            key : row-field value of new entry.
        Implementation:
        1) Get table header info by using the limstable regex.
        2) Generate html row (string) looking up fields in entry.
        3) Insert new xhtml row string between match headerrow and tablerows.
        4) Persist page if persistToServer is requested.
        """
        # self.Content is a property: probes self.Struct property,
        # which invokes self.reloadFromServer() is self._struct is not boolean True.
        xhtml = self.Content
        logger.debug("Adding entry to xhtml: %s", xhtml)
        match = self.LimstableRegexProg.match(xhtml)
        if not match:
            logger.warning("No match for re prog with pattern '%s' versus xhtml: %s", self.LimstableRegexProg.pattern, xhtml)
            return
        headers = self.getTableHeaders(match)
        try:
            entry_vals = [entry[field] for field in headers]
        except KeyError as e:
            logger.info("KeyError while sorting entry_vals list, headers = %s, entry = %s", headers, entry)
            entry_vals = [entry.get(field, "") for field in headers]
            logger.info("Defaulting to using '' for non-found keys, entry_vals = %s", entry_vals)
            if all(item=="" for item in entry_vals):
                logger.info("All entries are empty strings, so aborting...!")
                return
        entry_xhtml = "<tr>{}</tr>".format(
            "".join("<td><p>{}</p></td>".format(val) for val in entry_vals ) )
        insert_index = match.start('tablerows')
        new_xhtml = xhtml[:insert_index] + entry_xhtml + xhtml[insert_index:]
        self.Content = new_xhtml
        if persistToServer:
            if versionComment is None:
                versionComment = "Entry added by Labfluence LimsPage: {}".format(
                    entry.get('Product', "") )
            self.updatePage(struct_from='cache', versionComment=versionComment, minorEdit=minorEdit)
        return new_xhtml


    def getTableHeaders(self, match=None, xhtml=None):
        """
        Returns a list of the headers found in match.group('headerrow')
        If match is not given, use the LimstableRegexProg to parse xhtml.
        If xhtml is not given, defaults to self.Struct['content'].
        """
        #if matchorxhtml is None:
        #    matchorxhtml = self.Content
        #if isinstance(matchorxhtml, basestring):
        #    match = self.LimstableRegexProg.match(matchorxhtml)
        #else:
        #    match = matchorxhtml
        if match is None:
            if xhtml is None:
                xhtml = self.Content
            match = self.LimstableRegexProg.match(xhtml)
        if not match:
            logger.warning("No match for re prog with pattern '%s' versus xhtml: %s", self.LimstableRegexProg.pattern, xhtml)
            return
        # group(i) returns the i'th group. groups() returns all groups. groupdict() returns named groups as dict.
        headerstr = match.groupdict()['headerrow']
        headers = self.findCellsInTablerow(headerstr)
        return headers


    def findCellsInTablerow(self, rowxhtml):
        """
        Parses a xhtml table row string.

        >>> findCellsInTablerow(<tr><td>first cell</td><td>second cell</td></tr>)
        ('first cell', 'second cell')

        """
        # First attempt to remove any surrounding <tr> and </tr> tags:
        match = self.TableRowRegexProg.match(rowxhtml)
        if match:
            rowxhtml = match.group(1)
            logger.debug("rowxhtml surrounded by <tr> xhtml tags, match.group(1) is: %s", rowxhtml)
        else:
            logger.debug("rowxhtml NOT surrounded by <tr> xhtml tags: %s", rowxhtml)
        if not rowxhtml:
            logger.debug("rowxhtml is boolean false, aborting: '%s'", rowxhtml)
            return
        return [cell.strip() for cell in self.TableRowDataRegexProg.findall(rowxhtml)]

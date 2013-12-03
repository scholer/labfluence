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
# pylint: disable-msg=C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402,E0202,W0201
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
This module provides a fake xmlrpclib  which can be used for testing (and offline access, I guess).

"""


from model_testdoubles.fake_server import FakeConfluenceServer


class FakeServerProxy(object):
    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 allow_none=0, use_datetime=0):
        self.Uri = uri
        self.confluence2 = FakeConfluenceServer()



ServerProxy = Server = FakeServerProxy


class Fault(Error):
    """Indicates an XML-RPC fault package."""
    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString
    def __repr__(self):
        return (
            "<Fault %s: %s>" %
            (self.faultCode, repr(self.faultString))
            )

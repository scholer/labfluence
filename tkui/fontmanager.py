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

# python 2.7:
import tkFont

class FontManager():
    """
Standard fonts: (just use font='TkDefaultFont' when making e.g. labels...)
TkDefaultFont	The default for all GUI items not otherwise specified.
TkTextFont	Used for entry widgets, listboxes, etc.
TkFixedFont	A standard fixed-width font.
TkMenuFont	The font used for menu items.
TkHeadingFont	The font typically used for column headings in lists and tables.
TkCaptionFont	A font for window and dialog caption bars.
TkSmallCaptionFont	A smaller caption font for subwindows or tool dialogs
TkIconFont	A font for icon captions.
TkTooltipFont	A font for tooltips.

You can add new named fonts by providing name='new_font_name' when creating a font.
In this way, it will be globablly accessible.
    """
    def __init__(self):

        fonts = dict()
        defaultfont = tkFont.nametofont('TkDefaultFont')
        defaultfontspecs = defaultfont.actual()
        fonts['header1'] = dict(size=16)
        fonts['header2'] = dict(size=13, weight='bold')
        fonts['header3'] = dict(size=10, weight='bold')
        fonts['hyperlink_active'] = dict(defaultfontspecs, underline=True) # Yes, this is ok, later keys will override keys in the first dict.
        fonts['hyperlink_inactive'] = dict(defaultfontspecs, underline=False)#, color='blue') # color cannot be used as a init keyword.
        fonts['emphasis'] = dict(defaultfontspecs, slant='italic')#, color='blue') # color cannot be used as a init keyword.
        self.CustomFonts = dict()
        for name, specs in fonts.items():
            self.CustomFonts[name] = tkFont.Font(name=name, **specs)

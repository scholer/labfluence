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
# pylint: disable-msg=R0901,C0103,R0904,W0201

"""
Module with a primitive JournalViewer frame.
The journal viewer is attached to an experiment object, and
uses the experiment's methods to retrieve xhtml.
The xhtml can be displayed as raw code, or parsed and formatted
using a primitive HTML parser.
"""

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    import Tkinter as tk
    import ttk

#from subentrieslistbox import SubentriesListbox
from shared_ui_utils import ExpFrame
import formatter
from rspysol.rstkhtml import tkHTMLParser, tkHTMLWriter

import logging
logger = logging.getLogger(__name__)


class JournalViewer(ExpFrame):
    """
    Frame for viewing a wiki page journal, displaying the page's xhtml content
    in a text widget, either as raw html or rendered.
    """

    #def __init__(self, parent, experiment, **frameopts):
    #    """
    #    **frameopts refer to options for the frame.
    #    - however, if there is a textopts present in **frameopts, that item will be popped and used
    #        as argument to the text widget.
    #    """
    #    ExpFrame.__init__(self, parent, experiment, **frameopts)
        #self.Experiment = experiment
    #    textopts = dict(state='disabled', width=60)
    #    textopts.update(options)
    #    #self.Parent = parent
    #    # Uh, no. mega-widgets should always derive from ttk.Frame and not other widgets.

    def before_init(self, kwargs):
        textopts = dict(state='disabled')#, width=60)
        textopts.update(kwargs.pop('textopts', dict()))
        self.Textoptions = textopts

    def init_variables(self):
        self.JA = self.Experiment.JournalAssistant

    #def frame_defaults(self):
    #    pass

    def init_widgets(self):
        self.text = tk.Text(self, **self.Textoptions)
        self.scrollbar = ttk.Scrollbar(self)
        self.text.config(yscrollcommand=self.scrollbar.set)
        self.text.config(state='disabled')
        self.scrollbar.config(command=self.text.yview)

    def init_layout(self):
        self.text.grid(row=1, column=1, sticky="nesw")
        self.scrollbar.grid(row=1, column=2, sticky="nesw")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    def update_cache(self):
        """
        Sets the value of the text widget to the journal-assistant cache for the currently selected subentry:
        """
        cache = self.JA.getCacheContent()
        if cache:
            logger.debug("(%s) setting text area to cache string of length %s", self.__class__.__name__, len(cache))
        else:
            cache = ""
            logger.debug("(%s) self.JA.getCacheContent() did not return any cache, so setting text to empty string: %s",
                         self.__class__.__name__, len(cache))
        self.set_value(cache)

    def update_wiki_xhtml(self, ):
        """
        Loads the xhtml code into the text area
        without doing any parsing of the html.
        """
        xhtml = self.Experiment.getWikiXhtml()
        logger.debug("(%s) setting text area to raw xhtml of length %s", self.__class__.__name__, len(xhtml) if xhtml else xhtml)
        self.set_value(xhtml)


    def update_wiki_subentry(self):
        """
        Sets the value of the text widget to the journal-assistant cache for the currently selected subentry:
        Returns the html from experiment.getWikiSubentryXhtml().
        If the regex search failed, this will be None.
        """
        xhtml = self.Experiment.getWikiSubentryXhtml()
        #xhtml = "<h1>This is a header 1</h1><h4>RSNNN header</h4><p>Here is a description of RSNNN</p><h6>journal, date</h6><p>More text</p>"
        logger.debug("(%s) setting text area to subentry raw xhtml string of length %s", self.__class__.__name__, len(xhtml) if xhtml else xhtml)
        self.set_and_parse_xhtml(xhtml)
        return xhtml


    def set_and_parse_xhtml(self, xhtml=None):
        """
        Takes a xhtml text string and parses it using the tkHTMLWriter/Parser system.
        """
        # Ensure the input is ok:
        if xhtml is None:
            xhtml = self.Experiment.getWikiXhtml()
        if xhtml is None:
            xhtml = ""
        else:
            xhtml = xhtml.replace('&nbsp;', ' ')

        # prepare the text widget:
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.update_idletasks()
        if not xhtml:
            logger.debug("No xhtml, aborting...")
            self.text.config(state="disabled")
            return xhtml
        # Write the xhtml to the text widget:
        writer = tkHTMLWriter(self.text)
        fmt = formatter.AbstractFormatter(writer)
        parser = tkHTMLParser(fmt)
        parser.feed(xhtml)
        parser.close()
        # Finally, disable the text widget again
        self.text.config(state="disabled")
        logger.debug("(%s) text area updated with parsed/formatted html from string of length %s", self.__class__.__name__, len(xhtml) if xhtml else xhtml)


    def set_value(self, value):
        """
        Sets the content of the text area to <value>.
        """
        #initial_state = self.configure()['state'][4]
        initial_state = self.text.cget('state')
        self.text.configure(state='normal')
        if self.text.get('1.0', tk.END):
            self.text.delete('1.0', tk.END)
        if value:
            self.text.insert('1.0', value)
        #self.text.configure(state='disabled')
        self.text.configure(state=initial_state)
        self.text.see(tk.END) # Makes sure the end of the text is visible.
        logger.debug("(%s) - text area updated.", self.__class__.__name__)

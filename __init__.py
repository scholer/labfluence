#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2013-2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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

"""
Labfluence: Application(s) for interacting with a Confluence wiki in a laboratory setting.

Applications:
- Labfluence      : GUI Hub for managing experiments, both on the local filesystem
                    and on the wiki. Also includes a journalassistant for easy note-taking
                    during experiments.
- Labfluence CMD  : Command line interface for the model API, can perform many simple tasks
                    such as obtaining xhtml code for a page, etc.
- Labfluence LIMS : Simple GUI app for adding entries to a shared wiki page, thus
                    acting as a simple"laboratory inventory management system"

"""


import logging
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)

from apputils import getLoglevelInt, init_logging

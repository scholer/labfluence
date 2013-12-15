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
Created by Rasmus S. Sorensen <rasmusscholer@gmail.com>



"""


# python 3.x:
#from tkinter import ttk
# python 2.7:
import Tkinter as tk
import ttk

import logging
logging.addLevelName(4, 'SPAM') # Can be invoked as much as you'd like.
logger = logging.getLogger(__name__)



class LimsTkRoot(tk.Tk)
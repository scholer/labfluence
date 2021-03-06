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
Installs the labfluence configs in correct dirs:
system : <install-dir>/configs
user   : <home-dir>/.Labfluence/
"""


from setup.configinstaller import ConfigInstaller
import logging


if __name__ == '__main__':
    #logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    logfmt = "%(levelname)s: %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=logfmt)
    installer = ConfigInstaller()
    installer.install_configs()

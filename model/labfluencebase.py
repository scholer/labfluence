#!/usr/bin/env python
    # -*- coding: utf-8 -*-
##    Copyright 2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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
Base class for most labfluence classes.

"""


import logging
logger = logging.getLogger(__name__)

from mixin.simplecallbacksystem import SimpleCallbackSystem
from decorators.cache_decorator import cached_property


class LabfluenceBase(SimpleCallbackSystem):
    """
    Base class which assumes the confighandler is provied with init.

    Inherits from:
     - SimpleCallbackSystem
    """

    def __init__(self, confighandler, server=None):
        self.Confighandler = confighandler
        self._server = server
        SimpleCallbackSystem.__init__(self)


    @property
    def Server(self):
        """
        Returns server registrered in confighandler's singleton registry.
        """
        try:
            return self.Confighandler.Singletons.get('server', self._server)
        except AttributeError:
            return self._server
    @Server.setter
    def Server(self, value):
        """
        Set server in confighandler, if not already set.
        I do not allow overriding existing server if set, so using setdefault...
        """
        try:
            self.Confighandler.Singletons.setdefault('experimentmanager', value)
        except AttributeError:
            self._server = value

    @cached_property(ttl=60) # 1 minute cache...
    def ServerInfo(self):
        """ Remember, the cached_property makes a property, which must be nvoked without '()'!
        """
        return self.Server.getServerInfo()

    def getCurrentExpid(self):
        """Returns current experiment id from app_current_expid"""
        return self.Confighandler.setdefault('app_current_expid', None)
    def setCurrentExpid(self, new_expid):
        """Sets current experiment id as app_current_expid"""
        old_expid = self.getCurrentExpid()
        if old_expid != new_expid:
            self.Confighandler.setkey('app_current_expid', new_expid)
            self.Confighandler.invokeEntryChangeCallback('app_current_expid', new_expid)
    @property
    def ActiveExperimentIds(self):
        "List of active experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_active_experiments', list())
    @property
    def RecentExperimentIds(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())


    def getConfigEntry(self, entrykey):
        """
        Obtain config entry from confighandler using entrykey.
        """
        return self.Confighandler.get(entrykey)

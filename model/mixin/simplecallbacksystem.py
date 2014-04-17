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
# pylint: disable-msg=C0103,C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221
# messages:
#   C0301: Line too long (max 80), R0902: Too many instance attributes (includes dict())
#   C0302: too many lines in module; R0201: Method could be a function; W0142: Used * or ** magic
#   R0904: Too many public methods (20 max); R0913: Too many arguments;
#   W0221: Arguments differ from overridden method
"""
simple callback system
This module includes a base class that enables a simple callback system.


"""



import logging
logger = logging.getLogger(__name__)

from Tkinter import TclError



class SimpleCallbackSystem(object):
    """
    My own alternative to Kivy's EventDispatcher class,
    or obsub's @event decorator.

    Objects that inherits form this class will get a simple callback system,
    provided by the methods:
        registerPropertyCallback(<propkey>, callbackfunction) ->  used to register a callback for e.g. a property
        unregisterPropertyCallback(propkey=None, callbackfunction=None)  -> used to unregister callbacks.
        invokePropertyCallbacks(propkey, newvalue=None)

    This class and their methods does not attempt to determine IF callbacks should be called,
    i.e. it does not include logic to determine if a property has changed and only fire
    if it has changed.

    usage:

class TestClass(SimpleCallbackSystem):
    def __init__(self):
        SimpleCallbackSystem.__init__(self)

    (...)
    # Use in property setters to call callbacks when property is re-set:
    @MyProp.setter
    def MyProp(self, value):
        if value != self._myprop: # if you have the old value available...
            self._myprop = value
            self.invokePropertyCallbacks('MyProp', value)

    # Use in methods that modify the property indirectly:
    def resetMyprop(self):
        self._myprop = 0
        self.invokePropertyCallbacks('MyProp', 0)

    # Flagging properties as changed is convenient when you need to update a large batch of
    # properties, maybe via several methods, and you only want the callbacks to be invoked
    # when you are done updating the properties...
    def resetAll(self):
        if self._myprop:
            self._myprop = 0
            self.flagPropertyChanged('MyProp')
        if self._otherprop:
            self._otherprop = 0
            self.flagPropertyChanged('OtherProp')
        # Invoking with propkey=None will invoke callbacks for all properties flagged as changed.
        self.invokePropertyCallbacks(None)

    """

    def __init__(self):
        # Uh, I think there is something special with attribute names prefixed by two underscores
        # __attribute is converted by the interpreter to _Classname__attribute.
        self._propertiescallbacks = dict()
        self._changedproperties = set()

    def registerPropertyCallback(self, propkey, function):
        """
        Register function as a callback for property <propkey>.
        """
        self._propertiescallbacks.setdefault(propkey, list()).append(function)

    def unregisterPropertyCallback(self, propkey=None, function=None):
        """
        Unregister a callback.
        Will completely remove the function from the callback list
        for property given by propkey.
        If propkey is None, function will be unregistered for all properties.
        Propkey can also be a tuple or list of propkeys.
        """
        for propname, callbacklist in self._propertiescallbacks.items():
            if propkey is None or propkey == propname or (isinstance(propkey, (tuple, list)) and propname in propkey):
                while function in callbacklist:
                    callbacklist.remove(function)

    def invokePropertyCallbacks(self, propkey, newvalue=None):
        """
        Invoke registered callbacks for property given by propkey.
        newvalue is always passed to the callback as first and only argument.
        If no propkey is given, this will fire all callbacks for all propkeys
        registered with flagPropertyChanged.
        """
        failedfunctions = list()
        if propkey is None:
            logger.debug("propkey=%s, calling callbacks for all properties in _changedproperties=%s", propkey, self._changedproperties)
            # invokePropertyCallbacks will update self._changedproperties, so you need to iterate over a copy:
            propkeys_copy = self._changedproperties.copy()
            for changedprop in propkeys_copy:
                try:
                    nv = getattr(self, changedprop)
                except AttributeError:
                    logger.debug("%s does not have a property '%s', callbacks for this propkey will NOT be invoked.", self, changedprop)
                else:
                    self.invokePropertyCallbacks(changedprop, nv)
        else:
            for function in self._propertiescallbacks.get(propkey, list()):
                try:
                    logger.debug("Invoking callback %s(%s)...", function, newvalue)
                    function(newvalue)
                except TclError as e:
                    logger.debug("Callback for %s(%s) failed with error %s, will remove the function from the list of callbacks", function, newvalue, e)
                    failedfunctions.append(function)
            for function in failedfunctions:
                logger.info("Unregistrering callbacks for function: %s(...)", function)
                self.unregisterPropertyCallback(function=function)
            # Remove propkey from the set of flagged properties:
            self._changedproperties.discard(propkey)


    def invokeIfPropertyChanged(self, propkey, newvalue=None):
        """
        If you do not want to fire all callbacks by invoking
            invokePropertyCallbacks(None)
        then use this to only call callbacks for a single property,
        and only if the property has been flagged as changed.
        """
        if propkey in self._changedproperties:
            if newvalue is None:
                newvalue = getattr(self, propkey, None)
            self.invokePropertyCallbacks(propkey, newvalue)


    def flagPropertyChanged(self, propkey):
        """
        Mark property <propkey> as changed.
        """
        if propkey: # Do not accept non-True propkeys...
            self._changedproperties.add(propkey)
            logger.debug("property '%s' added to self._changedproperties", propkey)

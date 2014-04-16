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
# pylint: disable=W0212,R0903,C0103,W0201

"""

A minor note about python decorators:
They are defined as though they were classes.
They implement e.g. __init__ , __call__
(similar to what you could do in a normal object -- although you usually only override __init__)
and __get__
Example (PS: only works for new-style objects; uses mixin I think...)


"""

#
# © 2011 Christopher Arndt, MIT License
# From https://wiki.python.org/moin/PythonDecoratorLibrary#Cached_Properties

from functools import partial

def hashunhashable(value):
    try:
        hash(value)
    except TypeError:
        try:
            return sum(hash(key)+hashunhashable(val) for key, val in value.items())
        except AttributeError:
            return sum(hashunhashable(val) for val in value)

def gethash(value):
    try:
        h = hashunhashable(value)
        logger.debug("hash obtained with hashunhashable: %s", h)
    except TypeError:
        try:
            h = hash(str(value))
            logger.debug("hash obtained from string representation: %s", h)
        except TypeError:
            h = id(value)
            logger.debug("Could not obtain hash, using id(value) as fallback: %s", h)
    return h

def defaultset(self, value):
    self._value = value

def defaultget(self):
    return self._value


import time
import logging
logger = logging.getLogger(__name__)


class callback_property(object):
    '''
    Decorator for making a callback/observable property.

    When the property is set/changed, it will invoke registered callbacks.
    The callbacks are saved in <instance>._propertycallbacks[<property-name>] = list of callbacks.
    where <instance> or <inst> is the instance object to which this property belongs to.

    At the moment, I do not plan on storing args and kwargs in the callbacks list;
    if you want to save a callback which should be called with a particular set of
    fixed-value arguments, you should make a partial function with functools.
    The property's value will always be passed as the first argument to the callback function.

        callback(value)

    Current arguments:
        behaviour='call_instantly',     # When to invoke the callback
        enable_getter_monitor=False,    # If True, will check for changes in __get__() in addition to __set__()
        scheduler_method=None,          # Can be used to que callbacks with a UI scheduler instead of invoking immediately.
                                        # Examples: kivy.clock.Clock.schedule_once(), Tkinter.Tk().after_idle()
        skipIfLasthashIsNone=False,
        storeCallbacksInInstance=True,
        property_stores_value=False

    The property accepts a 'behaviour' argument. This will change the behaviour
    of the property:
        * 'call_instantly'  ->  all callbacks are called immediately when the property is changed.
        * 'flag_changed'    ->  do not call any callbacks; instead, simply flag the
                                property as changed in <inst>._changedproperties

    If behavior is 'flag_changed', then it is up to the modifying entity to
    invoke <inst>._invokeCallbacksForChangedProperties()
    This is mostly useful for "batch" updates, where you do not want to invoke a property's callback
    on every change, i.e. if you have a counter property that you increment in a for-loop.

    The enable_getter_monitor argument will attempt to monitor the property for changes on every
    access.

    If scheduler_method is provided, callbacks are added to the scheduler instead of being called
    instantly.

    If skipIfLasthashIsNone is set to true, then if the lasthash is none, a change in hash from
    None to anything else is *not* considered a change.

    Note that, unlike the property decorator, this decorator must be instantiated
    before it is used to wrap a method. This is because here the decoration is
    done by passing the method-to-be-wrapped to __call__, while in the property
    decorator the method-to-be-wrapped is passed to __init__ during instantiation.
    For this decorator, __init__ is used to customize the decorator, setting
    ttl and (in theory) other attributes.

    Thus, to use this property you MUST do:
        @cached_property()  # Notice the parenthesis
        def mymethod(...)
    this will NOT work:
        @cached_property    # Will not work without parenthesis;
        def mymethod        # since mymethod will then be passed to __init__

    Advanced:
    Can also be used as:
        self.A = callback_property(property_stores_value=True)
    Then you do not need to define a setter and getter for A, it will be handled by the property,
    but you have the choice to specify getter and setter at a later point.

    #######################
      THOUGHTS AND NOTES:
    #######################

    THOUGHTS REGARDING WHETHER TO SUPPORT STORING ADDITIONAL ARGUMENTS TO THE CALLBACK:
    For the confighandler's callback system, I allowed storing a high level of tailoring
    of how a callback should be invoked and if additional arguments should be provided, by storing
        *args, **kwargs, pass_newvalue_as_key=<keyword>, and pass_newvalue_as_first_arg=<bool>
    with the callback when registering it in the "list of callbacks", i.e.:
        (callback, args, kwargs, pass_newvalue_as_key, and pass_newvalue_as_first_arg)

    While this might be somewhat useful, I mostly did it to imitate (and extend) the
    API functionality of Tkinter's "after" callback system, which is as:
        after(ms,callable,*args) and after_idle(callable,*args)

    In reality, the exact same functionality should be available through lambdas or partials
    (available via functools), i.e. instead of storing:
        (callback, ['hej', 'der'], {'word': 'up'}, pass_newvalue_as_key='newvalue')
    which would be invoked as:
        callback('hej', 'der', word='up', newvalue=<value>)
    you can register the following partial:
        partial(callback, 'hej', 'der', word='up')
    When this is invoked, it will correspond to calling:
        callback('hej', 'der', <value>, word='up')

    Using partials is described by e.g. the Kivy documentation.
    However, even the Tkinter docs make use of lambdas for the "general" callback system,
    where widgets can be provided with a 'command' callback (which is called when a button is pushed),
    c.f. http://effbot.org/zone/tkinter-callbacks.htm:
        def callback(number):
            print number
        Button(text="one", command=lambda: callback(1))

    Pros and cons of just storing a single callback, possibly created with partial:

    Pros:
     - It is simpler. Much simpler.
     - I don't think I will have the need for storing callbacks with a complex pattern of arguments very often.

    Cons:
     -  Doesn't provide the same flexibility as the approach where *args, etc are stored with the callback.
     -  The callback *has* to fit the pattern. The newvalue *cannot* be passed as a kwargs.
        This basically means you cannot just take any method and store it as a callback.

    This means the following method cannot be used directly:
        dosomething(newvalue, where)    # Newvalue *has* to be the last non-keyword argument.
        dosomething(where, how='quick', with=<newvalue or None>)    # Because this takes newvalue as kwarg.

    Instead you would have to make 'adaptor' functions which re-arranges the order...

    Still, I think storing single callbacks and invoking them with the newvalue
    should suffice---especially since that is what others do :-)

    Note: Regardsless of how you roll it, it will never be as good as the native data models
    provided by the GUI toolkit you are using. (Which also implements the whole lot in C/CPython, not python)

    Kivy offers ListProperty, DictProperty, etc, which implements a dispatch/observer callback system.

    Qt has the QObject and derivatives which supports connect(), emit(), slots, signals, etc,
    Qt also has property binding and Model/View classes, but I think it mostly relies on connecting
    signals to slots.
    In general, if you want to use Qt, it would probably be easiest to re-implement the whole
    model domain as native Qt objects (QObject, QListWidget, ...)

    Tk has StringVariable, which can be bound to

    ## References ##

    Kivy:
    - http://kivy.org/docs/api-kivy.clock.html
    - http://kivy.org/docs/api-kivy.properties.html
    - https://github.com/kivy/kivy/blob/master/kivy/properties.pyx

    Qt:
    - http://zetcode.com/gui/pyqt4/eventsandsignals/
    - http://www.commandprompt.com/community/pyqt/c1267
    - http://qt-project.org/doc/qt-4.8/propertybinding.html
    - https://blog.qt.digia.com/blog/2008/08/29/data-bindings/

    '''
    def __init__(self, behaviour='call_instantly', enable_getter_monitor=False, scheduler_method=None,
                 skipIfLasthashIsNone=False, storeCallbacksInInstance=True, property_stores_value=False):
        self.lasthash = None
        self.lastcalltime = None
        self.behaviour = behaviour
        self.enable_getter_monitor = enable_getter_monitor
        self.scheduler_method = scheduler_method
        self.skipIfLasthashIsNone = skipIfLasthashIsNone
        self.storeCallbacksInInstance = storeCallbacksInInstance
        self._callbacks = list()    # This is only used if storeCallbacksInInstance=False
        self._ischanged = False
        self.fget = self.fset = self.fdel = None
        if property_stores_value:
            self.fget = defaultget
            self.fset = defaultset


    def __call__(self, fget, doc=None):
        """
        In the setup:
            @callback_property()
            def MyProperty():
                ...
        the created callback_property instance has __call__ invoked
        with the MyProperty method as only argument (fget).
        The return value (self) is then saved as the new MyProperty attribute.
        """
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        return self

    def __get__(self, inst, owner):
        ## Note: putting now = time.time() at the top will make the cache behavior dependent on the calculation time.
        ## You could argue the cache time-to-live should be calculated from _after_ the calculation
        ## has finished, not from when it was started.
        ## (This is only important if calculation time (self.fget) is comparable to self.ttl)
        value = self.fget(inst)
        if self.enable_getter_monitor:
            newhash = gethash(value)
            if newhash != self.lasthash:
                self.invokeCallbacks(inst, value)
            self.lasthash = newhash
        return value

    def __set__(self, inst, value):
        """
        Descriptor protocol:
            __set__(self, instance, value) --> None
        I override __set__ to ensure that the property is not automatically
        overwritten, e.g. if someone does:
        (class MyObj, instance myobj):
        @def cached_property
            def mycachedattr(self):
                return random.randint(0, 99)
        then later:
            myobj.mycachedattr = 2
        """
        logger.debug("__set__ invoked with inst '%s' and value '%s'", inst, value)
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(inst, value)
        newhash = gethash(value)
        if newhash != self.lasthash:
            self.invokeCallbacks(inst, value)
        self.lasthash = newhash
        now = time.time()
        try:
            cache = inst._cache
        except AttributeError:
            cache = inst._cache = {} # empty dict.
            logger.debug("No existing cache, created a new...")
        cache[self.__name__] = (value, now)

    def __delete__(self, inst):
        logger.debug("Deleting cache for property '%s'", self.__name__)
        try:
            del inst._cache[self.__name__]
        except AttributeError as e:
            logger.debug("inst '%s' doesn't have a _cache so nothing to delete. (%s)", inst, e)
        except KeyError as e:
            logger.debug("No key '%s' for _cache of inst '%s' so nothing to delete.", e, inst)


    def getter(self, fget):
        """ Returns a new callable instance, which will use fget as getter """
        return type(self)(fget, self.fset, self.fdel, self.__doc__)

    def setter(self, fset):
        """ Returns a new callable instance, which will use fset as setter """
        return type(self)(self.fget, fset, self.fdel, self.__doc__)

    def deleter(self, fdel):
        """ Returns a new callable instance, which will use fdel as deleter """
        return type(self)(self.fget, self.fset, fdel, self.__doc__)


    def registercallback(self, inst, callback):
        """
        Register callback to this property.
        callback is invoked whenever the property registers that is has changed.
        """
        if inst and self.storeCallbacksInInstance:
            try:
                inst._propertycallbacks[self.__name__] = callback
            except AttributeError:
                inst._propertycallbacks = {self.__name__ : callback}
        else:
            try:
                self._callbacks[self.__name__] = callback
            except AttributeError:
                self._callbacks = {self.__name__ : callback}

    def getcallbacks(self, inst):
        """
        This might be subject to change, so having this as a separate method for now to make
        future changes easier...
        """
        if inst and self.storeCallbacksInInstance:
            return inst._propertycallbacks[self.__name__]
        else:
            return self._callbacks

    def invokeCallbacks(self, inst, value):
        """
        Invoke all registered callbacks.
        """
        for callback in self.getcallbacks(inst):
            if self.scheduler_method:
                # Use functools.partial to create a partial function where value is set
                # (without the function actually being called here and now).
                self.scheduler_method(partial(callback, value))
            else:
                callback(value)
        try:
            del inst._changedproperties[self.__name__]
        except (AttributeError, KeyError) as e:
            logger.debug("Could not delete %s from %s._changedproperties: %s", self.__name__, inst, e)
        self._ischanged = False

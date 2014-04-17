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

import time
from functools import partial
import logging
logger = logging.getLogger(__name__)



def hashunhashable(value, recursiondepth=5):
    """
    Called recursively for
    Try to return a pseudo-hash of value. This is intended to be used
    to compare if value has been changed since last update.
    """
    try:
        return hash(value)
    except TypeError:
        if recursiondepth < 1:
            try:
                return hash(str(value))
            except TypeError:
                return id(value)
        try:
            return sum(hash(key)+hashunhashable(val, recursiondepth-1) for key, val in value.items())
        except AttributeError:
            return sum(hashunhashable(val, recursiondepth-1) for val in value)

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



class callback_property(object):
    '''
    Decorator for making a callback/observable property.

    When the property is set/changed, it will invoke registered callbacks.
    The callbacks are saved in <instance>._propertycallbacks[<property-name>] = list of callbacks.
    where <instance> or <obj> is the instance object to which this property belongs to.

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
                                property as changed in <obj>._changedproperties

    If behavior is 'flag_changed', then it is up to the modifying entity to
    invoke <obj>._invokeCallbacksForChangedProperties()
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

#####################
    Addendum:
#####################
A lot of my original implementation could not work, so I had to look for considerable inspiration in Kivy.
https://github.com/kivy/kivy/blob/master/kivy/_event.pyx
https://github.com/kivy/kivy/blob/master/kivy/properties.pyx

For instance, Kivy uses Property.link() to link a Property to its parrent instance when
the instance is initialized: (EventDispatcher is used as a mixin class...)

EventDispatcher.__init__()  ->  creates a list of attributes with dir(__cls__) and finds properties from this.
                                edit: how exactly? Why does it get the attribute and not the value returned by __get__ ?
                                ok, it gets the attr from the class, not self.
                                invokes attr.link(self, key/attrname)

Property.link(obj, name)    -> makes self._name, obj.__storage[name] = propertystorage d?, self.init_storage(obj, d)
Property.init_storage(obj, storage) -> just sets storage.value and storage.observers = list()

So uhm... yearh, if you want this thing, I think lifting it from Kivy is a good start...

Except of cause for the fact that I actually usually make use of making a getter, i.e.
    def ActiveExperimentIds(self):
        return self.confighandler. ...
And referencing self does not seem to work when EventDispatcher runs through dir(self.__class__)

Indeed, Kivy's Property getter signature is (self, EventDispatcher obj, objtype), and
it checks if obj is None.

Update:
Implementing Kivy-style self-aware properties does seem a bit elaborate, and will
always require the object instance to subclass a EventDispatcher or similar mixin class.

One alternative to this is to just implement a simple callback system in the object instance,
alá what I did in confighandler. This would be quite easy. It would, however, require
that who-ever modifies a property takes responsibility to call invokePropertyCallback(<property>),
but you can just make sure most updates are done by the object it self.

Another alternative is to implement a simple observer-event callback system,
e.g. something like what is described by DanielSank here:
http://stackoverflow.com/questions/21992849/binding-a-pyqt-pyside-widget-to-a-local-viriable-in-python

A third alternative is to make use of modules designed to implement such callback systems, e.g.
    obsub   -> implements a simple event-observer pattern, https://pypi.python.org/pypi/obsub/0.2
    pubsub  -> implements a publish-subscribe pattern, http://pubsub.sourceforge.net/

Note that obsub is about 1/10th the size of pubsub...!

The first, obsub, implements a event-observer pattern. A method can be decorated with @event.
This will essentially just invoke registerd handlers (observers) for the event:
    class MyClass(object):
        @event
        def mymethod(self, what, who, where):
            print "{} is doing {} with {} in the {}".format(self, what, who, where)

    def myhandler(self, what, who, where):
        print "After {} has completed doing {} with {}, this handler will now do something.".format(self, what, who)

    # try it:
    myobj = MyClass()
    myobj.mymethod += myhandler
    myobj.mymethod('nothing', 'the president', 'white house')
    ## should output:
    # <__main__.MyClass object at 0x02BD55D0> is doing nothing with the president in the white house
    # After <__main__.MyClass object at 0x02BD55D0> has completed doing nothing with the president, this handler will now do something.

However, this is not immediately suitable for properties. Yes, you could do it for the setter,
but it doesn't check whether the property's value has actually been changed. It should NOT be
applied blindly to the getter (would invoke it constantly), and it wouldn't check for indirect
updates either.
Obviously, the @event should not be blindly applied to e.g. experiment.mergeWikiSubentries.
Instead, to use this, I should probably create dedicated "event methods", i.e.
    @event
    def on_subentries_changed(self):
        ...

However, this seems pretty similar to what I would do with my own "simple callback system":
For a widget who wants to be notified if an experiment's subentries change:

    # In the "widget"'s code:
    def update_list(self, exp): # For obsub, the signatures MUST match. If
        ...
    def update_subentries(self, subentries): # For my callback system, the new value is passed as first (only) argument (maybe consider passing the object also).
        ...
    # obsub register:
    experiment.on_subentries_changed += self.update_list
    # simple callback register:
    experiment.registerPropertyCallback('Subentries', self.update_subentries)
    # To invoke the callbacks:
    experiment.on_subentries_changed()
    experiment.invokePropertyCallbacks('Subentries')

The two are more or less identical. Obsub requires you to create methods for each event,
and if you want to use this as a 'property-changed' notifier, that might be a bit verbose.

One difference is that to enable the functionality in a class, with obsub you create the
on_something methods with @event decorator. While with the simple callback system
I would probably have the registerPropertyCallback, unregisterPropertyCallback,
and invokePropertyCallbacks in a separate mixin class, which the class must inherit from.

The other module, pubsub, seems very similar to what is already in confighandler: a single, universal
system, where methods can be attached (registered/subscribe to) a particular key, e.g.
'app_activeexperimentids':
    confighandler.registerEntryChangeCallback(<configentry-key>, function, args=None, kwargs=None, ...)
    pubsub.pub.subscribe(listenerfunction, <topic-key>)
The callbacks are invoked when someone calls:
    confighandler.invokeEntryChangeCallback(<key>, [<new_value>])
    pubsub.pub.sendMessage(<key>, *args)
The main difference is that pubsub allows sending multiple arguments in sendMessage,
while the confighandler's callback system specifies arguments when registering the callback.
(Although you could easily change invokeEntryChangeCallback to allow for extra arguments...)
Also, pubsub implements a whole lot of message-related stuff, e.g. checks for message data specification (MDS)
upon subscribing, and checks for topic typos, etc.

Partial conclusion:

    Implementing a self-aware, observable PROPERTY alá Kivy, as I had planned with this
    callback_property has turned out to be quite complex, and require the parent object
    to have some code to make the property aware of its parent.

    Continue to use the confighandler isn't really pretty for multiple object,
    and using a full-featured publish-subscribe module wouldn't make it much better.

    OBSUB and my own simple callback system seems fairly equivalent. The code required would
    be very minor in both cases (obsub is 32 loc, my own is 33 loc). The obsub approach *is* neat,
    and while the obsub code is also quite awesome, it is also very complex
    and not easy to understand. My own simple callback system, on the other hand,
    would be very simple to understand: Each object instance has a property dict,
    keyed by property name with a corresponding list of callbacks.

    '''
    def __init__(self, fget=None, fset=None, fdel=None, doc=None,
                 behaviour='call_instantly', enable_getter_monitor=False, scheduler_method=None,
                 skipIfLasthashIsNone=False, storeCallbacksInInstance=True, property_stores_value=False):

        self.fget, self.fset, self.fdel = fget, fset, fdel
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc
        self._name = id(self) # tempoary...?
        self.lasthash = None
        self.lastcalltime = None
        self.behaviour = behaviour
        self.enable_getter_monitor = enable_getter_monitor
        self.scheduler_method = scheduler_method
        self.skipIfLasthashIsNone = skipIfLasthashIsNone
        self.storeCallbacksInInstance = storeCallbacksInInstance
        self._callbacks = list()    # This is only used if storeCallbacksInInstance=False
        self._ischanged = False
        if property_stores_value:
            self.fget = defaultget
            self.fset = defaultset
        logger.info("%s initialized: %s", self.__class__.__name__, self)

    def __call__(self, fget, doc=None, fset=None, fdel=None):
        """
        In the setup:
            @callback_property()
            def MyProperty():
                ...
        the created callback_property instance has __call__ invoked
        with the MyProperty method as only argument (fget).
        The return value (self) is then saved as the new MyProperty attribute.
        """
        logger.info("%s called, setting fget to %s", self.__class__.__name__, fget)
        #self.fget = fget
        self.fget, self.fset, self.fdel = fget, fset, fdel
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        return self

    def __get__(self, obj, owner):
        ## Note: putting now = time.time() at the top will make the cache behavior dependent on the calculation time.
        ## You could argue the cache time-to-live should be calculated from _after_ the calculation
        ## has finished, not from when it was started.
        ## (This is only important if calculation time (self.fget) is comparable to self.ttl)
        logger.info("%s - invoked get with obj = %s", self.__class__.__name__, obj)
        value = self.fget(obj)
        if self.enable_getter_monitor:
            newhash = gethash(value)
            if newhash != self.lasthash:
                self.invokeCallbacks(obj, value)
            self.lasthash = newhash
        return value

    def __set__(self, obj, value):
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
        logger.debug("__set__ invoked with obj '%s' and value '%s'", obj, value)
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)
        newhash = gethash(value)
        if newhash != self.lasthash:
            self.invokeCallbacks(obj, value)
        self.lasthash = newhash
        now = time.time()
        try:
            cache = obj._cache
        except AttributeError:
            cache = obj._cache = {} # empty dict.
            logger.debug("No existing cache, created a new...")
        cache[self.__name__] = (value, now)

    def __delete__(self, obj):
        logger.debug("Deleting cache for property '%s'", self.__name__)
        try:
            del obj._cache[self.__name__]
        except AttributeError as e:
            logger.debug("obj '%s' doesn't have a _cache so nothing to delete. (%s)", obj, e)
        except KeyError as e:
            logger.debug("No key '%s' for _cache of obj '%s' so nothing to delete.", e, obj)


    def getter(self, fget):
        """ Returns a new callable instance, which will use fget as getter """
        #return type(self)(fget, self.fset, self.fdel, self.__doc__)
        return self(fget=fget, fset=self.fset, fdel=self.fdel, doc=self.__doc__)

    def setter(self, fset):
        """ Returns a new callable instance, which will use fset as setter """
        #return type(self)(self.fget, fset, self.fdel, self.__doc__)
        return self(fget=self.fget, fset=fset, fdel=self.fdel, doc=self.__doc__)

    def deleter(self, fdel):
        """ Returns a new callable instance, which will use fdel as deleter """
        #return type(self)(self.fget, self.fset, fdel, self.__doc__)
        return self(fget=self.fget, fset=self.fset, fdel=fdel, doc=self.__doc__)

    def link(self, obj, name):
        """
        Links property to its parrent object.
        Lifted from https://github.com/kivy/kivy/blob/master/kivy/properties.pyx
        """
        # Kivy properties uses d = PropertyStorage()
        # this seems to just keep track of 1) registrered observers, 2) value(?)
        # However, I think for the moment I will just use a list of observers.
        # self.init_storage(obj, d) # just sets d.value and d.observers
        #obj.__storage[name] = d
        self._name = name
        try:
            obj.__propertiescallbacks[name] = list()
        except AttributeError:
            obj.__propertiescallbacks = dict(name=[])


    def registercallback(self, obj, callback):
        """
        Register callback to this property.
        callback is invoked whenever the property registers that is has changed.
        Question: How do you reach this method from the outside?
        obj.__dict__[MyProperty].registercallback ? - a bit long?
        """
        # Uh, much of this won't work, self has no __name__ attribute...
        if obj and self.storeCallbacksInInstance:
            try:
                obj._propertycallbacks[self.__name__] = callback
            except AttributeError:
                obj._propertycallbacks = {self.__name__ : callback}
        else:
            try:
                self._callbacks[self.__name__] = callback
            except AttributeError:
                self._callbacks = {self.__name__ : callback}

    def getcallbacks(self, obj):
        """
        This might be subject to change, so having this as a separate method for now to make
        future changes easier...
        """
        if obj and self.storeCallbacksInInstance:
            try:
                return obj._propertycallbacks[self.__name__]
            except (AttributeError, KeyError) as e:
                logger.debug("%s while obtaining callbacks from obj, probably nothing registered.", e)
                return list()
        else:
            return self._callbacks

    def invokeCallbacks(self, obj, value):
        """
        Invoke all registered callbacks.
        """
        for callback in self.getcallbacks(obj):
            if self.scheduler_method:
                # Use functools.partial to create a partial function where value is set
                # (without the function actually being called here and now).
                self.scheduler_method(partial(callback, value))
            else:
                callback(value)
        try:
            del obj._changedproperties[self.__name__]
        except (AttributeError, KeyError) as e:
            logger.debug("Could not delete %s from %s._changedproperties: %s", self.__name__, obj, e)
        self._ischanged = False

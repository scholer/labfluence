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
# pylint: disable-msg=C0111,W0613,W0622,W0102

from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)


class FakeVar(object):

    def __init__(self, value='', **kwargs):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value




class FakeTkroot(object):

    PY_VAR = 'PY_VAR'


    ############################################
    ## MODIFIED MOCK METHODS
    ## (derive new mock class for special cases)
    ############################################

    def mainloop(self, n=0):
        logger.debug("Mock FakeTkroot mainloop invoked...")
    def destroy(self, ):
        self._destroyed = True
        self._destroyed_count += 1
    def geometry(self):
        return "50x50+20+30"


    #######################################
    ## PUBLIC METHODS, GENERATED USING:
    ## generate_mock_public_methods
    ######################################

    def after(self, ms, func=None, *args):
        pass
    def after_cancel(self, id):
        pass
    def after_idle(self, func, *args):
        pass
    def aspect(self, minNumer=None, minDenom=None, maxNumer=None, maxDenom=None):
        pass
    def attributes(self, *args):
        pass
    def bbox(self, column=None, row=None, col2=None, row2=None):
        pass
    def bell(self, displayof=0):
        pass
    def bind(self, sequence=None, func=None, add=None):
        pass
    def bind_all(self, sequence=None, func=None, add=None):
        pass
    def bind_class(self, className, sequence=None, func=None, add=None):
        pass
    def bindtags(self, tagList=None):
        pass
    def cget(self, key):
        pass
    def client(self, name=None):
        pass
    def clipboard_append(self, string, **kw):
        pass
    def clipboard_clear(self, **kw):
        pass
    def clipboard_get(self, **kw):
        pass
    def colormapwindows(self, *wlist):
        pass
    def colormodel(self, value=None):
        pass
    def columnconfigure(self, index, cnf={}, **kw):
        pass
    def command(self, value=None):
        pass
    def config(self, cnf=None, **kw):
        pass
    def configure(self, cnf=None, **kw):
        pass
    def deiconify(self):
        pass
    def deletecommand(self, name):
        pass
    def event_add(self, virtual, *sequences):
        pass
    def event_delete(self, virtual, *sequences):
        pass
    def event_generate(self, sequence, **kw):
        pass
    def event_info(self, virtual=None):
        pass
    def focus(self):
        pass
    def focus_displayof(self):
        pass
    def focus_force(self):
        pass
    def focus_get(self):
        pass
    def focus_lastfor(self):
        pass
    def focus_set(self):
        pass
    def focusmodel(self, model=None):
        pass
    def frame(self):
        pass
    def getboolean(self, s):
        pass
    def getvar(self, name=PY_VAR):
        pass
    def grab_current(self):
        pass
    def grab_release(self):
        pass
    def grab_set(self):
        pass
    def grab_set_global(self):
        pass
    def grab_status(self):
        pass
    def grid(self, baseWidth=None, baseHeight=None, widthInc=None, heightInc=None):
        pass
    def grid_bbox(self, column=None, row=None, col2=None, row2=None):
        pass
    def grid_columnconfigure(self, index, cnf={}, **kw):
        pass
    def grid_location(self, x, y):
        pass
    def grid_propagate(self, flag=['_noarg_']):
        pass
    def grid_rowconfigure(self, index, cnf={}, **kw):
        pass
    def grid_size(self):
        pass
    def grid_slaves(self, row=None, column=None):
        pass
    def group(self, pathName=None):
        pass
    def iconbitmap(self, bitmap=None, default=None):
        pass
    def iconify(self):
        pass
    def iconmask(self, bitmap=None):
        pass
    def iconname(self, newName=None):
        pass
    def iconposition(self, x=None, y=None):
        pass
    def iconwindow(self, pathName=None):
        pass
    def image_names(self):
        pass
    def image_types(self):
        pass
    def keys(self):
        pass
    def lift(self, aboveThis=None):
        pass
    def loadtk(self):
        pass
    def lower(self, belowThis=None):
        pass
    def maxsize(self, width=None, height=None):
        pass
    def minsize(self, width=None, height=None):
        pass
    def nametowidget(self, name):
        pass
    def option_add(self, pattern, value, priority=None):
        pass
    def option_clear(self):
        pass
    def option_get(self, name, className):
        pass
    def option_readfile(self, fileName, priority=None):
        pass
    def overrideredirect(self, boolean=None):
        pass
    def pack_propagate(self, flag=['_noarg_']):
        pass
    def pack_slaves(self):
        pass
    def place_slaves(self):
        pass
    def positionfrom(self, who=None):
        pass
    def propagate(self, flag=['_noarg_']):
        pass
    def protocol(self, name=None, func=None):
        pass
    def quit(self):
        pass
    def readprofile(self, baseName, className):
        pass
    def register(self, func, subst=None, needcleanup=1):
        pass
    def report_callback_exception(self, exc, val, tb):
        pass
    def resizable(self, width=None, height=None):
        pass
    def rowconfigure(self, index, cnf={}, **kw):
        pass
    def selection_clear(self, **kw):
        pass
    def selection_get(self, **kw):
        pass
    def selection_handle(self, command, **kw):
        pass
    def selection_own(self, **kw):
        pass
    def selection_own_get(self, **kw):
        pass
    def send(self, interp, cmd, *args):
        pass
    def setvar(self, name=PY_VAR, value=1):
        pass
    def size(self):
        pass
    def sizefrom(self, who=None):
        pass
    def slaves(self):
        pass
    def state(self, newstate=None):
        pass
    def title(self, string=None):
        pass
    def tk_bisque(self):
        pass
    def tk_focusFollowsMouse(self):
        pass
    def tk_focusNext(self):
        pass
    def tk_focusPrev(self):
        pass
    def tk_menuBar(self, *args):
        pass
    def tk_setPalette(self, *args, **kw):
        pass
    def tk_strictMotif(self, boolean=None):
        pass
    def tkraise(self, aboveThis=None):
        pass
    def transient(self, master=None):
        pass
    def unbind(self, sequence, funcid=None):
        pass
    def unbind_all(self, sequence):
        pass
    def unbind_class(self, className, sequence):
        pass
    def update(self):
        pass
    def update_idletasks(self):
        pass
    def wait_variable(self, name=PY_VAR):
        pass
    def wait_visibility(self, window=None):
        pass
    def wait_window(self, window=None):
        pass
    def waitvar(self, name=PY_VAR):
        pass
    def winfo_atom(self, name, displayof=0):
        pass
    def winfo_atomname(self, id, displayof=0):
        pass
    def winfo_cells(self):
        pass
    def winfo_children(self):
        pass
    def winfo_class(self):
        pass
    def winfo_colormapfull(self):
        pass
    def winfo_containing(self, rootX, rootY, displayof=0):
        pass
    def winfo_depth(self):
        pass
    def winfo_exists(self):
        pass
    def winfo_fpixels(self, number):
        pass
    def winfo_geometry(self):
        pass
    def winfo_height(self):
        pass
    def winfo_id(self):
        pass
    def winfo_interps(self, displayof=0):
        pass
    def winfo_ismapped(self):
        pass
    def winfo_manager(self):
        pass
    def winfo_name(self):
        pass
    def winfo_parent(self):
        pass
    def winfo_pathname(self, id, displayof=0):
        pass
    def winfo_pixels(self, number):
        pass
    def winfo_pointerx(self):
        pass
    def winfo_pointerxy(self):
        pass
    def winfo_pointery(self):
        pass
    def winfo_reqheight(self):
        pass
    def winfo_reqwidth(self):
        pass
    def winfo_rgb(self, color):
        pass
    def winfo_rootx(self):
        pass
    def winfo_rooty(self):
        pass
    def winfo_screen(self):
        pass
    def winfo_screencells(self):
        pass
    def winfo_screendepth(self):
        pass
    def winfo_screenheight(self):
        pass
    def winfo_screenmmheight(self):
        pass
    def winfo_screenmmwidth(self):
        pass
    def winfo_screenvisual(self):
        pass
    def winfo_screenwidth(self):
        pass
    def winfo_server(self):
        pass
    def winfo_toplevel(self):
        pass
    def winfo_viewable(self):
        pass
    def winfo_visual(self):
        pass
    def winfo_visualid(self):
        pass
    def winfo_visualsavailable(self, includeids=0):
        pass
    def winfo_vrootheight(self):
        pass
    def winfo_vrootwidth(self):
        pass
    def winfo_vrootx(self):
        pass
    def winfo_vrooty(self):
        pass
    def winfo_width(self):
        pass
    def winfo_x(self):
        pass
    def winfo_y(self):
        pass
    def withdraw(self):
        pass
    def wm_aspect(self, minNumer=None, minDenom=None, maxNumer=None, maxDenom=None):
        pass
    def wm_attributes(self, *args):
        pass
    def wm_client(self, name=None):
        pass
    def wm_colormapwindows(self, *wlist):
        pass
    def wm_command(self, value=None):
        pass
    def wm_deiconify(self):
        pass
    def wm_focusmodel(self, model=None):
        pass
    def wm_frame(self):
        pass
    def wm_geometry(self, newGeometry=None):
        pass
    def wm_grid(self, baseWidth=None, baseHeight=None, widthInc=None, heightInc=None):
        pass
    def wm_group(self, pathName=None):
        pass
    def wm_iconbitmap(self, bitmap=None, default=None):
        pass
    def wm_iconify(self):
        pass
    def wm_iconmask(self, bitmap=None):
        pass
    def wm_iconname(self, newName=None):
        pass
    def wm_iconposition(self, x=None, y=None):
        pass
    def wm_iconwindow(self, pathName=None):
        pass
    def wm_maxsize(self, width=None, height=None):
        pass
    def wm_minsize(self, width=None, height=None):
        pass
    def wm_overrideredirect(self, boolean=None):
        pass
    def wm_positionfrom(self, who=None):
        pass
    def wm_protocol(self, name=None, func=None):
        pass
    def wm_resizable(self, width=None, height=None):
        pass
    def wm_sizefrom(self, who=None):
        pass
    def wm_state(self, newstate=None):
        pass
    def wm_title(self, string=None):
        pass
    def wm_transient(self, master=None):
        pass
    def wm_withdraw(self):
        pass





class FakeLimsTkroot(FakeTkroot):

    def __init__(self, app=None, confighandler=None, **kwargs):
        FakeTkroot.__init__(self)
        logger.info( "FakeTkroot initializing, with self=%s, app=%s, confighandler=%s, kwargs=%s",
                     self, app, confighandler, kwargs )
        self.Fields = dict()
        self.Confighandler = confighandler
        self.Message = FakeVar()
        self._destroyed = False
        self._destroyed_count = 0
        self._state = 'normal'


    def init_ui(self, ):
        logger.debug("init_ui called, invoking init_fieldvars...")
        self.init_fieldvars()
    def init_fieldvars(self, fields=None):
        """
        Note: The fieldvars should probably be provided by the confighandler.
        """
        if fields is None:
            fields = self.Fields
        logger.debug("init_fieldvars called, creating fieldvars from fields: %s", fields)
        self.Fieldvars = OrderedDict(
            ( key, [FakeVar(value=value), key, dict(), None] )
                for key, value in fields.items()
            )
        logger.debug("self.Fieldvars is now: %s", self.Fieldvars)
    def get_result(self, ):
        return dict( (key, speclist[0].get()) for key, speclist in self.Fieldvars.items() )


















def generate_mock_public_methods(cls, ignore_methods=None):
    """
    # with a little inspiration from http://thomassileo.com/blog/2012/12/21/dynamically-load-python-modules-or-classes/
    """
    import inspect
    import importlib

    try:
        module, clsname = cls.rsplit('.', 1)
        #__import__(module)
        module = importlib.import_module(module)
        cls = getattr(module, clsname)
    except (IndexError, ValueError) as e:
        logger.info("Could not split class '%s'. If this is in the main namespace, this is probably not an issue. (%s)", cls, e)
    except ImportError as e:
        logger.info("Error while importing module '%s'; cls=%s, derived clsname='%s'. (error was: %s)",
                    module, cls, clsname, e)
    def make_argslist(method):
        argspec = inspect.getargspec(method)
        a = argspec.args
        d = argspec.defaults or list()
        s = ", ".join( "{}".format(arg) if len(d)+i-len(a)<0 else "{}={}".format(arg, d[len(d)+i-len(a)])
                      for i, arg in enumerate(a) )
        if argspec.varargs:
            s += ", *{}".format(argspec.varargs)
        if argspec.keywords:
            s += ", **{}".format(argspec.keywords)
        return s
    if ignore_methods is None:
        ignore_methods = ('destroy', 'geometry', 'get_result')
    methods = [ tup for tup in inspect.getmembers(cls) if inspect.ismethod(tup[1]) and tup[0][0] != '_' ]
    logger.info("Methods: %s", [tup[0] for tup in methods])
    print "## Generated mock methods for {}:".format(cls)
    print "\n".join( "def {}({}):\n    pass".format(name, make_argslist(method))
                    for name, method in methods
                    if name not in ignore_methods )
    print "## --- finished ---- ##".format(cls)


###
# other useful one-liners:
# all_methods_with_kwargs_aggregator = \
#         ["{}: {}".format(name, argspec) for name, argspec in
#              ((name, inspect.getargspec(method)) for name, method in methods)
#                   if argspec.keywords is not None]

if __name__ == '__main__':

    import argparse
    logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    logging.basicConfig(level=logging.INFO, format=logfmt)

    parser = argparse.ArgumentParser(description="Labfluence LIMS mode.")
    parser.add_argument('cls', help="Class or object name to generate for.")
    parser.add_argument('--ignore', metavar='<method_name_to_ignore>', nargs='*', # default defaults to None.
                        help="Specify methods that you do not want to include when generating the list, \
                             e.g. --ignore destroy geometry get_result.")
    argsns = parser.parse_args() # produces a namespace, not a dict.

    generate_mock_public_methods(argsns.cls)

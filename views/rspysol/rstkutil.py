## vim:ts=4:et:nowrap
##
##---------------------------------------------------------------------------##
##
## PySol -- a Python Solitaire game
##
## Copyright (C) 2003 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2002 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2001 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2000 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 1999 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 1998 Markus Franz Xaver Johannes Oberhumer
## All Rights Reserved.
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; see the file COPYING.
## If not, write to the Free Software Foundation, Inc.,
## 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
## Markus F.X.J. Oberhumer
## <markus@oberhumer.com>
## http://www.oberhumer.com/pysol
##
##---------------------------------------------------------------------------##


# imports
import sys, os, re, string, time, types
import Tkinter

# Toolkit imports
#import tkinit  # Fixes some bugs in tkinter for python. Not sure this is really needed...
#from tkconst import tkversion
tkversion = (8, 0, 0, 0)
#from tkfont import getFont

getFont_cache = {}
def getFont(name, cardw=0):
    key = (name, cardw)
    font = getFont_cache.get(key)
    if font:
        return font
    # default
    font = ("Helvetica", "-14")
    #
    if name in ("canvas", "canvas_small", "small", "tree_small",):
        font = ("Helvetica", "-12")
    elif name in ("canvas_large",):
        font = ("Helvetica", "-18")
    elif name in ("canvas_card",):
        if cardw >= 71:
            font = getFont("canvas_large")
        elif cardw >= 57:
            font = ("Helvetica", "-16")
        else:
            font = ("Helvetica", "-14")
    elif name in ("canvas_fixed",):
        font = ("Courier", "-12")
    elif name in ("fixed",):
        font = ("Courier", "-14")
    elif not name in ("default",):
        pass
    #
    getFont_cache[key] = font
    return font


# /***********************************************************************
# // window manager util
# ************************************************************************/

def wm_withdraw(window):
    window.wm_withdraw()

def wm_deiconify(window):
    need_fix = os.name == "nt" and tkversion < (8, 3, 0, 0)
    if need_fix:
        # FIXME: This is needed so the window pops up on top on Windows.
        try:
            window.wm_iconify()
            window.update_idletasks()
        except Tkinter.TclError:
            # wm_iconify() may fail if the window is transient
            pass
    window.wm_deiconify()

def wm_map(window, maximized=0):
    if window.wm_state() != "iconic":
        if maximized and os.name == "nt":
            window.wm_state("zoomed")
        else:
            wm_deiconify(window)

def wm_set_icon(window, filename):
    if not filename:
        return
    if os.name == "posix":
        window.wm_iconbitmap("@" + filename)
        window.wm_iconmask("@" + filename)

__wm_get_geometry_re = re.compile(r"^(\d+)x(\d+)\+([\-]?\d+)\+([\-]?\d+)$")

def wm_get_geometry(window):
    g = window.wm_geometry()
    m = __wm_get_geometry_re.search(g)
    if not m:
        raise Tkinter.TclError, "invalid geometry " + str(g)
    l = map(int, m.groups())
    if window.wm_state() == "zoomed":
        # workaround as Tk returns the "unzoomed" origin
        l[2] = l[3] = 0
    return l


# /***********************************************************************
# // window util
# ************************************************************************/

def setTransient(window, parent, relx=None, rely=None, expose=1):
    # Make an existing toplevel window transient for a parent.
    #
    # The window must exist but should not yet have been placed; in
    # other words, this should be called after creating all the
    # subwidget but before letting the user interact.

    # remain invisible while we figure out the geometry
    window.wm_withdraw()
    window.wm_group(parent)
    need_fix = os.name == "nt" and tkversion < (8, 3, 0, 0)
    if need_fix:
        # FIXME: This is needed to avoid ugly frames on Windows.
        window.wm_geometry("+%d+%d" % (-10000, -10000))
        if expose and parent is not None:
            # FIXME: This is needed so the window pops up on top on Windows.
            window.wm_iconify()
    if parent and parent.wm_state() != "withdrawn":
        window.wm_transient(parent)
    # actualize geometry information
    window.update_idletasks()
    # show
    x, y = __getWidgetXY(window, parent, relx=relx, rely=rely)
    if need_fix:
        if expose:
            wm_deiconify(window)
        window.wm_geometry("+%d+%d" % (x, y))
    else:
        window.wm_geometry("+%d+%d" % (x, y))
        if expose:
            window.wm_deiconify()

def makeToplevel(parent, title=None, class_=None):
    # Create a Toplevel window.
    #
    # This is a shortcut for a Toplevel() instantiation plus calls to
    # set the title and icon name of the window.
    if class_:
        window = Tkinter.Toplevel(parent, class_=class_)
    else:
        window = Tkinter.Toplevel(parent)
    ##window.wm_group(parent)
    ##window.wm_command("")
    if os.name == "posix":
        window.wm_command("/bin/true")
    ##window.wm_protocol("WM_SAVE_YOURSELF", None)
    if title:
        window.wm_title(title)
        window.wm_iconname(title)
    return window

makeHelpToplevel = makeToplevel

def __getWidgetXY(widget, parent, relx=None, rely=None,
                  w_width=None, w_height=None):
    if w_width is None:
        w_width = widget.winfo_reqwidth()
    if w_height is None:
        w_height = widget.winfo_reqheight()
    s_width = widget.winfo_screenwidth()
    s_height = widget.winfo_screenheight()
    m_x = m_y = 0
    m_width, m_height = s_width, s_height
    if parent and parent.winfo_ismapped():
        ##print parent.wm_geometry()
        ##print parent.winfo_geometry(), parent.winfo_x(), parent.winfo_y(), parent.winfo_rootx(), parent.winfo_rooty(), parent.winfo_vrootx(), parent.winfo_vrooty()
        m_x = m_y = None
        if os.name == "nt":
            try:
                m_width, m_height, m_x, m_y = wm_get_geometry(parent)
            except:
                pass
        if m_x is None:
            m_x = parent.winfo_x()
            m_y = parent.winfo_y()
            m_width = parent.winfo_width()
            m_height = parent.winfo_height()
            if relx is None: relx = 0.5
            if rely is None: rely = 0.3
        else:
            if relx is None: relx = 0.5
            if rely is None: rely = 0.5
        m_x = max(m_x, 0)
        m_y = max(m_y, 0)
    else:
        if relx is None: relx = 0.5
        if rely is None: rely = 0.3
    x = m_x + int((m_width - w_width) * relx)
    y = m_y + int((m_height - w_height) * rely)
    ##print x, y, w_width, w_height, m_x, m_y, m_width, m_height
    # make sure the widget is fully on screen
    if x < 0: x = 0
    elif x + w_width + 32 > s_width: x = max(0, (s_width - w_width) / 2)
    if y < 0: y = 0
    elif y + w_height + 32 > s_height: y = max(0, (s_height - w_height) / 2)
    return x, y


# /***********************************************************************
# // bind wrapper - Tkinter doesn't properly delete all bindings
# ************************************************************************/

__mfx_bindings = {}
__mfx_wm_protocols = ("WM_DELETE_WINDOW", "WM_TAKE_FOCUS", "WM_SAVE_YOURSELF")

def bind(widget, sequence, func, add=None):
    assert callable(func)
    if sequence in __mfx_wm_protocols:
        funcid = widget._register(func)
        widget.tk.call("wm", "protocol", widget._w, sequence, funcid)
    elif add is None:
        funcid = widget.bind(sequence, func)
    else:
        ##add = add and "+" or ""
        funcid = widget.bind(sequence, func, add)
    k = id(widget)
    if __mfx_bindings.has_key(k):
        __mfx_bindings[k].append((sequence, funcid))
    else:
        __mfx_bindings[k] = [(sequence, funcid)]

def unbind_destroy(widget):
    if widget is None:
        return
    k = id(widget)
    if __mfx_bindings.has_key(k):
        for sequence, funcid in __mfx_bindings[k]:
            ##print widget, sequence, funcid
            try:
                if sequence in __mfx_wm_protocols:
                    widget.tk.call("wm", "protocol", widget._w, sequence, "")
                    ##widget.deletecommand(funcid)
                else:
                    widget.unbind(sequence, funcid)
            except Tkinter.TclError:
                pass
        del __mfx_bindings[k]
    ##for k in __mfx_bindings.keys(): print __mfx_bindings[k]
    ##print len(__mfx_bindings.keys())


# /***********************************************************************
# // timer wrapper - Tkinter doesn't properly delete all commands
# ************************************************************************/

def after(widget, ms, func, *args):
    timer = apply(widget.after, (ms, func) + args)
    command = widget._tclCommands[-1]
    return (timer, command, widget)

def after_idle(widget, func, *args):
    return apply(after, (widget, "idle", func) + args)

def after_cancel(t):
    if t is not None:
        t[2].after_cancel(t[0])
        try:
            t[2].deletecommand(t[1])
        except Tkinter.TclError:
            pass


# /***********************************************************************
# // image handling
# ************************************************************************/

def makeImage(file=None, data=None, dither=None, alpha=None):
    kw = {}
    if data is None:
        assert file is not None
        kw["file"] = file
    else:
        assert data is not None
        kw["data"] = data
    if os.name == "nt":
        # Commented out by RS to resolve "unknown option -dither" error.
        #if dither is not None:
        #    kw["dither"] = dither
        if alpha is not None:
            kw["alpha"] = alpha
    return apply(Tkinter.PhotoImage, (), kw)

loadImage = makeImage

def copyImage(image, x, y, width, height):
    dest = Tkinter.PhotoImage(width=width, height=height)
    assert dest.width() == width
    assert dest.height() == height
    dest.blank()
    image.tk.call(dest, "copy", image.name, "-from", x, y, x+width, y+height)
    assert dest.width() == width
    assert dest.height() == height
    return dest

def fillImage(image, fill, outline=None):
    if not fill and not outline:
        return
    width = image.width()
    height = image.height()
    ow = 1                              # outline width
    if width <= 2*ow or height <= 2*ow:
        fill = fill or outline
        outline = None
    if not outline:
        f = (fill,) * width
        f = (f,) * height
        assert len(f) == height
        image.put(f)
    elif not fill:
        l = ((outline,) * width,)
        for y in range(0, ow):
            image.put(l, (0, y))
        for y in range(height-ow, height):
            image.put(l, (0, y))
        p = ((outline,) * ow,)
        for y in range(ow, height-ow):
            image.put(p, (0, y))
            image.put(p, (width-ow, y))
    else:
        l1 = (outline,) * width
        l2 = (outline,) * ow + (fill,) * (width-2*ow) + (outline,) * ow
        f = (l1,) * ow + (l2,) * (height-2*ow) + (l1,) * ow
        assert len(f) == height
        image.put(f)

def createImage(width, height, fill, outline=None):
    image = Tkinter.PhotoImage(width=width, height=height)
    assert image.width() == width
    assert image.height() == height
    image.blank()
    fillImage(image, fill, outline)
    return image

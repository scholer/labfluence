# if a directory's __init__.py is empty, then all modules can be referenced. 
# However, if a directory's __init__.py is empty, then modules must be imported as : 
#     from views import expnotebook.ExpNotebook
# in other words, "from views import *" will not work.

# If you want to be able to "import *", then the directory's __init__.py must explicitly denote the modules,
# either as one of:
#    from expnotebook import ExpNotebook
#    import ExpNotebook
# or using
# __all__ = ["expnotebook", ...]
# to automatically load all modules _and_ be able to use "import *" requires some loading logic:
# __all__ = [ os.path.basename(f)[:-3] for f in glob.glob(os.path.dirname(__file__)+"/*.py")]
# c.f.:
# http://docs.python.org/tutorial/modules.html
# http://stackoverflow.com/questions/1057431/loading-all-modules-in-a-folder-in-python
# http://stackoverflow.com/questions/1944569/how-do-i-write-good-correct-init-py-files

# if you have any import statements (i.e. if the __init__.py is not empty)
# then all the modules that you want to reference in this directory must be stated.
# from expnotebook import *
# or:
# from expnotebook import ExpNotebook
# or: (these are then referenced as expnotebook.ExpNotebook and not directly with ExpNotebook)
# import expnotebook
# or, to only load the ExpNotebook class and not other stuff from expnotebook:
# import expnotebook.ExpNotebook
"""
A note on controllers:

The idea with controllers is that they can help encapsulate the connections between a widget and
a) The model domain.
b) Other widgets.

This allows the developer to focus on the layout of the widget in the widget code (in many cases without even subclassing it).
In these cases, all that is needed for the widget to work is to hook a (often generic) widget up to a controller.

This was the case with e.g. the listbox controllers in the first GUI version.

Another way to yield a specialized widget is of cause to subclass it.
This is how the ActiveExpsListbox and colleagues work.
However, in this case, the derived listbox'es mostly interact with the model domain
and only indirectly with other widgets via callbacks registrered with the confighandler.

So, what about the case where a widget needs to affect other widgets?
In particular, other widgets that are not child widgets and whose position is really unknown?
One option is to call the widget's parent/master. However, if the parent is just a dumb frame, 
and the interacting widget is distant in the widget hierarchy, child-parent-grandparent-parent-child-other-widget 
communication paths are not worth the trouble.
Of cause, the child should of cause also not need to know too much about the tree hierarchy.

One way would be to route all calls via the app/tkroot.
This is easy, since 'app' is usually registrered and easily accessible.
That is how I implemented the listboxcontrollers, calling e.g. 
    app = self._app or self.Confighandler.Singletons.get('app')
    app.show_notebook()
However, that would leave a lot of logic routed through the app object.
(althrough, since the tkroot and mainframe takes care of most UI-specific stuff, that might not
be as bad as it sounds!)

Another solution could be to have the logic in the nearest common ancestor (NCA).
For the active-experiments-list and the rightframe, this would be the mainframe widget.

A third solution is to do 'light-weight' binding of two widgets.
In this case, the nearest common ancestor can bind e.g.
listbox.on_select = other_widget.some_method
But then, what when other_widget is destroyed? Then you would need to implement a
proper register+unregister call system, but that over-complicates things.

I guess actually I could simply rely on the callback system implemented in the model domain:
selecting an entry in ActiveExpsListbox could trigger:
    self.Experimentmanager.Current_experiment = self.selection_ ...
    self.Confighandler.invokeEntryChangeCallback('app_current_expid')
and then the rightframe (or whatever) could subscribe to 'app_current_expid' changes.

In any case, I think it is a bit messy to have a widget interact *on* another widget
without being specifically told, i.e. hard-coding interactions with other widgets
*in the class definition* seems messy.
This might be ok if a) you are using a controller to encapsulate that logic, 
or b) you are routing calls through the 'app' singleton.
Note that I think it is ok to hard-code interactions with the *model domain*
directly in the widget class definition.

So, in conclusion, how does this relate to e.g. ActiveExpsListbox?
a) You implement the interactions in the mainframe (NCA) using bind.
b) You implement via announcements/subscriptions to 'app_current_expid' configentry.
c) You implement with controllers that interact with the app singleton.

Regarding a) using bind in the mainframe (NCA):
    self.activeexps_list.bind('<<selection>>', self.activeexp_selected)
    requires you to investigate the list selection, which again requires you to have
    rather intimate knowledge on the listbox internals (or, well, maybe you can just 
    use the index and hope that it is up-to-date). I think, however, that I prefer
    to use a controller.

Regarding b) using announcements/subscriptions to 'app_current_expid' configentry:
    You could make either a specific "SelectCurrentExpListbox", which is derived from
    ActiveExpsListbox, but updates 'app_current_expid' when selected
    In practice, the listbox should call self.Experimentmanager.set_current_expid(expid)
    and ExperimentManager.set_current_expid should then update 'app_current_expid'
    and invokes self.Confighandler.invokeEntryChangeCallback('app_current_expid').
    The subscriber could then be the mainframe (or the app), which has 
    This would have the added benefit of indirectly persisting the UI state in many cases,
    (i.e. cases where the UI state really relates on the last state of the model domain.)

    Of cause, the problem might be that you risk smudging UI related things in the model domain,
    particularly the confighandler. But who cares, as long as it is just a setting/config entry
    and not something hard-coded in the model that should have been in the UI.

Regarding c) controllers that interact with the app singleton.
    Well, I know this works and I know that it is nice. 

"""
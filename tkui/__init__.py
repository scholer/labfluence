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
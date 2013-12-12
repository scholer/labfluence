"""
Add this hook to your hgrc to display information about the
python interpreter used by hg.
"""


def hgpyinfo(*args, **kwargs):

    # For some reason, imports are not invoked if this is outside main...
    print "hg python interpreter info:"
    import sys, os
    # Note: the hg python version might be so old that zero-length field names are not supported...
    print "- sys.version: {0}".format(sys.version)
    print "- sys.version_info: {0}".format(sys.version_info)
    print "- sys.executable: {0}".format(sys.executable)
    print "- sys.path: {0}".format(sys.path)
    print "- sys.argv: {0}".format(sys.argv)
    print "- os.getcwd(): {0}".format(os.getcwd())


if __name__ == '__main__':
    #main()
    print "well, this was invoked..."

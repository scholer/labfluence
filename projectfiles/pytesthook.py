"""
Notice: Requires you to install pytest in the mercurial
"""


def rspytest(*args, **kwargs):

    # For some reason, imports are not invoked if this is outside main...
    try:
        import pytest
        pytest_available = True
    except ImportError:
        pytest_available = False
        print "pytest not available!!"
        print "python info:"
        import sys, os
        # Note: the hg python version might be so old that zero-length field names are not supported...
        print "sys.version: {0}".format(sys.version)
        print "sys.version_info: {0}".format(sys.version_info)
        print "sys.executable: {0}".format(sys.executable)
        print "sys.path: {0}".format(sys.path)
        print "sys.argv: {0}".format(sys.argv)
        print "os.getcwd(): {0}".format(os.getcwd())
        return 1

    if args:
        print "args are: %s" % args
    if kwargs:
        print "kwargs are: %s" % kwargs

    print "invoking pytest.main()"
    res = pytest.main()
    print "pytest result: '%s'" % res
    # if all tests succeeed: res == 0
    # if any test fails: res == 1
    return res

if __name__ == '__main__':
    #main()
    print "well, this was invoked..."

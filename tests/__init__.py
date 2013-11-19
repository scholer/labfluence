#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2013 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
"""
Litt:
* http://docs.python-guide.org/en/latest/writing/tests/
* http://pytest.org/latest/getting-started.html
* http://docs.python.org/2/library/unittest.html


The project includes the following test suites / types:
unittests:    Unittests are the most thorough.
pytests:      For faster test writing.
rstests:      My own custom tests. Mostly includes legacy code. Should be converted to py.test code.

Important note:
- py.test can run unittest code!
- Nose runs unittests, but the API is so similar to py.test that some py.test can be run with nose.
- Note: You do not need to invent test cases for every imaginable case and parameter combination.
        Write tests to see if your code works as expected when coding, and write more tests when
        debugging. If tests becomes obsolete, do not be afraid to eliminate them from the main test runs.

-----------------------
-- Unittest testing ---
-----------------------

Unittests are the most thorough of the tests in this project.
Unit tests are written as test suits composed of individual test cases.
Each test case should test only one small functional part.
Unit test cases should derive from unittest.TestCase.
Legacy code can derive from unittest.FunctionTestCase,
which only implements a subset of the TestCase functionality.

unittest.TestSuite can be used to group individual tests cases.

Unittest provides the following test methods:
    assertEqual(a, b), assertNotEqual(a, b), assertTrue(x), assertFalse(x)

    assertIs(a, b), assertIsNot(a, b), assertIsNone(x), assertIsNotNone(x),
    assertIn(a, b), assertNotIn(a, b), assertIsInstance(a, b), assertNotIsInstance(a, b).

    assertRaises(exc, fun, *args, **kwds), assertRaisesRegexp(exc, r, fun, *args, **kwds).

    assertAlmostEqual(a, b), assertNotAlmostEqual(a, b), assertGreater(a, b), assertGreaterEqual(a, b)
    assertLess(a, b), assertLessEqual(a, b), assertRegexpMatches(s, r), assertNotRegexpMatches(s, r),
    assertItemsEqual(a, b),
Deprechated:
    assertDictContainsSubset(a, b)  (since 3.2)

Example assertion tests:
    self.assertEqual(self.seq, range(10))
    self.assertTrue(element in self.seq)
    self.assertRaises(TypeError, random.shuffle, (1,2,3))


-----------------------
-- py.test testing  ---
-----------------------
Run py.test with either of the following:
: python -m pytest test_um_pytest.py
: py.test test_um_pytest.py
Commandline args:
- v : verbose


py.test tests are used for rapid test writing.
py.test can automatically find tests in the project hierarchy:
- files should be named test_something.py
- functions should be named test_something()
to test, use:
    assert some_function(args) == <expected return value>
to test for exceptions:
    with pytest.raises(SystemExit):
        f()
tests can be grouped in test classes, like UnitTests:
class TestClass:
    def test_one(self):
        x = "this"
        assert 'h' in x


py.test refs:
* http://pytest.org/latest/
* http://pytest.org/latest/talks.html
* http://pythontesting.net/framework/pytest/pytest-introduction/


-------------------------
-- Other tests tools  ---
-------------------------

Other test tools include:
- Doctest   Write tests in method docstrings.
- Nose      Makes it easier to do use unittest by making it more like py.test
- tox       Makes it easiert to test different interpreters.
- mock      For making 'mock' classes, http://www.voidspace.org.uk/python/mock/
- Pylint    For automatic advanced source code checking, http://www.logilab.org/857




More litterature:
* http://pythontesting.net/start-here/
* http://pythontesting.net/framework/unittest/unittest-introduction/
* http://pythontesting.net/framework/specify-test-unittest-nosetests-pytest/
* http://stackoverflow.com/questions/3371255/writing-unit-tests-in-python-how-do-i-start
* http://openp2p.com/pub/a/python/2004/12/02/tdd_pyunit.html   -- on UnitTest, a bit old.
* http://onlamp.com/pub/a/python/2005/02/03/tdd_pyunit2.html
* http://diveintopython.net/unit_testing/index.html
* http://cgoldberg.github.io/python-unittest-tutorial/     - UnitTest
"""

#__all__ = ['model_tests']
#import model_tests
#from .. import model, views, ui, controllers, labfluence_gui

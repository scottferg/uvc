import os
from cStringIO import StringIO

from uvc.path import path
from uvc import commands, svn, main, exc
from uvc.tests.util import test_context
from uvc.tests.mock import patch

StatusOutput = commands.StatusOutput

dialect = svn.SVNDialect()

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", 
                        "testfiles"))

context = None

def setup_module(module):
    global context
    if not os.path.exists(topdir):
        os.mkdir(topdir)
    context = main.Context(topdir)
    
def test_clone_command_conversion():
    generic_clone = commands.clone(context, ["http://paver.googlecode.com/svn/trunk/", 
                                    "paver"])
    svn_clone = svn.clone(generic_clone)
    svn_clone_command = " ".join(svn_clone.get_command_line())
    assert svn_clone_command == "svn checkout http://paver.googlecode.com/svn/trunk/ paver"

def test_convert_function():
    generic_clone = commands.clone(context, ["http://paver.googlecode.com/svn/trunk/", 
                                    "paver"])
    svn_clone = dialect.convert(generic_clone)
    svn_clone_command = " ".join(svn_clone.get_command_line())
    assert svn_clone_command == "svn checkout http://paver.googlecode.com/svn/trunk/ paver"
    
def test_convert_unknown_command():
    class Foo(object):
        pass
    
    try:
        result = dialect.convert(Foo())
        assert False, "expected SVNError for unknown command"
    except svn.SVNError:
        pass

def test_commit_command():
    generic_commit = commands.commit(test_context, 
                ["-m", "test message", "foo", "bar"])
    result = dialect.convert(generic_commit)
    assert str(result) == "commit -m test message foo bar"
    
def test_diff_command():
    generic_diff = commands.diff(context, [])
    result = dialect.convert(generic_diff)
    assert str(result) == "diff"
    
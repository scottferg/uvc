import os
from cStringIO import StringIO

from uvc.path import path
from uvc import commands, svn, main, exc, util
from uvc.tests.util import test_context
from uvc.tests.mock import patch

StatusOutput = commands.StatusOutput

dialect = svn.SVNDialect()

topdir = path(__file__).dirname().abspath() / ".." / ".." / "testfiles"

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
    commit_file = path(test_context.working_dir) / ".svn_commit_messages"
    if commit_file.exists():
        commit_file.unlink()
    
    generic_commit = commands.commit(test_context, 
                ["-m", "test message", "foo", "bar"])
    result = dialect.convert(generic_commit)
    assert result.get_command_line() == None
    assert str(result.get_output()) == "Commit message saved. Don't forget to push to save to the remote repository!"
    
    assert commit_file.exists(), "Expected commit file at " + commit_file
    assert commit_file.text() == "test message\n\n"
    
def test_push_command_before_commit():
    commit_file = path(test_context.working_dir) / ".svn_commit_messages"
    if commit_file.exists():
        commit_file.unlink()
    
    generic_push = commands.push(test_context, [])
    result = dialect.convert(generic_push)
    assert result.get_command_line() == None
    assert str(result.get_output()) == "Nothing to push. Run commit first."
    
def test_push_after_commit():
    commit_file = path(test_context.working_dir) / ".svn_commit_messages"
    if commit_file.exists():
        commit_file.unlink()
    
    generic_commit = commands.commit(test_context, 
                ["-m", "test message1", "foo", "bar"])
    result = dialect.convert(generic_commit)
    result.get_output()
    
    generic_commit = commands.commit(test_context, 
                ["-m", "test message2", "foo", "bar"])
    result = dialect.convert(generic_commit)
    result.get_output()
    
    generic_push = commands.push(test_context, [])
    result = dialect.convert(generic_push)
    assert result.get_command_line() == ["svn", "commit", "-m", 
        "test message1\n\ntest message2\n\n"]
    
def test_diff_command():
    generic_diff = commands.diff(context, [])
    result = dialect.convert(generic_diff)
    assert str(result) == "diff"
    
@patch("uvc.util.run_in_directory")
def test_add_all_files(rid):
    generic_add = commands.add(test_context, [])
    result = dialect.convert(generic_add)
    stdout = StringIO("""A      foo.txt
?      bar.txt
A      baz.txt
""")
    rid.return_value = [0, stdout]
    assert result.get_command_line() == ["svn", "add", "bar.txt"]
    assert rid.called
    
def test_revert_all_files():
    testfile = topdir / "foo.txt"
    testfile.write_text("Test text")
    try:
        generic_revert = commands.revert(context, [])
        result = dialect.convert(generic_revert)
        assert result.get_command_line() == ["svn", "revert", "-R", "foo.txt"]
    finally:
        testfile.unlink()
    
@patch("uvc.util.run_in_directory")
def test_resolve_all_files(rid):
    stdout = StringIO("""A      foo.txt
C      bar.txt
A      baz.txt
""")
    rid.return_value = [0, stdout]
    generic_resolved = commands.resolved(context, [])
    result = dialect.convert(generic_resolved)
    assert result.get_command_line() == ["svn", "resolve", 
        "--accept", "working", "bar.txt"]
    assert rid.called
    
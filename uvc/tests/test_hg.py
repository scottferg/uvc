import os
from cStringIO import StringIO

from uvc.path import path
from uvc import commands, hg, main, exc
from uvc.tests.util import test_context
from uvc.tests.mock import patch

StatusOutput = commands.StatusOutput

dialect = hg.HgDialect()

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", 
                        "testfiles"))

context = None

def setup_module(module):
    global context
    if not os.path.exists(topdir):
        os.mkdir(topdir)
    context = main.Context(topdir)

def test_clone_command_conversion():
    generic_clone = commands.clone(context, ["http://hg.mozilla.org/labs/bespin", 
                                    "bespin"])
    hg_clone = hg.clone(generic_clone)
    assert str(hg_clone) == "clone http://hg.mozilla.org/labs/bespin bespin"
    
def test_convert_function():
    generic_clone = commands.clone(context, ["http://hg.mozilla.org/labs/bespin", 
                                    "bespin"])
    result = dialect.convert(generic_clone)
    assert str(result) == "clone http://hg.mozilla.org/labs/bespin bespin"
    
def test_convert_unknown_command():
    class Foo(object):
        pass
    
    try:
        result = dialect.convert(Foo())
        assert False, "expected HgError for unknown command"
    except hg.HgError:
        pass

def test_commit_command():
    test_context.user = "Zaphod Beeblebrox <zaphod@onecooldude.us>"
    generic_commit = commands.commit(test_context, ["-m", "test message", "foo", "bar"])
    result = dialect.convert(generic_commit)
    assert not result.reads_remote
    assert not result.writes_remote
    command_parts = result.command_parts()
    assert command_parts == ["commit", "-u", "Zaphod Beeblebrox <zaphod@onecooldude.us>",
                            "-m", "test message", "foo", "bar"]
    
def test_diff_command():
    generic_diff = commands.diff(context, [])
    result = dialect.convert(generic_diff)
    assert not result.reads_remote
    assert not result.writes_remote
    assert str(result) == "diff"
    
def test_clone_command_simple_ssh_auth():
    context = main.Context(topdir, auth=dict(type="ssh", key="/tmp/id.rsa"))
    generic_clone = commands.clone(context, ["ssh://hg.mozilla.org/bar"])
    result = dialect.convert(generic_clone)
    assert result.reads_remote
    assert not result.writes_remote
    assert str(result) == "clone -e ssh -i /tmp/id.rsa -o StrictHostKeyChecking=no ssh://hg.mozilla.org/bar bar"
    
def test_clone_command_ssh_username_auth():
    context = main.Context(topdir, auth=dict(type="ssh", key="/tmp/id.rsa", 
                                username="someone_else"))
    generic_clone = commands.clone(context, ["ssh://hg.mozilla.org/bar"])
    result = dialect.convert(generic_clone)
    assert str(result) == "clone -e ssh -i /tmp/id.rsa -o StrictHostKeyChecking=no ssh://someone_else@hg.mozilla.org/bar bar"
    
def test_clone_command_http_password_auth():
    context = main.Context(topdir, auth=dict(type="password", 
                        username="supercooluser", password="hithere"))
    generic_clone = commands.clone(context, ["http://hg.mozilla.org/bar"])
    result = dialect.convert(generic_clone)
    assert str(result) == "clone http://supercooluser:hithere@hg.mozilla.org/bar bar"
    
def test_push_command_ssh_username_auth():
    context = main.Context(topdir, auth=dict(type="ssh", key="/tmp/id.rsa", 
                                username="someone_else"))
    generic_push = commands.push(context, ["ssh://hg.mozilla.org/bar"])
    result = dialect.convert(generic_push)
    assert result.writes_remote
    assert result.reads_remote
    assert str(result) == "push -e ssh -i /tmp/id.rsa -o StrictHostKeyChecking=no ssh://someone_else@hg.mozilla.org/bar"

def test_update_command():
    generic_update = commands.update(context, [])
    update = hg.update(generic_update)
    assert update.reads_remote
    assert not update.writes_remote
    assert update.get_command_line() == ["hg", "fetch"]
    
def test_resolved_command():
    myfile = path(topdir) / "myfile"
    myfile.write_bytes("test data")
    try:
        generic_resolved = commands.resolved(context, ["myfile"])
        resolved = hg.resolved(generic_resolved)
    finally:
        myfile.unlink()
        
    assert not resolved.reads_remote
    assert not resolved.writes_remote
    assert resolved.get_command_line() == ["hg", "resolve", "-m", "myfile"]
    
def test_resolved_command_no_targets():
    myfile = path(topdir) / "myfile"
    myfile.write_bytes("test data")
    try:
        generic_resolved = commands.resolved(context, [])
        resolved = hg.resolved(generic_resolved)
    finally:
        myfile.unlink()
        
    assert not resolved.reads_remote
    assert not resolved.writes_remote
    assert resolved.get_command_line() == ["hg", "resolve", "-m", "-a"]
    
def test_remove_command_no_targets():
    myfile = path(topdir) / "myfile"
    myfile.write_bytes("test data")
    try:
        generic_remove = commands.remove(context, ["myfile"])
        remove = hg.remove(generic_remove)
    finally:
        myfile.unlink()
        
    assert not remove.reads_remote
    assert not remove.writes_remote
    assert remove.get_command_line() == ["hg", "remove", "-f", "myfile"]
    
def test_status_command():
    generic_status = commands.status(context, [])
    status = hg.status(generic_status)
    assert not status.writes_remote
    assert not status.reads_remote
    
    assert status.get_command_line() == ["hg", "status"]
    
    status_output = """M modified/file
A new/file
R removed/file
C clean/file
! missing/file
? unknown/file
I ignored/file
"""
    
    output = status.process_output(0, StringIO(status_output))
    the_list = output.as_list()
    print the_list
    assert the_list == [
[StatusOutput.MODIFIED, "modified/file"],
[StatusOutput.ADDED, "new/file"],
[StatusOutput.REMOVED, "removed/file"],
[StatusOutput.CLEAN, "clean/file"],
[StatusOutput.MISSING, "missing/file"],
[StatusOutput.UNKNOWN, "unknown/file"],
[StatusOutput.IGNORED, "ignored/file"]
]
    assert str(output) == status_output
    
@patch("uvc.main.infer_dialect")
def test_init_command(infer_dialect):
    infer_dialect.return_value = None
    init = hg.init.from_args(test_context, [])
    assert init.command_parts() == ["init"]
    assert init.get_command_line() == ["hg", "init"]
    
@patch('uvc.main.infer_dialect')
def test_init_command_in_existing_repo(infer_dialect):
    infer_dialect.return_value = dialect
    
    try:
        init = hg.init.from_args(test_context, [])
        assert False, "Should have gotten an exception about existing repo"
    except exc.RepositoryAlreadyInitialized:
        pass
    
def test_revert_command():
    myfile = path(topdir) / "myfile"
    myfile.write_bytes("test data")
    try:
        generic_revert = commands.revert(context, [])
        revert = hg.revert(generic_revert)
    finally:
        myfile.unlink()
        
    assert not revert.reads_remote
    assert not revert.writes_remote
    assert revert.get_command_line() == ["hg", "revert", "--no-backup", "-a"]
    
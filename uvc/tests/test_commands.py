
from uvc.path import path
from uvc import commands
from uvc.tests.util import test_context
from uvc.main import Context, SecureContext
from uvc.exc import UVCError

topdir = (path(__file__).parent.parent.parent) / "testfiles"

context = None
secure_context = None

def setup_module(module):
    global context, secure_context
    if not topdir.exists:
        topdir.mkdir()
    context = Context(topdir)
    secure_context = SecureContext(topdir)
    
def test_create_clone_command():
    clone = commands.clone(context, ["http://hg.mozilla.org/labs/bespin", 
                                    "bespin"])
    assert clone.reads_remote
    assert not clone.writes_remote
    assert clone.source == "http://hg.mozilla.org/labs/bespin"
    assert clone.dest == "bespin"
    assert str(clone) == "clone http://hg.mozilla.org/labs/bespin bespin"
    
def test_bad_clone_command():
    try:
        clone = commands.clone(context, [])
        assert False, "Expected BadArgument exception for missing args."
    except commands.BadArgument:
        pass
    
def test_commit_command():
    commit = commands.commit(test_context, 
            ["-m", "my commit message", "bespin", "uvc"])
    assert not commit.reads_remote
    assert not commit.writes_remote
    message = commit.message
    assert message == "my commit message"
    assert commit.targets == ["bespin", "uvc"]
    assert str(commit) == "commit -m my commit message bespin uvc"
    
    try:
        commit = commands.commit(test_context, ["foo"])
        assert False, "Expected prompting for value"
    except commands.GetValueFromEditor,e :
        assert e.template_args == ["commit", '-m', commands.inserted_value, "foo"]
        assert e.prompt == "Please enter a commit message"
    
def test_diff_command():
    diff = commands.diff(test_context, ["myfile"])
    assert not diff.reads_remote
    assert not diff.writes_remote
    assert diff.targets == ["myfile"]
    assert str(diff) == "diff myfile"
    
    diff = commands.diff(test_context, [])
    assert diff.targets == None
    assert str(diff) == "diff"
    
def test_status_command():
    status = commands.status(test_context, [])
    assert not status.reads_remote
    assert not status.writes_remote
    assert str(status) == "status"
    
    status = commands.status(test_context, ["mydir"])
    assert str(status) == "status mydir"

def test_remove_command():
    remove = commands.remove(test_context, ["myfile"])
    assert not remove.reads_remote
    assert not remove.writes_remote
    assert remove.targets == ["myfile"]
    assert str(remove) == "remove myfile"
    
    try:
        remove = commands.remove(test_context, [])
        assert False, "Expected an error for remove without a file"
    except UVCError:
        pass

def test_revert_command():
    revert = commands.revert(test_context, ["myfile"])
    assert not revert.reads_remote
    assert not revert.writes_remote
    assert revert.targets == ["myfile"]
    assert str(revert) == "revert myfile"
    
    revert = commands.revert(test_context, [])
    assert revert.targets == None
    assert str(revert) == "revert"


def test_push_command():
    push = commands.push(test_context, [])
    assert push.reads_remote
    assert push.writes_remote
    assert str(push) == "push"
    
def test_update_command():
    update = commands.update(test_context, [])
    assert update.reads_remote
    assert not update.writes_remote
    assert str(update) == "update"

def test_update_command_with_url():
    update = commands.update(test_context, ["http://hg.mozilla.org/labs/bespin"])
    assert update.source == "http://hg.mozilla.org/labs/bespin"
    assert str(update) == "update http://hg.mozilla.org/labs/bespin"

def test_resolved_command():
    resolved = commands.resolved(test_context, ["myfile"])
    assert not resolved.reads_remote
    assert not resolved.writes_remote
    assert resolved.targets == ["myfile"]
    assert str(resolved) == "resolved myfile"
    
def test_add_command():
    add = commands.add(test_context, [])
    assert str(add) == "add"
    
def test_basic_dir_validation():
    newdir = topdir / "newdir"
    if newdir.exists():
        newdir.rmtree()
    
    try:
        newval = context.validate_existing_directory(newdir)
        assert False, "Expected exception for directory that does not exist"
    except commands.FileError:
        pass
    
    # no exception means we're fine.
    newval = context.validate_new_directory(newdir)
    assert newval == newdir
    
    newdir.mkdir()
    
    try:
        newval = context.validate_new_directory(newdir)
        assert False, "Expected exception for existing directory"
    except commands.FileError:
        pass
    
    newval = context.validate_existing_directory(newdir)
    assert newval == newdir
    
def test_basic_file_validation():
    newdir = topdir / "newdir"
    newfile = newdir / "testfile.txt"
    if newfile.exists():
        newfile.unlink()
        
    if not newdir.exists():
        newdir.mkdir()
    
    try:
        newval = context.validate_existing_file(newfile)
        assert False, "Expected exception for file that does not exist"
    except commands.FileError:
        pass
        
    try:
        newval = context.validate_exists(newfile)
        assert False, "Expected exception for file that does not exist"
    except commands.FileError:
        pass
    
    # no exception means we're fine.
    newval = context.validate_new_file(newfile)
    assert newval == newfile
    
    newfile.write_bytes("Hi\n")
    
    try:
        newval = context.validate_new_file(newfile)
        assert False, "Expected exception for existing file"
    except commands.FileError:
        pass
    
    newval = context.validate_existing_file(newfile)
    assert newval == newfile
    newdir.rmtree()
    
def test_clone_command_checks_for_existence():
    bespin_dir = topdir / "bespin"
    if bespin_dir.exists():
        bespin_dir.rmdir()
        
    # should work when the dest directory is not there.
    clone = commands.clone(context, ["http://hg.mozilla.org/labs/bespin"])
    dest = clone.dest
    assert dest == "bespin"
    
    bespin_dir.mkdir()
    try:
        clone = commands.clone(context, ["http://hg.mozilla.org/labs/bespin"])
        assert False, "Expected FileError for existing dest directory"
    except commands.FileError:
        pass
    
    bespin_dir.rmdir()
    
def test_secure_context_keeps_user_in_working_dir():
    newdir = topdir / ".." / "newdir"
    newfile = topdir / ".." / "newfile.txt"
    assert not newdir.exists()
    assert not newfile.exists()
    
    existdir = topdir / ".."
    existfile = topdir / ".." / "setup.py"
    assert existdir.exists()
    assert existfile.exists()
        
    context = SecureContext(topdir)
    try:
        context.validate_new_directory(newdir)
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
    
    try:
        context.validate_new_file(newfile)
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
    
    try:
        context.validate_existing_directory(existdir)
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
    
    try:
        context.validate_existing_file(existfile)
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
    
    try:
        context.validate_exists(existfile)
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass

def test_clone_is_secured():
    try:
        clone = commands.clone(secure_context, 
            ["http://hg.mozilla.org/labs/bespin", topdir / ".." / "foo"])
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
    
def test_commit_is_secured():
    try:
        commit = commands.commit(secure_context, 
            ["-m", "commit message", topdir / ".." / "foo"])
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
    
def test_diff_is_secured():
    try:
        diff = commands.diff(secure_context, [topdir / ".." / "foo"])
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass

def test_revert_is_secured():
    try:
        revert = commands.revert(secure_context, [topdir / ".." / "foo"])
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
        
def test_status_is_secured():
    try:
        status = commands.status(secure_context, [topdir / ".." / "foo"])
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass
        
def test_remove_is_secured():
    try:
        remove = commands.remove(secure_context, [topdir / ".." / "foo"])
        assert False, "Expected exception for going above topdir"
    except commands.SecurityError:
        pass

def test_push_is_secured():
    try:
        push = commands.push(secure_context, [topdir / ".." / "foo"])
        assert False, "Expected security error for trying to push elsewhere"
    except commands.SecurityError:
        pass
    
    try:
        push = commands.push(secure_context, ["file:///etc/passwd"])
        assert False, "Expected security error for trying to push elsewhere"
    except commands.SecurityError:
        pass
    
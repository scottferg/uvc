"""Implements the uvc command processing."""

import sys
import os
import subprocess
import tempfile
import logging

from uvc import commands, hg, svn
from uvc.util import run_in_directory
from uvc.path import path
from uvc.exc import *

log = logging.getLogger("uvc.main")

dialects = dict(hg=hg.HgDialect(), svn=svn.SVNDialect())

class Context(object):
    # all schemes are allowed
    remote_scheme_whitelist = None
    
    # a user can be set, because some DVCS operations
    # want a user to flag the commits, etc.
    user = None
    
    def __init__(self, working_dir, auth=None):
        """working_dir is the working directory in which commands should
        run. auth is a dictionary of authentication information:
        
        * type: 'ssh' or 'password'
        * key: for SSH, this should be the path to the user's private key
        * username: for SSH or password auth, this is the username to use
        * password: for password auth, this is the password to use"""
        self.working_dir = path(working_dir)
        self.auth = auth
        
    def _normalize_path(self, unnorm_path):
        norm_path = self.working_dir / path(unnorm_path)
        norm_path = norm_path.normpath()
        norm_path = norm_path.realpath()
        norm_path = norm_path.abspath()
        return norm_path
    
    def validate_new_directory(self, newdir):
        """Confirms that newdir does not exist, raising a 
        FileError otherwise."""
        newdir = self._normalize_path(newdir)
        if newdir.exists():
            if newdir.isdir():
                raise FileError("Directory %s already exists" % newdir)
            else:
                raise FileError("Cannot create %s, path exists" % newdir)
        return newdir
    
    def validate_existing_directory(self, existingdir):
        """Confirms that existingdir does exist, raising a FileError
        otherwise."""
        existingdir = self._normalize_path(existingdir)
        if not existingdir.isdir():
            raise FileError("Directory %s does not exist" % existingdir)
        return existingdir
        
    def validate_new_file(self, newfile):
        """Confirms that newfile does not exist, raising a
        FileError otherwise."""
        newfile = self._normalize_path(newfile)
        if newfile.isfile():
            raise FileError("File %s already exists" % newfile)
        return newfile
        
    def validate_existing_file(self, existingfile):
        """Confirms that existingfile exists, raising a FileError
        otherwise."""
        existingfile = self._normalize_path(existingfile)
        if not existingfile.isfile():
            raise FileError("File %s does not exist" % existingfile)
        return existingfile
        
    def validate_exists(self, existing):
        """Confirms that existing is a directory or
        file, raising a FileError otherwise."""
        existing = self._normalize_path(existing)
        if not existing.exists():
            raise FileError("File or directory %s does not exist" % (existing))
        return existing
    
class SecureContext(Context):
    # this is not the ideal place for this
    remote_scheme_whitelist = set(["http", "https", "ssh", "svn", "git", "bzr",
                                "svn+ssh"])
    
    def _normalize_path(self, unnorm_path):
        """Ensures that the path provided is underneath
        this context's working directory."""
        norm_path = super(SecureContext, self)._normalize_path(unnorm_path)
        rel_path = self.working_dir.relpathto(norm_path)
        if rel_path.isabs() or rel_path.startswith(".."):
            raise SecurityError("Path is outside of working directory: %s" 
                            % unnorm_path)
        return norm_path
    
def get_dialect(dialect_name):
    """Looks up the dialect in the dialect registry by name."""
    return dialects.get(dialect_name)

def infer_dialect(directory):
    d = set(dialects.values())
    cwd = os.getcwd()
    directory = os.path.abspath(directory)
    try:
        os.chdir(directory)
        remove_dialects = set()
        prev = None
        # stop when we hit the root directory (os.dirname
        # will stop giving us different values)
        while prev != directory:
            for dialect in d:
                is_match = dialect.cwd_is_this_dialect()
                if is_match == 0:
                    continue
                elif is_match == 1:
                    break
                else:
                    # in the case of Subversion, for example,
                    # if the directory doesn't have .svn in it, we
                    # know there's no match
                    remove_dialects.add(dialect)
            
            if is_match == 1:
                return dialect
            
            d.difference_update(remove_dialects)
            remove_dialects.clear()
            prev = directory
            directory = os.path.dirname(directory)
    finally:
        os.chdir(cwd)
    return None

def get_command_class(context, args, dialect=None):
    """This is similar to convert, but removes a step from the
    process. Use this if you need to inspect the command
    class before fulling setting up the context. Then,
    use from_args on the returned class to get an instance."""
    if dialect is None and args[0] in dialects:
        dialect_name = args.pop(0)
        dialect = get_dialect(dialect_name)
        command_name = args.pop(0)
        return dialect.get_dialect_command_class(command_name)
    else:
        generic_command_class = commands.get_command_class(context, args)
        guessed_dialect = generic_command_class.guess_dialect(context, args)
        if guessed_dialect:
            dialect = get_dialect(guessed_dialect)
        if dialect is None:
            raise commands.UVCError("Cannot run without knowing which VCS to use")
        return dialect.convert_class(generic_command_class)

def convert(context, args, dialect=None):
    """Converts the arguments provided into a command in the given dialect,
    or figures out the dialect for the project."""
    cmdclass = get_command_class(context, args, dialect)
    return cmdclass.from_args(context, args)

def run_command(command, context):
    command_line = command.get_command_line()
    log.debug("Running: %s", (command_line,))
    log.debug("Working dir: %s", context.working_dir)
    
    returncode, stdout = run_in_directory(context.working_dir, command_line)
    
    output = command.process_output(returncode, stdout)
    log.debug("Command output: %s", output)
    return output

def _get_command_with_blanks_filled_in(context, args, dialect):
    """This will launch the user's text editor for
    items that really need to be filled in (such as
    commit messages)."""
    while True:
        try:
            return convert(context, args, dialect=dialect)
        except commands.GetValueFromEditor, e:
            editor = os.environ.get("EDITOR", "vi")
            tfile_handle, tfile_name = tempfile.mkstemp()
            try:
                command_line = [editor, tfile_name]
                p = subprocess.Popen(command_line).wait()
                contents = open(tfile_name).read()
            finally:
                os.unlink(tfile_name)
            if not contents:
                print "No text entered... exiting."
                sys.exit(1)
            args = e.template_args
            for i in range(0, len(args)):
                if args[i] == commands.inserted_value:
                    args[i] = contents
            
def is_new_project_command(args):
    log.debug("Verifying new project for %s", args)
    if args[0] == "clone" or args[0] == "checkout" \
       or (len(args) > 2 and " ".join(args[0:2]) in
       ["hg clone", "bzr clone", "git clone", "svn checkout"]):
        return True
    return False

def run(args=None):
    if args is None:
        args = sys.argv
    args.pop(0)
    
    cwd = os.getcwd()
    context = Context(cwd)
    
    if args and args[0] in dialects:
        dialect = None
    elif not is_new_project_command(args):
        dialect = infer_dialect(cwd)
    else:
        dialect = None
    
    command = _get_command_with_blanks_filled_in(context, args, dialect)
    output = run_command(command, context)
    print str(output)
    
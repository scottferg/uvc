"""Implements the Git VCS dialect."""
import os

from uvc.commands import UVCError, DialectCommand, StatusOutput, BaseCommand
from uvc.exc import RepositoryAlreadyInitialized

class GitError(UVCError):
    """A Git-dialect specific error."""
    pass

class GitCommand(DialectCommand):
    dialect_name = "git"

class AuthGitCommand(GitCommand):
    def command_parts(self):
        parts = super(AuthGitCommand, self).command_parts()
        auth = self.generic.auth
        if auth:
            if auth['type'] == "ssh":
                parts.insert(1, "-e")
                # setting StrictHostKeyChecking to no is less than ideal...
                parts.insert(2, "ssh -i %s -o StrictHostKeyChecking=no" % (auth['key']))
        return parts

class init(GitCommand):
    reads_remote = False
    writes_remote = False
    
    @classmethod
    def from_args(cls, context, args):
        return cls(context, args)
        
    def __init__(self, context, args):
        from uvc import main
        dialect = main.infer_dialect(context.working_dir)
        if dialect:
            raise RepositoryAlreadyInitialized("It looks like there is an %s" 
                            " repository there" % dialect.name)
        
    def command_parts(self):
        return ['init']

class clone(AuthGitCommand):
    reads_remote = True
    writes_remote = False

    def __init__(self, context, args):
        super(clone, self).__init__(context, args)
        
        # If this is a git repository, make sure to
        # remove the extension in the URL
        if self.dest[-4:] == ".git":
            self.dest = self.dest[:-4]

checkout = clone

class commit(GitCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(commit, self).command_parts()
        if self.generic.user:
            parts.insert(1, "-a")
        return parts
    
class diff(GitCommand):
    reads_remote = False
    writes_remote = False
    
class remove(GitCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(remove, self).command_parts()
        # uvc's remove command implies "force"
        parts.insert(1, "-f")
        return parts

class add(GitCommand):
    reads_remote = False
    writes_remote = False
    
class push(AuthGitCommand):
    reads_remote = True
    writes_remote = True
    
class update(AuthGitCommand):
    reads_remote = True
    writes_remote = False
    
    def command_parts(self):
        parts = super(update, self).command_parts()
        parts[0] = "fetch"
        return parts

class resolved(GitCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(resolved, self).command_parts()
        parts[0] = "resolve"
        parts.insert(1, "-m")
        if not self.targets:
            parts.append("-a")
        return parts
        
class status(GitCommand):
    reads_remote = False
    writes_remote = False
    
    def process_output(self, returncode, stdout):
        return StatusOutput(returncode, stdout)
    
class revert(GitCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(revert, self).command_parts()
        parts.insert(1, "--no-backup")
        if not self.targets:
            parts.append("-a")
        return parts
    

class GitDialect(object):
    
    name = "git"
    
    def convert(self, command_object):
        """Converts to a Git-specific command."""
        local_command = self.get_dialect_command_class(command_object.__class__.__name__)
        return local_command(command_object)
    
    def convert_class(self, command_class):
        """Converts a generic command class to its equivalent."""
        local_command_class = self.get_dialect_command_class(command_class.__name__)
        return local_command_class
    
    def get_dialect_command_class(self, command_name):
        """Looks up a Git-specific command and returns the
        class."""
        local_command = globals().get(command_name)
        if not local_command:
            raise GitError("Command cannot be converted to git: %s" 
                            % (command_name))
        return local_command
    
    def get_dialect_command(self, context, command_name, args):
        """Looks up a Git-specific command."""
        local_command = self.get_dialect_command_class(command_name)
        return local_command.from_args(context, args)
    
    def cwd_is_this_dialect(self):
        """Returns 1 if the .git directory is here, 0 otherwise."""
        if os.path.isdir(".git"):
            return 1
        return 0
    

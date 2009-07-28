"""Implements the Mercurial VCS dialect."""
import os

from uvc.commands import UVCError, DialectCommand, StatusOutput, BaseCommand
from uvc.exc import RepositoryAlreadyInitialized

class HgError(UVCError):
    """A Mercurial-dialect specific error."""
    pass

class HgCommand(DialectCommand):
    dialect_name = "hg"

class AuthHgCommand(HgCommand):
    def command_parts(self):
        parts = super(AuthHgCommand, self).command_parts()
        auth = self.generic.auth
        if auth:
            if auth['type'] == "ssh":
                parts.insert(1, "-e")
                # setting StrictHostKeyChecking to no is less than ideal...
                parts.insert(2, "ssh -i %s -o StrictHostKeyChecking=no" % (auth['key']))
        return parts

class init(HgCommand):
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
    

class clone(AuthHgCommand):
    reads_remote = True
    writes_remote = False

checkout = clone

class commit(HgCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(commit, self).command_parts()
        if self.generic.user:
            parts.insert(1, "-u")
            parts.insert(2, self.generic.user)
        return parts
    
class diff(HgCommand):
    reads_remote = False
    writes_remote = False
    
class remove(HgCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(remove, self).command_parts()
        # uvc's remove command implies "force"
        parts.insert(1, "-f")
        return parts

class add(HgCommand):
    reads_remote = False
    writes_remote = False
    
class push(AuthHgCommand):
    reads_remote = True
    writes_remote = True
    
class update(AuthHgCommand):
    reads_remote = True
    writes_remote = False
    
    def command_parts(self):
        parts = super(update, self).command_parts()
        parts[0] = "fetch"
        return parts

class resolved(HgCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(resolved, self).command_parts()
        parts[0] = "resolve"
        parts.insert(1, "-m")
        if not self.targets:
            parts.append("-a")
        return parts
        
class status(HgCommand):
    reads_remote = False
    writes_remote = False
    
    def process_output(self, returncode, stdout):
        return StatusOutput(returncode, stdout)
    
class revert(HgCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        parts = super(revert, self).command_parts()
        parts.insert(1, "--no-backup")
        if not self.targets:
            parts.append("-a")
        return parts
    

class HgDialect(object):
    
    name = "hg"
    
    def convert(self, command_object):
        """Converts to a Mercurial-specific command."""
        local_command = self.get_dialect_command_class(command_object.__class__.__name__)
        return local_command(command_object)
    
    def convert_class(self, command_class):
        """Converts a generic command class to its equivalent."""
        local_command_class = self.get_dialect_command_class(command_class.__name__)
        return local_command_class
    
    def get_dialect_command_class(self, command_name):
        """Looks up a Mercurial-specific command and returns the
        class."""
        local_command = globals().get(command_name)
        if not local_command:
            raise HgError("Command cannot be converted to hg: %s" 
                            % (command_name))
        return local_command
    
    def get_dialect_command(self, context, command_name, args):
        """Looks up a Mercurial-specific command."""
        local_command = self.get_dialect_command_class(command_name)
        return local_command.from_args(context, args)
    
    def cwd_is_this_dialect(self):
        """Returns 1 if the .hg directory is here, 0 otherwise."""
        if os.path.isdir(".hg"):
            return 1
        return 0
    
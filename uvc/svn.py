"""Implements the Subversion VCS dialect."""
import os

from uvc.commands import UVCError, DialectCommand, StatusOutput, BaseCommand
from uvc.exc import RepositoryAlreadyInitialized

class SVNError(UVCError):
    """A Subversion-specific error."""
    pass

class SVNCommand(DialectCommand):
    dialect_name = "svn"

class AuthSVNCommand(SVNCommand):
    def command_parts(self):
        parts = super(AuthSVNCommand, self).command_parts()
        auth = self.generic.auth
        if auth:
            if auth['type'] == "ssh":
                parts.insert(0, "--non-interactive")
                parts.insert(1, "--trust-server-cert")
                parts.insert(2, "")
                parts.insert(3, "")
                parts.insert(4, "")
                #parts.insert(1, "-e")
                # setting StrictHostKeyChecking to no is less than ideal...
                #parts.insert(2, "ssh -i %s -o StrictHostKeyChecking=no" % (auth['key']))
            elif auth['type'] == "password":
                parts.insert(0, "--non-interactive")
                parts.insert(1, "--username")
                parts.insert(2, auth['username'])
                parts.insert(3, "--password")
                parts.insert(4, auth['password'])
        return parts

class init(SVNCommand):
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

class clone(AuthSVNCommand):
    reads_remote = True
    writes_remote = False

    def command_parts(self):
        parts = super(clone, self).command_parts()
        parts[5] = "checkout"
        return parts

checkout = clone

class commit(SVNCommand):
    reads_remote = False
    writes_remote = False

class diff(SVNCommand):
    reads_remote = False
    writes_remote = False

class remove(SVNCommand):
    reads_remote = False
    writes_remote = False

    def command_parts(self):
        parts = super(remove, self).command_parts()
        # uvc's remove command implies "force"
        parts.insert(1, "--force")
        return parts

delete = remove

class add(SVNCommand):
    reads_remote = False
    writes_remote = False

class push(AuthSVNCommand):
    reads_remote = True
    writes_remote = True

    def command_parts(self):
        parts = super(clone, self).command_parts()
        parts[0] = "commit"
        parts.insert(1, "-m");
        # Where are we storing the commit message?
        return parts

class update(AuthSVNCommand):
    reads_remote = True
    writes_remote = False

#    def command_parts(self):
#        parts = super(update, self).command_parts()
#        parts[0] = "update"
#        return parts

#class resolved(SVNCommand):
#    reads_remote = False
#    writes_remote = False
#
#    def command_parts(self):
#        parts = super(resolved, self).command_parts()
#        parts[0] = "resolve"
#        parts.insert(1, "-m")
#        if not self.targets:
#            parts.append("-a")
#        return parts

class status(SVNCommand):
    reads_remote = False
    writes_remote = False

    def process_output(self, returncode, stdout):
        return StatusOutput(returncode, stdout)

class revert(SVNCommand):
    reads_remote = False
    writes_remote = False

#    def command_parts(self):
#        parts = super(revert, self).command_parts()
#        parts.insert(1, "--no-backup")
#        if not self.targets:
#            parts.append("-a")
#        return parts

class SVNDialect(object):
    
    name = "svn"
    
    def convert(self, command_object):
        """Converts to an SVN-specific command."""
        local_command = self.get_dialect_command_class(command_object.__class__.__name__)
        return local_command(command_object)
        
    def convert_class(self, command_class):
        """Converts a generic command class to its equivalent."""
        local_command_class = self.get_dialect_command_class(command_class.__name__)
        return local_command_class
        
    def get_dialect_command_class(self, command_name):
        """Looks up an svn-specific command class."""
        local_command = globals().get(command_name)
        if not local_command:
            raise SVNError("Command cannot be converted to svn: %s" 
                            % (command_name))
        return local_command
    
    def get_dialect_command(self, context, command_name, args):
        """Looks up an svn-specific command."""
        local_command = self.get_dialect_command_class(command_name, args)
        return local_command.from_args(context, args)
    
    def cwd_is_this_dialect(self):
        """Returns 1 if the .svn directory is here, 2 otherwise. svn
        plants directories everywhere, so if it's not in the current
        directory, it's not an svn project."""
        if os.path.isdir(".svn"):
            return 1
        return 2
    
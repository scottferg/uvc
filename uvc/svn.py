"""Implements the Subversion VCS dialect."""
import os
import re
import glob

from uvc.commands import UVCError, DialectCommand, StatusOutput, BaseCommand,\
                        SimpleStringOutput
from uvc.exc import RepositoryAlreadyInitialized
from uvc import util

class SVNError(UVCError):
    """A Subversion-specific error."""
    pass

class SVNCommand(DialectCommand):
    dialect_name = "svn"

class AuthSVNCommand(SVNCommand):
    def add_auth_info(self, parts):
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
    
    def command_parts(self):
        parts = super(AuthSVNCommand, self).command_parts()
        self.add_auth_info(parts)
        return parts

class clone(AuthSVNCommand):
    reads_remote = True
    writes_remote = False

    def command_parts(self):
        parts = ["checkout", self.source_without_auth, self.dest]
        
        self.add_auth_info(parts)
            
        return parts

checkout = clone

def _commit_log_file(working_dir):
    return working_dir / ".svn_commit_messages"

class commit(SVNCommand):
    reads_remote = False
    writes_remote = False
    
    def command_parts(self):
        return []
        
    def get_command_line(self):
        return None
        
    def get_output(self):
        commit_log = _commit_log_file(self.generic.working_dir)
        if not commit_log.exists():
            content = self.generic.message + "\n\n"
        else:
            content = commit_log.text() + self.generic.message + "\n\n"
        commit_log.write_text(content)
        return SimpleStringOutput("Commit message saved. Don't forget to push to save to the remote repository!")

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

_status_line_mask = re.compile("^(.)..... (.*)$")

def _get_file_list(working_dir, status="?"):
    retcode, stdout = util.run_in_directory(working_dir,
        ["svn", "status"])
    status_lines = stdout.read().split("\n")
    file_list = []
    for line in status_lines:
        m = _status_line_mask.match(line)
        if not m:
            continue
        if m.group(1) == status:
            filename = m.group(2)
            if not filename.startswith("."):
                file_list.append(m.group(2))
    
    return file_list

class add(SVNCommand):
    reads_remote = False
    writes_remote = False

    def command_parts(self):
        parts = super(add, self).command_parts()
        if not self.targets:
            parts.extend(_get_file_list(self.generic.working_dir))
        return parts

class push(AuthSVNCommand):
    reads_remote = True
    writes_remote = True
    
    def get_command_line(self):
        commit_log = _commit_log_file(self.generic.working_dir)
        if not commit_log.exists():
            return None
        return super(push, self).get_command_line()
        
    def get_output(self):
        # only called if the commit_log doesn't exist
        return SimpleStringOutput("Nothing to push. Run commit first.")
    
    def command_parts(self):
        parts = []
        self.add_auth_info(parts)
        parts.append("commit")
        parts.append("-m")
        commit_log = _commit_log_file(self.generic.working_dir)
        parts.append(commit_log.text())
        return parts
        
    def command_successful(self):
        commit_log = _commit_log_file(self.generic.working_dir)
        commit_log.unlink()

class update(AuthSVNCommand):
    reads_remote = True
    writes_remote = False

    def command_parts(self):
        parts = ["update"]
        self.add_auth_info(parts)
        return parts

class resolved(SVNCommand):
   reads_remote = False
   writes_remote = False

   def command_parts(self):
       parts = super(resolved, self).command_parts()
       parts[0] = "resolve"
       parts.insert(1, "--accept")
       parts.insert(2, "working")
       if not self.targets:
           parts.extend(_get_file_list(self.generic.working_dir, status="C"))
       return parts

class status(SVNCommand):
    reads_remote = False
    writes_remote = False

    def process_output(self, returncode, stdout):
        return StatusOutput(returncode, stdout)

class revert(SVNCommand):
    reads_remote = False
    writes_remote = False

    def command_parts(self):
        parts = super(revert, self).command_parts()
        if not self.targets:
            parts.append("-R")
            pwd = os.getcwd()
            try:
                os.chdir(self.generic.working_dir)
                parts.extend(glob.glob("*"))
            finally:
                os.chdir(pwd)
        return parts

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
    
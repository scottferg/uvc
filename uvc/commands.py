"""The basic set of Uber Version Controller commands. These are the commands
that are not specific to any given version control system."""

from optparse import OptionParser
from urlparse import urlparse, urlunparse

from uvc.path import path
from uvc.exc import *

class Sentinel(object):
    pass

inserted_value = Sentinel()

class GetValueFromEditor(UVCError):
    def __init__(self, template_args, prompt):
        self.template_args = template_args
        self.prompt = prompt
    
class BasicOutput(object):
    def __init__(self, return_code, stdout):
        self.return_code = return_code
        self.output = stdout.read()
    
    def __str__(self):
        return self.output

class DialectCommand(object):
    """Base class for the dialect-specific command classes.
    If you subclass this, the default behavior is to pass
    through the generic command interpretation."""
    
    # dialects should override this
    dialect_name = ""
    
    @classmethod
    def from_args(cls, context, args):
        generic = globals()[cls.__name__](context, args)
        return cls(generic)

    def __init__(self, generic):
        self.generic = generic

    def __str__(self):
        return " ".join(self.command_parts())
    
    def process_output(self, return_code, stdout):
        return BasicOutput(return_code, stdout)
    
    def command_parts(self):
        return self.generic.command_parts()
    
    def get_command_line(self):
        return [self.dialect_name] + self.command_parts()
        
    def set_auth(context):
        """Updates the authentication information based on the
        context. It is generally best for __init__ to call
        this, but there will be times when the authentication
        requirements are not known before this object is
        created. The default behavior is to do nothing."""
        pass
        
    def __getattr__(self, attr):
        return getattr(self.generic, attr)
    
class BaseCommand(object):
    def __init__(self, context, args):
        self.auth = context.auth
        self.user = context.user
    
    def __str__(self):
        return " ".join(self.command_parts())
    
    @classmethod
    def guess_dialect(cls, context, args):
        return None

def _apply_auth(url, context):
    parsed = urlparse(url)
    
    if parsed.scheme == "" or parsed.scheme == "file":
        # we don't need to apply auth info to local files
        return url
        
    auth = context.auth
    if auth:
        if 'username' in auth or 'password' in auth:
            # build up username/password for URL from the context
            new_url = list(parsed)
            auth_info = [auth['username']]
            if 'password' in auth:
                auth_info.append(auth['password'])
            
            # strip off the old auth info
            netloc = parsed.netloc
            if "@" in netloc:
                netloc = netloc.split('@')[1]
                
            new_url[1] = "%s@%s" % (":".join(auth_info), netloc)
            url = urlunparse(new_url)
    return url
    

class clone(BaseCommand):
    # source of the repository to get
    source = None
    
    # where to put the resulting files
    dest = None
    
    reads_remote = True
    writes_remote = False
    
    @classmethod
    def guess_dialect(cls, context, args):
        guessed = None
        source = args[0]
        if "hg" in source:
            guessed = "hg"
        elif "svn" in source:
            guessed = "svn"
        elif "git" in source:
            guessed = "git"
        elif "bzr" in source:
            guessed = "bzr"
        return guessed
    
    def __init__(self, context, args):
        super(clone, self).__init__(context, args)
        if len(args) < 1:
            raise BadArgument("Clone requires a source argument")
        source = args[0]
        
        self.guessed_dialect = self.guess_dialect(context, args)
        
        parsed = urlparse(source)
        
        source = _apply_auth(source, context)
                    
        self.source = source
        
        if len(args) == 2:
            self.dest = args[1]
        else:
            if parsed.path.endswith("/"):
                index = -2
            else:
                index = -1
            last_path = parsed.path.split('/')[index]
            if not last_path:
                raise BadArgument("Clone requires source and dest arguments.")
            self.dest = last_path

        context.validate_new_directory(self.dest)
    
    def command_parts(self):
        return ["clone", self.source, self.dest]
    
checkout = clone
    
class commit(BaseCommand):
    """Commit command."""
    # commit message
    message = None
    
    # specific directories/files to commit
    targets = None
    
    # this is the DVCS view of commit
    reads_remote = False
    writes_remote = False
    
    parser = OptionParser()
    parser.add_option('-m', "--message", dest="message", 
        help="commit message")
    
    def __init__(self, context, args):
        super(commit, self).__init__(context, args)
        options, args = self.parser.parse_args(args)
        if not options.message:
            args = ["commit", "-m", inserted_value] + args
            raise GetValueFromEditor(args, "Please enter a commit message")
        self.message = options.message
        for target in args:
            context.validate_exists(target)
        self.targets = args
        
    def command_parts(self):
        parts = ["commit"]
        message = self.message
        if message is not None:
            parts.extend(["-m", message])
        targets = self.targets
        if targets:
            parts.extend(targets)
        return parts
    
class WithTargets(BaseCommand):
    """Base class for commands that take a set of target files"""
    targets_required = False
    
    def __init__(self, context, args):
        super(WithTargets, self).__init__(context, args)
        for target in args:
            context.validate_exists(target)
            
        if args:
            self.targets = args
        else:
            if self.targets_required:
                raise UVCError("You must list at least one file to remove.")
            else:
                self.targets = None
            
    def command_parts(self):
        parts = [self.__class__.__name__]
        if self.targets:
            parts.extend(self.targets)
        return parts

class diff(WithTargets):
    """The diff command"""
    
    reads_remote = False
    writes_remote = False
    
class remove(WithTargets):
    """Remove a file from the repository."""
    targets_required = True
    
    reads_remote = False
    writes_remote = False
    
class add(WithTargets):
    """The add command, to add files"""
    
    reads_remote = False
    writes_remote = False

class resolved(WithTargets):
    """Marks files as resolved."""
    
    reads_remote = False
    writes_remote = False
    
class status(WithTargets):
    """Retrieve the status of the files in the working copy."""
    
    reads_remote = False
    writes_remote = False
    
class revert(WithTargets):
    """Revert a set of files"""
    
    reads_remote = False
    writes_remote = False

class StatusOutput(object):
    """Output specific to a status command."""
    
    MODIFIED = "M"
    ADDED = "A"
    REMOVED = "R"
    CLEAN = "C"
    MISSING = "!"
    UNKNOWN = "?"
    IGNORED = "I"
    valid_values = set(['M', 'A', 'R', 'C', '!', '?', 'I'])
    
    def __init__(self, returncode, stdout):
        data = []
        line = stdout.readline()
        while line:
            line = line.rstrip()
            if line and line[0] in StatusOutput.valid_values:
                data.append(line.split(" ", 1))
            line = stdout.readline()
        self.data = data
    
    def as_list(self):
        return self.data
    
    def __str__(self):
        return "\n".join(" ".join(info) for info in self.data) + "\n"
    
class push(BaseCommand):
    """The push command"""
    
    reads_remote = True
    writes_remote = True
    
    def __init__(self, context, args):
        super(push, self).__init__(context, args)
        
        if args:
            dest = args[0]
            if context.remote_scheme_whitelist:
                parsed = urlparse(dest)
                if parsed.scheme not in context.remote_scheme_whitelist:
                    raise SecurityError("Push is limited to only permitted remote repositories")
            self.dest = _apply_auth(dest, context)
        else:
            self.dest = None
    
    def command_parts(self):
        parts = ["push"]
        if self.dest:
            parts.append(self.dest)
            
        return parts

class update(BaseCommand):
    """The update command, intended to act like Mercurial's fetch:
    does a pull from the remote repository and an update of the local
    working copy, merging as needed."""
    
    reads_remote = True
    writes_remote = False
    
    source = None
    
    def __init__(self, context, args):
        super(update, self).__init__(context, args)
        if args:
            source = args[0]
            parsed = urlparse(source)
            
            if context.remote_scheme_whitelist:
                if parsed.scheme not in context.remote_scheme_whitelist:
                    raise SecurityError("Push is limited to only permitted remote repositories")

            source = _apply_auth(source, context)
            self.source = source
    
    def command_parts(self):
        parts = ["update"]
        if self.source:
            parts.append(self.source)
        return parts
    
def get_command_class(context, args):
    """Retrieve a command's class."""
    command_name = args.pop(0).lower()
    command_class = globals().get(command_name)
    if not command_class:
        raise UnknownCommand("There is no %s command." % (command_name))
    return command_class
    
def get_command(context, args):
    """Retrieve a command object based on the command line given"""
    command_class = get_command_class(context, args)
    return command_class(context, args)
    
"""Exceptions for UVC"""

class UVCError(Exception):
    """Root exception for UVC problems"""
    pass
    
class BadArgument(UVCError):
    """An argument provided to the command was invalid."""
    pass

class UnknownCommand(UVCError):
    """Error when a non-existent command is requested."""
    pass

class FileError(UVCError):
    """Error for files and directories that are out of place."""
    pass

class SecurityError(UVCError):
    """Error for attempting to access something that is
    not known to be secure for remote access."""
    pass
    
class RepositoryAlreadyInitialized(UVCError):
    """Denotes that a directory is already version
    controlled when the user tries to initialize
    it."""
    pass
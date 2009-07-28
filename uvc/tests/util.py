"""Utilities for testing VCS, specifically for working around not acually needing to
run a VCS."""
from functools import wraps
from cStringIO import StringIO

from uvc import main, commands
from uvc.path import path

topdir = (path(__file__).parent)

def mock_run_command(command_output, create_dir=None):
    """Monkeypatches in a new run_command function in uvc.main
    so that we can pretend about what happens when you run the
    command."""
    run_command_params = []
    def new_run_command(command, context):
        run_command_params.append(command)
        run_command_params.append(context)
        if create_dir is not None:
            working_dir = path(context.working_dir)
            (working_dir / create_dir).mkdir()
        return command.process_output(0, StringIO(command_output))
        
    def entangle(func):
        @wraps(func)
        def new_one():
            old_run_command = main.run_command
            try:
                main.run_command = new_run_command
                return func(run_command_params)
            finally:
                main.run_command = old_run_command
        return new_one
    return entangle

class TestContext(main.Context):
    def _normalize_path(self, unnorm_path):
        return super(TestContext, self)._normalize_path(topdir)

test_context = TestContext(topdir)



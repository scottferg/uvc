"""Utility functions used by uvc."""

import os
import subprocess

def run_in_directory(working_dir, command_line):
    current_dir = os.getcwd()
    os.chdir(working_dir)
    try:
        p = subprocess.Popen(command_line, 
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()
    finally:
        os.chdir(current_dir)
    
    return [p.returncode, p.stdout]
    
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

import os
from os.path import join as pjoin
import subprocess
import sys

pnorm = lambda path : os.path.normpath(os.path.expanduser(path))

def warning(*objs):
    print("WARNING: ", *objs, file=sys.stderr)

def fail(message):
    sys.exit("ERROR: {message}".format(message=message))

# SETTINGS
PROJECT_DIR = pnorm(os.path.dirname(os.path.realpath(__file__)))
PROJECT = os.path.basename(PROJECT_DIR)
WORKON_HOME = pnorm(os.environ.get("WORKON_HOME", pjoin("~", ".venv")))
VIRTUAL_ENV = pnorm(os.environ.get("VIRTUAL_ENV", pjoin(WORKON_HOME, PROJECT)))

def has_module(module_name):
    try:
        import imp
        imp.find_module(module_name)
        del imp
        return True
    except ImportError:
        return False

def pip_install(args):
    """Pip install arguments."""
    pip = pjoin(VIRTUAL_ENV, 'bin', 'pip')
    command = [pip, 'install'] + list(args)
    subprocess.check_call(command)
    
def mkvirtualenv(version='', project=PROJECT_DIR, name=PROJECT):
    """Make a new virtualenv."""
    subprocess.check_call(['mkvirtualenv', 
                           '--python', 'python{0:s}'.format(version), 
                           '-a', project, name ])

def main():
    """Main function to bootstrap things"""
    if not os.path.exists(VIRTUAL_ENV):
        print("Building virtual environment for {0}".format(PROJECT))
        mkvirtualenv(project=PROJECT_DIR, name=PROJECT)
    
    requirements = pjoin(PROJECT_DIR, 'requirements.txt')
    if not os.path.exists(requirements):
        error("Can't find requirements.txt at {0}".format(requirements))
    pip_install(['-r', requirements])
    requirements_dir = pjoin(PROJECT_DIR, 'requirements')
    if os.path.exists(requirements_dir):
        pip_install(['-r', pjoin(requirements_dir,'test.txt')])
        pip_install(['-r', pjoin(requirements_dir,'doc.txt')])
    else:
        warning("No requirements/ directory found in {0}".format(PROJECT_DIR))

if __name__ == '__main__':
    main()
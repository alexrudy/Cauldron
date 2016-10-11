# -*- coding: utf-8 -*-
"""
Console scripts for KTL.
"""

import argparse
import collections
import time
import logging
import sys

from .exc import TimeoutError, DispatcherError
from .config import get_timeout

try:
    import lumberjack
    lumberjack.setup_warnings_logger()
except:
    pass

class BackendAction(argparse.Action):
    """An action to select a KTL backend."""
    
    def __init__(self, option_strings, dest, **kwargs):
        """Handle add_argument args."""
        kwargs['nargs'] = 1
        kwargs['const'] = None
        kwargs.setdefault('default','ktl')
        kwargs['type'] = str
        kwargs['choices'] = None
        kwargs.setdefault('required', False)
        kwargs.setdefault('help', "The Cauldron backend to use.")
        kwargs.setdefault('metavar', 'backend')
        super(BackendAction, self).__init__(option_strings, dest, **kwargs)
        
    def __call__(self, parser, namespace, values, option_string):
        """Actions to take to set up the Cauldron backend."""
        from .api import use
        backend = values[0]
        try:
            use(backend)
        except ValueError as e:
            parser.error("The backend '{0}' is not available.\n{1!s}".format(backend, e))
        setattr(namespace, self.dest, values[0])
        
    
class ConfigureAction(argparse.Action):
    """An action to configure Cauldron."""
    def __init__(self, option_strings, dest, **kwargs):
        kwargs['nargs'] = 1
        kwargs['const'] = None
        kwargs.setdefault('default','cauldron.cfg')
        kwargs['type'] = str
        kwargs['choices'] = None
        kwargs.setdefault('required', False)
        kwargs.setdefault('help', "The Cauldron configuration file.")
        kwargs.setdefault('metavar', 'configuration')
        super(ConfigureAction, self).__init__(option_strings, dest, **kwargs)
    
    def __call__(self, parser, namespace, values, option_string):
        """Actions to take to configure cauldron."""
        from .config import read_configuration
        configuration = read_configuration(values)
        setattr(namespace, 'config', configuration)
        

def setup_debug_logging():
    """Setup debug logging."""
    try:
        import lumberjack
        h = lumberjack.SplitStreamHandler()
        h.setFormatter(lumberjack.ColorFormatter("%(clevelname)s: %(message)s [%(name)s]"))
    except:
        h = logging.StreamHandler()
    
    h.setLevel(logging.DEBUG)
    for logger in ["Cauldron", "ktl"]:
        logger = logging.getLogger(logger)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(h)

def show():
    """Argument parsing and actions."""
    parser = argparse.ArgumentParser(description="Show a single keyword value.")
    parser.add_argument('-c', '--configuration', action=ConfigureAction, 
        help="The Cauldron configuration file.")
    parser.add_argument('-k', '--backend', action=BackendAction, default='ktl',
        help="The Cauldron Backend to use.")
    parser.add_argument('-s', '--service', type=str, required=True,
        help="Name of the KTL service containing the keyword(s) to display.")
    parser.add_argument('-b', '--binary', action='store_true',
        help="Display the binary version of a keyword.")
    parser.add_argument('-d', '--debug', action='store_true',
        help="Show debug information.")
    parser.add_argument('keyword', type=str, nargs="+", help="Name of the KTL Keyword to display.")
    opt = parser.parse_args()
    if opt.debug:
        setup_debug_logging()
    ktl_show(opt.service, *opt.keyword, binary=opt.binary)
    return 0
    
def ktl_show(service, *keywords, **options):
    """Implement the KTL Show functionality."""
    from Cauldron import ktl
    binary = options.pop('binary', False)
    outfile = options.pop('output', sys.stdout)
    errfile = options.pop('error', sys.stderr if outfile == sys.stdout else outfile)
    
    svc = ktl.Service(service, populate=False)
    for keyword in keywords:
        
        try:
            keyword = svc[keyword]
        except KeyError as e:
            errfile.write("Can't find keyword '{0}' in service '{1}'\n{2!s}\n".format(
                keyword.upper(), svc.name, e
            ))
            errfile.flush()
            continue
        
        try:
            value = keyword.read(binary=binary)
        except DispatcherError as e:
            errfile.write("Can't read from keyword '{0}'\n{1!s}".format(keyword.full_name, e))
            errfile.flush()
            continue
        
        unit = keyword['units']
        if unit is None:
            outfile.write("{0}: {1}\n".format(keyword.name, value))
            outfile.flush()
        else:
            outfile.write("{0}: {1} {2}\n".format(keyword.name, value, unit))
            outfile.flush()
    return

def parseModifyCommands(commands, flags, verbose=False):
    """Parse modify commands, yielding values"""
    keyword, assignment = None, False
    
    for argument in commands:
        argument = str(argument)
        if verbose: print(argument, keyword, assignment)
        if keyword is None:
            if "=" in argument:
                keyword, proposed_value = argument.split("=", 1)
                if proposed_value.strip() != '':
                    yield keyword, proposed_value
                    if verbose: print("y-1", keyword, proposed_value)
                    
                    keyword, assignment = None, False
                else:
                    assignment = True
            elif argument.lower() in flags:
                flags[argument.lower()] = True
            else:
                keyword = argument
        
        elif assignment is False:
            if argument[0] != "=":
                raise ValueError("Expected an assignment for keyword '{0} {1}'".format(keyword, argument))
            else:
                yield keyword, argument[1:]
                if verbose: print("y-2", keyword, argument[1:])
                keyword, assignment = None, False
        else:
            if argument[0] == "=":
                # There was an '=' in the keyword value.
                yield keyword, argument
                if verbose: print("y-3", keyword, argument)
                keyword, assignment = None, False
            elif "=" in argument:
                yield keyword, ''
                if verbose: print("y-4", keyword, '')
                keyword, proposed_value = argument.split("=", 1)
                if proposed_value.strip() != '':
                    yield keyword, proposed_value
                    if verbose: print("y-5", keyword, proposed_value)
                    keyword, assignment = None, False
                else:
                    assignment = True
            elif argument.lower() in flags:
                flags[argument.lower()] = True
            else:
                yield keyword, argument
                if verbose: print("y-6", keyword, argument)
                keyword, assignment = None, False
        
    
    if assignment:
        yield keyword, ''
    elif keyword is not None:
        raise ValueError("Incomplete assignment for keyword '{0}'".format(keyword))
            
                
            

def modify():
    """Argument parsing and actions for modify"""
    epilog="""
    For compatibility with the KROOT version of this script, flags may be passed without the prefix '-' in the list of regular command items. For example, to modify with nowait, you could write `modify -s SVC KWD=blah nowait`
    
    """
    parser = argparse.ArgumentParser(description="Modify a keyword value or a series of keyword values on a given KTL service.", epilog=epilog)
    parser.add_argument('-c', '--configuration', action=ConfigureAction, 
        help="The Cauldron configuration file.", metavar='config.cfg')
    parser.add_argument('-k', '--backend', action=BackendAction, default='ktl',
        help="The Cauldron Backend to use.")
    parser.add_argument('-s', '--service', type=str, required=True,
        help="Name of the KTL service containing the keyword(s) to modify.")
    parser.add_argument('-b', '--binary', action='store_true',
        help="Interpret an argument as.")
    parser.add_argument('-d', '--debug', action='store_true',
        help="Show debug information.")
    parser.add_argument('-n', '--nowait', action='store_true',
        help="Don't wait for modify to complete, return immediately.")
    parser.add_argument('-q', '--silent', action='store_true',
        help="Don't produce output.")
    parser.add_argument('-p', '--notify', action='store_true', dest='parallel',
        help="Process requests in parallel.")
    parser.add_argument('-t', '--timeout', type=float, help="Timeout when waiting for keywords.")
    parser.add_argument('commands', nargs="+", help="Keyword assignments", metavar="keyword=value")
    opt = parser.parse_args()
    
    flags = {'binary' : opt.binary, 'debug': opt.debug, 'notify' : opt.parallel, 'nowait' : opt.nowait,
        'silent' : opt.silent}
    try:
        commands = list(parseModifyCommands(opt.commands, flags))
    except ValueError as e:
        parser.error(str(e))
    for flag, value in flags.items():
        setattr(opt, flag, value)
    if opt.debug:
        setup_debug_logging()
    flags['timeout'] = opt.timeout
    try:
        ktl_modify(opt.service, *commands, **flags)
    except TimeoutError as e:
        parser.exit(status=2, message=str(e))
    except Exception as e:
        if opt.debug:
            raise
        parser.exit(status=1, message=str(e))
    return 0
    
    
def ktl_modify(service, *commands, **options):
    """Modify a series of KTL keywords."""
    from Cauldron import ktl
    
    # Handle arguments
    binary = options.pop('binary', False)
    debug = options.pop('debug', False)
    parallel = options.pop('notify', False)
    nowait = options.pop('nowait', False)
    wait = not (nowait or parallel)
    verbose = not options.pop('silent', False)
    timeout = get_timeout(options.pop('timeout', None))
    waitfor = collections.deque()
    outfile = options.pop('output', sys.stdout)
    errfile = options.pop('error', sys.stderr if outfile == sys.stdout else outfile)
    
    
    if parallel:
        mode = "(notify)"
    elif wait:
        mode = "(wait)"
    else:
        mode = "(nowait)"
    try:
        svc = ktl.Service(service, populate=False)
    
        # Initial write loop.
        for keyword, value in commands:
        
            try:
                keyword = svc[keyword]
            except KeyError as e:
                errfile.write("Can't find keyword '{0}' in service '{1}'\n{2!s}\n".format(
                    keyword.upper(), svc.name, e
                ))
                errfile.flush()
                continue
            else:
                if verbose:
                    outfile.write("setting {0:s} = {1:s} {2:s}\n".format(keyword.name, value, mode))
                    outfile.flush()
                sequence = keyword.write(value, binary=binary, wait=wait)
                if parallel == True and nowait == False:
                    waitfor.append((keyword, sequence))
        
    
        # Wait for writes to complete loop.
        start = time.time()
        while len(waitfor):
            if timeout is not None:
                elapsed = time.time() - start
                if elapsed > timeout:
                    raise TimeoutError("Error setting keyword(s): Timeout waiting for write(s) to complete")
            keyword, sequence = waitfor.popleft()
            success = keyword.wait(sequence=sequence, timeout=0.1)
            if not success:
                waitfor.append((keyword, sequence))
            elif success and verbose:
                outfile.write("{0:s} complete\n".format(keyword.name))
                outfile.flush()
    finally:
        svc.shutdown()
    return
    
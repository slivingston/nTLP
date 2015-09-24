#!/usr/bin/env python

from distutils.core import setup


###########################################
# Dependency or optional-checking functions
###########################################
# (see notes below.)

def check_gr1c():
    import subprocess
    try:
        subprocess.call(["gr1c", "-V"], stdout=subprocess.PIPE)
        subprocess.call(["rg", "-V"], stdout=subprocess.PIPE)
        subprocess.call(["grpatch", "-V"], stdout=subprocess.PIPE)
    except OSError:
        return False
    return True

def check_yaml():
    try:
        import yaml
    except ImportError:
        return False
    return True

def check_cvc4():
    import subprocess
    cmd = subprocess.Popen(['which', 'cvc4'],
                           stdout=subprocess.PIPE, close_fds=True)
    for line in cmd.stdout:
        if 'cvc4' in line:
            return True
    return False

def check_yices():
    import subprocess
    cmd = subprocess.Popen(['which', 'yices'],
                           stdout=subprocess.PIPE, close_fds=True)
    for line in cmd.stdout:
        if 'yices' in line:
            return True
    return False

def check_glpk():
    try:
        import cvxopt.glpk
    except ImportError:
        return False
    return True

def check_gephi():
    import subprocess
    cmd = subprocess.Popen(['which', 'gephi'], stdout=subprocess.PIPE)
    for line in cmd.stdout:
        if 'gephi' in line:
            return True
    return False


# Handle "dry-check" argument to check for dependencies without
# installing the tulip package; checking occurs by default if
# "install" is given, unless both "install" and "nocheck" are given
# (but typical users do not need "nocheck").

# You *must* have these to run TuLiP.  Each item in other_depends must
# be treated specially; thus other_depends is a dictionary with
#
#   keys   : names of dependency;

#   values : list of callable and string, which is printed on failure
#           (i.e. package not found); we interpret the return value
#           True to be success, and False failure.
other_depends = {}

# These are nice to have but not necessary. Each item is of the form
#
#   keys   : name of optional package;
#   values : list of callable and two strings, first string printed on
#           success, second printed on failure (i.e. package not
#           found); we interpret the return value True to be success,
#           and False failure.
optionals = {'glpk' : [check_glpk, 'GLPK found.', 'GLPK seems to be missing\nand thus apparently not used by your installation of CVXOPT.\nIf you\'re interested, see http://www.gnu.org/s/glpk/'],
             'gephi' : [check_gephi, 'Gephi found.', 'Gephi seems to be missing. If you\'re interested in graph visualization, see http://gephi.org/'],
             'gr1c' : [check_gr1c, 'gr1c found.', 'gr1c, rg, or grpatch not found.\nIf you\'re interested in a GR(1) synthesis tool besides JTLV, see http://scottman.net/2012/gr1c'],
             'PyYAML' : [check_yaml, 'PyYAML found.', 'PyYAML not found.\nTo read/write YAML, you will need to install PyYAML; see http://pyyaml.org/'],
             'yices' : [check_yices, 'Yices found.', 'Yices not found.'],
             'cvc4' : [check_cvc4, 'CVC4 found.', 'The SMT solver CVC4 was not found; see http://cvc4.cs.nyu.edu/\nSome functions in the rhtlp module will be unavailable.']}

import sys
perform_setup = True
check_deps = False
if 'install' in sys.argv[1:] and 'nocheck' not in sys.argv[1:]:
    check_deps = True
elif 'dry-check' in sys.argv[1:]:
    perform_setup = False
    check_deps = True

# Pull "dry-check" and "nocheck" from argument list, if present, to play
# nicely with Distutils setup.
try:
    sys.argv.remove('dry-check')
except ValueError:
    pass
try:
    sys.argv.remove('nocheck')
except ValueError:
    pass

if check_deps:
    if not perform_setup:
        print "Checking for required dependencies..."

        # Python package dependencies
        try:
            import numpy
        except:
            print 'ERROR: NumPy not found.'
            raise
        try:
            import scipy
        except:
            print 'ERROR: SciPy not found.'
            raise
        try:
            import cvxopt
        except:
            print 'ERROR: CVXOPT not found.'
            raise
        try:
            import matplotlib
        except:
            print 'ERROR: matplotlib not found.'
            raise

        try:
            import networkx
        except:
            print 'ERROR: NetworkX not found.'
            raise

        # Other dependencies
        for (dep_key, dep_val) in other_depends.items():
            if not dep_val[0]():
                print dep_val[1]
                raise Exception('Failed dependency: '+dep_key)

    # Optional stuff
    for (opt_key, opt_val) in optionals.items():
        print 'Probing for optional '+opt_key+'...'
        if opt_val[0]():
            print "\t"+opt_val[1]
        else:
            print "\t"+opt_val[2]


if perform_setup:
    from tulip import __version__ as tulip_version
    setup(name = 'tulip',
          version = tulip_version,
          description = 'nTLP (forked from Temporal Logic Planning toolbox)',
          author = 'Caltech Control and Dynamical Systems',
          author_email = 'slivingston@cds.caltech.edu',
          url = 'http://scottman.net/2013/nTLP',
          license = 'BSD',
          requires = ['numpy', 'scipy', 'cvxopt', 'matplotlib'],
          packages = ['tulip'],
          package_dir = {'tulip' : 'tulip'},
          package_data={'tulip': ['jtlv_grgame.jar', 'polytope/*.py']}
          )

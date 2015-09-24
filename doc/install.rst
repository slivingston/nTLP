.. Emacs, this is -*-rst-*-
.. highlight:: rst

Installation
============

TuLiP is known to work with Python versions 2.6 and 2.7.  (This
comment matters given dependence on Python standard libraries.)  To
determine your default installed version of Python, open a new
terminal and type::

  $ python -V

Note that you may have more than one version installed.  On Unix
machines, these are typically named with the usual "python" followed
by a major and minor version number, e.g. "python2.6".  Try looking
for these with::

  $ ls /usr/bin/python*

The following packages are also *required*: `NumPy <http://numpy.org/>`_, `SciPy
<http://www.scipy.org/>`_, `CVXOPT <http://abel.ee.ucla.edu/cvxopt/>`_,
`pyparsing <http://pyparsing.wikispaces.com/>`_, `NetworkX
<http://networkx.lanl.gov/>`_, and `matplotlib
<http://matplotlib.sourceforge.net/>`_ (at least version 1.1).  These packages
are quite standard in scientific computing environments and may already be
installed.  To check, open a new terminal and try::

  $ python -c 'import numpy'
  $ python -c 'import scipy'
  $ python -c 'import cvxopt'
  $ python -c 'import pyparsing'
  $ python -c 'import networkx'
  $ python -c 'import matplotlib; print matplotlib.__version__'

If an error message occurs, the package might not be visible on the
current path or may not be installed at all.  The last line should
cause the version of Matplotlib to be printed.  More or less that
approach can be used to easily find the installed versions for other
packages.  Try to install them yourself, or see
:ref:`troubleshoot-sec-label` below for help.

The default GR[1] synthesis tool used by TuLiP is implemented in `JTLV
<http://jtlv.ysaar.net/>`_. To use it, you must have Java version 1.6
(or later) installed.  The Java runtime environment is standard on
most platforms. You can check whether it's on the path and, if so,
determine the version using::

  $ java -version

Another supported synthesis tool is `gr1c
<http://scottman.net/2012/gr1c>`_. To see if it is on your path
and which version is installed, try::

  $ gr1c -V

For receding horizon problems, you will need a tool for checking satisfiability.
At present `CVC4 <http://cvc4.cs.nyu.edu/>`_ is supported.  Check that it is on
the shell path with::

  $ cvc4 -V

which will return the installed version number.

For problems on continuous state spaces, you will need methods for
manipulating convex polytopes, computing partitions, etc.  In the
recent release this is by default achieved with the TuLiP polytope
library which uses some convex optimization routines from CVXOPT. 
If you use this functionality, it is highly recommended---but not required---that you install `GLPK <http://www.gnu.org/s/glpk/>`_ (a fast linear
programming solver). Note that you need to install GLPK **before**
installing CVXOPT and follow the instructions in CVXOPT installation
to ensure it recognizes GLPK as a solver. If you are a `MacPorts
<http://www.macports.org/>`_ user, please note that MacPorts does not
do this linking automatically.


Once all of the above preparations are completed, you can install
TuLiP.  As with most `Distutils
<http://docs.python.org/install/index.html>`_-based packages,
installation proceeds with::

  $ python setup.py install

This script will also check for dependencies, i.e. look for NumPy,
CVXOPT, etc.


Other features (optional)
-------------------------

Here are some optional advanced features that require installing additional dependencies. None of them is required to run the examples that come with the toolbox. Only in some examples you will be prompted to choose whether you would like to use Gephi visualization. You can simply say no if you don't have it installed.


External solvers
````````````````

If you wish to use functions depending on `SPIN
<http://spinroot.com/spin/>`_ or `NuSMV <http://nusmv.fbk.eu/>`_, then
you must create a directory called ``solvers`` within the tulip
package and place there executables for (or links to) SPIN and
NuSMV. For instance, if you have TuLiP installed under
``/usr/local/lib/python2.7/site-packages``, the SPIN executable at
``/usr/bin/spin``, and the NuSMV executable at ``/usr/bin/NuSMV``,
then you would do ::

  $ sudo mkdir /usr/local/lib/python2.7/site-packages/tulip/solvers
  $ sudo ln -s /usr/bin/spin /usr/local/lib/python2.7/site-packages/tulip/solvers
  $ sudo ln -s /usr/bin/NuSMV /usr/local/lib/python2.7/site-packages/tulip/solvers


Gephi visualization
```````````````````

If you would like to use the new visualization and simulation functions that are part of release 0.2a, you need to download and install `Gephi <http://gephi.org/>`_. After making sure gephi is on the path, you can install tulip-AutomatonSimulation plugin for Gephi. To install the plugin, open Gephi, then the 'Tools' drop-down menu, 'Plugins', the
'Downloaded' tab, 'Add Plugins...', and browse to this folder to select the 'org-tulip-automatonsimulation.nbm' file. Also select the 'org-gephi-layout-plugin.nbm' file. It contains an updated layout module that's necessary for the AutomatonSimulation plugin to work [#f2]_. Then choose 'Install' and follow the instructions given.

To check if Gephi is on your path, try::

  $ which gephi

If this returns nothing, then you should add Gephi to your path. On Mac OS X, you can do this, for instance, by following the instructions from `this webpage <http://keito.me/tutorials/macosx_path>`_ where YOURPATHHERE should be set to the directory where Gephi is located on your machine. It is typically located under ``/Applications/gephi.app/Contents/MacOS/``.


.. _troubleshoot-sec-label:

Troubleshooting
---------------

Regarding installation of numerical computing packages (NumPy, etc.),
for the love of all that is good, please run tests to verify proper
behavior!  ...unless you use a very well established install method.
Nonetheless, unit testing is always good practice.

If you think the necessary packages are installed, but are unsure how
to debug Python, then consider the following tips.  To see the python
path, execute::

  $ python -c 'import sys; print "\n".join(sys.path)'

Each path searched is listed on a new line. You can augment this list
by appending locations (separated by ":") to the environment variable
**PYTHONPATH**.  To see what it's currently set to, and add a new path
to "/home/frodo/work", use::

  $ echo $PYTHONPATH
  $ export PYTHONPATH=$PYTHONPATH:/home/frodo/work

You may need to tweak the export statement depending on your terminal
shell.  All of my examples are tested with zsh (the Z shell).


Ubuntu (or Debian) GNU/Linux
````````````````````````````

To install the python package dependencies, try::

  $ sudo apt-get install python-numpy python-scipy python-matplotlib python-cvxopt python-networkx

Mac OS X
````````

For installing SciPy, NumPy, and Matplotlib, consider trying
`Scipy Superpack for Mac OSX
<http://fonnesbeck.github.com/ScipySuperpack/>`_ by Chris Fonnesbeck.


Microsoft Windows
`````````````````

For Windows users, type the above commands without "$" in the terminal. For example, check the version of your Python by typing::

  python -V

To check whether the packages has been installed, open a new terminal and try::

  python
  import numpy
  import scipy
  import cvxopt
  import networkx
  import matplotlib

If an error message occurs, the package might not be visible on the current path or may not be installed at all. When you cannot find a suitable package of NumPy, SciPy, CVXOPT, and Matplotlib for your system, consider trying `Unofficial Windows Binaries for Python Extension Packages <http://www.lfd.uci.edu/~gohlke/pythonlibs/>`_ by Christoph Gohlke. 

The package of Gr1c for Windows still cannot be found. But without this package, you can also run most TuLiP functions.

.. _venv-pydoc-sec-label:

virtualenv and pydoc
````````````````````

If you have installed TuLiP into a `virtualenv
<http://www.virtualenv.org/>`_-built environment, then the
documentation may not be visible through `pydoc
<http://docs.python.org/library/pydoc.html>`_ .  There are more
sophisticated ways to fix this, but an easy solution is to augment the
path used by pydoc with an alias.  E.g., suppose your username is
"frodo", you are running Python v2.6, and your virtual environment is
called "PY_scratch" under your home directory.  Then the appropriate
alias is similar to::

  $ alias pydoc='PYTHONPATH=$PYTHONPATH:/home/frodo/PY_scratch/lib/python2.6/site-packages/ pydoc'

To set this alias for every new terminal session, add the line to your
shell startup script; e.g., ``~/.bashrc`` for bash, or ``~/.zshrc``
for zsh.  To test it, try looking at the Automaton module by
entering::

  $ pydoc tulip.automaton


.. rubric:: Footnotes

.. [#f1] On Unix systems, in particular GNU/Linux and Mac OS X, the
         terminal shell treats ``~`` as a special symbol representing
         the home directory of the current user.

.. [#f2] The current Gephi build uses version 0.8.0.2 of the layout module;
         the version AutomatonSimulation plugin needs is 0.8.0.3. This extra
         step should become unnecessary once Gephi updates its release.

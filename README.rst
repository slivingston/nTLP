nTLP
====

**nTLP** is a permanent fork of TuLiP.  The design of nTLP is motivated
primarily by performance.  Relevant upstream changes will still be followed,
though major deviations include removal of dependencies on MPT, yices, and JTLV.

The citable URL is http://scottman.net/2013/nTLP


Installation
------------

In most cases, it suffices to::

  python setup.py install

To avoid checking for optional dependencies, add the option "nocheck"::

  python setup.py install nocheck

Detailed instructions, including notes about dependencies and troubleshooting,
are available at http://slivingston.github.io/nTLP/doc/install.html

The documentation sources are under ``doc/``.  A test suite is provided under
``tests/``.  Brief notes for using these are below.


Sphinx and Epydoc generated documentation
-----------------------------------------

There are two main sources of documentation outside the code.  The User's Guide
is built from sources under ``doc/`` using `Sphinx <http://sphinx.pocoo.org/>`_,
so try the usual ::

  make html

Note that a Windows build file, make.bat, was auto-generated at the
time of first initialising the docs configuration files (ca. 2011 May
8) but is not actively maintained.  It is included for convenience; please
consider Makefile to be the ground truth.  The API documentation is built using
`Epydoc <http://epydoc.sourceforge.net/>`_ and can also be built from the
``doc/`` directory, now by ::

  make api

Built copies of the User's Guide and API documentation for the most recent
release of nTLP are available online at

* http://slivingston.github.io/nTLP/doc/
* http://slivingston.github.io/nTLP/api/


Format specifications
---------------------

The directory ``doc/formats/`` contains definitions and documentation about data
and file formats used in the project.  The goal is to formalize specifications
expected in the code in a medium external to it.  Some of this is done in
docstrings, but ``formats/`` should provide single and normative points of
reference.


Testing
-------

Tests are performed using nose; see http://readthedocs.org/docs/nose/ for
details.  From the root of the source tree (i.e., where setup.py is located),
run::

  ./run_tests.py

to run all available tests.  Use the flag "-h" to see driver script options.

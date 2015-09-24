#!/usr/bin/env python
"""
Read data for a continuous transition system from a YAML file,
optionally visualize the partition, and save the result into a
tulipcon XML file.

Flags: -v  verbose;
       -p  generate figure using functions in polytope.plot module.


SCL; 6 June 2012.
"""

import numpy as np
import sys
from StringIO import StringIO

from tulip import conxml, discretize
import tulip.polytope.plot as pplot

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 5:
        print "Usage: autopart.py input.yaml [-p] [-v] [output.xml]"
        exit(1)

    if "-p" in sys.argv:
        show_pplot = True
        sys.argv.remove("-p")
    else:
        show_pplot = False

    if "-v" in sys.argv:
        verbose = 1
        sys.argv.remove("-v")
    else:
        verbose = 0

    if len(sys.argv) == 2:
        out_fname = sys.argv[1]+".xml"
    else:
        out_fname = sys.argv[2]

    (sys_dyn, initial_partition, N) = conxml.readYAMLfile(sys.argv[1], verbose=verbose)
    disc_dynamics = discretize.discretize(initial_partition, sys_dyn, N=N,
                                          verbose=verbose)

    with open(out_fname, "w") as f:
        f.write(conxml.dumpXMLtrans(sys_dyn, disc_dynamics, N,
                                    extra="This data file only contains a continuous transition system definition.",
                                    pretty=True))

    if show_pplot:
        pplot.plot_partition(disc_dynamics, plot_transitions=True)

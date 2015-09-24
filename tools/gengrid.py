#!/usr/bin/env python
"""
Generate uniform grid in the plane and output as YAML polytopes (vertices).

  Usage: gengrid.py [PREFIX] x0 x1 dx y0 y1 dy

where ``PREFIX`` is the basename to use in labeling cells of the
grid (default is "X"), ``x0`` and ``x1`` define the lower and upper
bounds on the first axis ("x-axis") axis, with step size of ``dx``,
and ``y0``, ``y1``, and ``dy`` have an entirely similar meaning for
the second axis.  For example, to create a grid covering with
integral steps and sides ranging from 0 to 10 along the first axis
and 0 to 6 along the second, use ::

  $ gengrid.py 0 10 1 0 6 1

SCL; 5 June 2012.
"""

import numpy as np
import sys


if __name__ == "__main__":
    if len(sys.argv) != 7 and len(sys.argv) != 8:
        print "Usage: gengrid.py [PREFIX] x0 x1 dx y0 y1 dy"
        exit(1)

    part_name = "gengrid_partition"
    if len(sys.argv) == 8:
        prefix = sys.argv[1]
        ind_offset = 1
    else:
        prefix = "X"
        ind_offset = 0
    cell_counter = 0
    dx = float(sys.argv[ind_offset+3])
    dy = float(sys.argv[ind_offset+6])
    print part_name+":"
    for x in np.arange(float(sys.argv[ind_offset+1]), float(sys.argv[ind_offset+2]), dx):
        for y in np.arange(float(sys.argv[ind_offset+4]), float(sys.argv[ind_offset+5]), dy):
            print "  "+prefix+str(cell_counter)+":\n    V: |"
            print "      "+str(x)+" "+str(y)
            print "      "+str(x+dx)+" "+str(y)
            print "      "+str(x+dx)+" "+str(y+dy)
            print "      "+str(x)+" "+str(y+dy)
            cell_counter += 1

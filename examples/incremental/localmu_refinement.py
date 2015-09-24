#!/usr/bin/env python
"""
Example of "local fixed point" algorithm for case of cell refinement.

DOT dumps of the strategy before and after patching are to the files
named tmp-orig.dot and tmp-pat.dot, respectively.


SCL; 19 Apr 2013.
"""

import numpy as np
import tulip.polytope as pc
import tulip.gridworld as gw
from tulip import gr1cint
from tulip.spec import GRSpec
from tulip.discretize import CtsSysDyn, discretize
import tulip.prop2part
from tulip.incremental import refine_cell

import tulip.polytope.plot as pplot
import matplotlib.pyplot as plt
from cProfile import Profile


DESC="""
2 6
IG   
   * G
"""
NONBOOL=False


def quadsplit(P):
    """Divide a rectangular (so, 2-dimensional) polytope into four pieces.
    """
    abs_tol = 1e-7
    V = pc.extreme(P)
    mV = np.mean(V, axis=0)
    low_bd = np.min(V, axis=0)
    high_bd = np.max(V, axis=0)
    ll = np.array([low_bd[0], low_bd[1]])  # lower-left
    ul = np.array([low_bd[0], high_bd[1]])  # upper-left
    ur = np.array([high_bd[0], high_bd[1]])  # upper-right
    lr = np.array([high_bd[0], low_bd[1]])  # lower-right
    left_steps = np.linspace(ll[1], ul[1], 5)
    left_points = np.outer(left_steps, np.ones(2))
    left_points.T[0] = ll[0]
    right_steps = np.linspace(lr[1], ur[1], 5)
    right_points = np.outer(right_steps, np.ones(2))
    right_points.T[0] = lr[0]
    return [pc.qhull(np.array([left_points[i], left_points[i+1],
                               right_points[i], right_points[i+1]])) for i in range(4)]

    #ml = np.mean([ul, ll], axis=0)  # mid-left
    #mr = np.mean([ur, lr], axis=0)  # mid-right
    #mu = np.mean([ul, ur], axis=0)  # mid-up
    #md = np.mean([ll, lr], axis=0)  # mid-down
    #return (pc.qhull(np.array([ul, mu, mV, ml])),  # upper-left cell
    #        pc.qhull(np.array([ll, ml, mV, md])),  # lower-left cell
    #        pc.qhull(np.array([ur, mr, mV, mu])),  # upper-right cell
    #        pc.qhull(np.array([lr, md, mV, mr])))  # lower-right cell


if __name__ == "__main__":
    mode_colors = {0:(1.,1.,.5), 1:(.5,1.,1.)}

    Y = gw.GridWorld(DESC, prefix="Y")
    initial_partition = Y.dumpPPartition(side_lengths=(1., 1.), offset=(0., 0.), nonbool=NONBOOL)

    # Problem parameters
    input_bound = .5
    uncertainty = 0.
    horizon = 10

    # Continuous dynamics
    A = np.array([[1., 0.],
                  [ 0., 1.]])
    B = np.array([[1., 0.],
                  [ 0., 1.]])
    E = np.array([[1,0],
                  [0,1]])
    U = pc.Polytope(np.array([[1., 0.],[-1., 0.], [0., 1.], [0., -1.]]),
                    input_bound*np.array([[1.],[1.],[1.],[1.]]))
    W = pc.Polytope(np.array([[1.,0.],[-1.,0.],[0.,1.],[0.,-1.]]),
                    uncertainty*np.array([1., 1., 1., 1.]))
    sys_dyn = CtsSysDyn(A,B,E,[],U,W)
    disc_dynamics = discretize(initial_partition, sys_dyn,
                               closed_loop=True, N=horizon, min_cell_volume=0.1,
                               verbose=2)
    pplot.plot_partition(disc_dynamics, plot_transitions=True)

    # Build specification in terms of countable gridworld
    spec = GRSpec()
    spec.importGridWorld(Y, nonbool=NONBOOL)
    spec.sys_safety = []

    # ...and then import discretization of continuous state space
    cells = spec.importDiscDynamics(disc_dynamics)
    cells = dict([(k,v.list_poly[0]) for (k,v) in cells.items()])

    # Check realizability and compute an automaton
    if gr1cint.check_realizable(spec, verbose=1):
        print "Realizable.  Synthesizing..."
    else:
        print "Not realizable."
        exit(-1)
    
    orig_prof = Profile()
    orig_prof.run("aut = gr1cint.synthesize(spec, verbose=1)")
    ind = -1
    while not hasattr(orig_prof.getstats()[ind].code, "co_name") or (orig_prof.getstats()[ind].code.co_name != "synthesize"):
        ind -= 1
    orig_time = orig_prof.getstats()[ind].totaltime

    aut.writeDotFileColor("tmp-orig.dot", hideZeros=True, mode_colors=mode_colors, node_attrib=True)

    # Perform substitution in specification by hand
    oldcell = "cellID_6"
    rP = quadsplit(cells[oldcell])
    refinements = dict([(oldcell, [("r"+str(i), rP[i]) for i in range(len(rP))])])
    spec.sys_vars.remove(oldcell)
    spec.sys_vars.extend(["r"+str(i) for i in range(len(rP))])
    subformula = " | ".join(["r"+str(i) for i in range(len(rP))])
    subformula_next = " | ".join(["r"+str(i)+"'" for i in range(len(rP))])
    oldcell_next = oldcell+"'"
    spec.sym2prop(props={oldcell_next:subformula_next})
    spec.sym2prop(props={oldcell:subformula})

    pat_prof = Profile()
    pat_prof.run("aut_patched = refine_cell(spec, aut, cells, refinements, radius=.5, nonbool=NONBOOL, verbose=1)")
    if aut_patched is None:
        print "Patching failed."
        exit(-1)

    ind = -1
    while not hasattr(pat_prof.getstats()[ind].code, "co_name") or (pat_prof.getstats()[ind].code.co_name != "refine_cell"):
        ind -= 1
    pat_time = pat_prof.getstats()[ind].totaltime

    aut_patched.writeDotFileColor("tmp-pat.dot", hideZeros=True, mode_colors=mode_colors, node_attrib=True)


    print "Original time: "+str(orig_time)
    print "Patching time: "+str(pat_time)

    print "Original automaton size: "+str(len(aut))
    print " Patched automaton size: "+str(len(aut_patched))


    # Depict the refined partition
    cells.update([("r"+str(i), rP[i]) for i in range(len(rP))])
    del cells[oldcell]
    refined_partition = tulip.prop2part.prop2part2(disc_dynamics.domain, cells)
    pplot.plot_partition(refined_partition)

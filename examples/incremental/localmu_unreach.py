#!/usr/bin/env python
"""
Example of "local fixed point" algorithm for case of an unreachable cell.

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
from tulip.incremental import unreachable_cell

import tulip.polytope.plot as pplot
from cProfile import Profile


DESC="""
5 5
IG*



    G
"""
NONBOOL=False

if __name__ == "__main__":
    mode_colors = {0:(1.,1.,.5), 1:(.5,1.,1.)}

    Y = gw.GridWorld(DESC, prefix="Y")
    initial_partition = Y.dumpPPartition(side_lengths=(1., 1.), offset=(0., 0.), nonbool=NONBOOL)
    #initial_partition.trans = initial_partition.adj.copy()
    #pplot.plot_partition(initial_partition, plot_transitions=True)

    # Problem parameters
    input_bound = .5
    uncertainty = 0.01
    horizon = 10

    # Continuous dynamics
    A = np.array([[1.1, 0.],
                  [ 0., 1.1]])
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
    if gr1cint.check_realizable(spec):
        print "Realizable.  Synthesizing..."
    else:
        print "Not realizable."
        exit(-1)
    
    orig_prof = Profile()
    orig_prof.run("aut = gr1cint.synthesize(spec)")
    ind = -1
    while not hasattr(orig_prof.getstats()[ind].code, "co_name") or (orig_prof.getstats()[ind].code.co_name != "synthesize"):
        ind -= 1
    orig_time = orig_prof.getstats()[ind].totaltime

    aut.writeDotFileColor("tmp-orig.dot", hideZeros=True, mode_colors=mode_colors, node_attrib=True)

    # Find a meaningful cell to block
    patch_success = False
    for node in aut.nodes_iter():
        blocked_state = aut.node[node]["state"]
        blocked_cell_name = [k for (k,v) in blocked_state.items() if v == 1][0]
        pat_prof = Profile()
        pat_prof.run("aut_patched = unreachable_cell(spec, aut, cells, blocked_cell_name, radius=.5, nonbool=NONBOOL, verbose=0)")
        if (aut_patched is not None) and (len(aut_patched.findAllAutPartState(blocked_state)) == 0):
            patch_success = True
            break
    if not patch_success:
        print "No meaningful cell to block was found."
        exit(-1)

    print "\nCell "+blocked_cell_name+" is now unreachable."
    ind = -1
    while not hasattr(pat_prof.getstats()[ind].code, "co_name") or (pat_prof.getstats()[ind].code.co_name != "unreachable_cell"):
        ind -= 1
    pat_time = pat_prof.getstats()[ind].totaltime

    aut_patched.writeDotFileColor("tmp-pat.dot", hideZeros=True, mode_colors=mode_colors, node_attrib=True)


    print "Original time: "+str(orig_time)
    print "Patching time: "+str(pat_time)

    print "Original automaton size: "+str(len(aut))
    print " Patched automaton size: "+str(len(aut_patched))

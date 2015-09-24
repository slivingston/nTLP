#!/usr/bin/env python
"""
Randomly generate, solve, modify, and then patch discrete unreachable
cell problems.  Results are pickled and saved to a file named

  simdata_localmu_unreach-YYYYMMDD-HHMMSS.pickle

where "YYYYMMDD-HHMMSS" is the timestamp at time of invocation.  The
pickled data is a list called "simdata", where each element is a tuple

  (Y_desc, troll_list, blocked_cell, result_code, globaltime, success_radius, success_patchingtime, total_patchingtime)

where
  - Y_desc : gridworld description string for the base problem, without trolls;
  - troll_list : argument given to add_trolls();
  - blocked_cell : cell in gridworld Y that is newly blocked and around which
                   patching occurs;
  - result_code :  0 if successfully patched,
                  -1 if we failed to patch (but modified game can still be won);
  - globaltime : time for global re-synthesis;
  - success_radius : if result_code=0, radius at which patching was successful;
  - success_patchingtime : if result_code=0, time to patch using success_radius;
  - total_patchingtime : if result_code=0, total time to try all radii, before
                         and including the successful one.

Gridworld cells can be represented using Boolean-valued variables or
variables over finite integral domains in terms of the GR(1) formula.
The default is to use integral variables.  To use Boolean variables
instead, change the NONBOOL flag to False (near line 48 of
stats_localmu_unreach_discrete.py).

Core simulation parameters can be adjusted near the top of the script.
E.g., (num_rows, num_cols) on line 61 defines the gridworld size.


SCL; 7 May 2013.
"""

import sys
import time
import numpy as np

import tulip.gridworld as gw
from tulip.spec import GRSpec
from tulip import gr1cint
from tulip.incremental import unreachable_cell_discrete

import cPickle
from cProfile import Profile


NONBOOL=True

if __name__ == "__main__":

    outfilename = "simdata_localmu_unreach-"+time.strftime("%Y%m%d-%H%M%S")+".pickle"
    print "Results will be saved to "+outfilename+"..."

    total_it = 20
    max_radius = 3
    (num_rows, num_cols) = (32, 32)
    find_blockedcell_timeout = 30  # seconds

    simdata = []
    num_it = 0
    while num_it < total_it:
        Y = gw.random_world((num_rows, num_cols),
                            wall_density=.2, num_init=1, num_goals=10,
                            prefix="Y")#, ensure_feasible=True, timeout=15)
        if not gr1cint.check_realizable(Y.spec()):
            print "Random gridworld is not deterministically realizable.  Trying again..."
            continue
        # if Y is None:
        #     print "Timed out while looking for feasible random gridworld."
        #     continue

        troll_list = []
        troll_list.append(((int(np.random.rand()*num_rows),
                            int(np.random.rand()*num_cols)), 1))
        while (not Y.isEmpty(troll_list[-1][0])) or (troll_list[-1][0] in Y.goal_list) or (troll_list[-1][0] in Y.init_list):
            troll_list[-1] = ((int(np.random.rand()*num_rows),
                               int(np.random.rand()*num_cols)), 1)

        (spec, moves_N) = gw.add_trolls(Y, troll_list, nonbool=NONBOOL)
        if not gr1cint.check_realizable(spec):
            print "o",
            continue

        orig_prof = Profile()
        orig_prof.run("aut = gr1cint.synthesize(spec, verbose=1)")
        ind = -1
        while not hasattr(orig_prof.getstats()[ind].code, "co_name") or (orig_prof.getstats()[ind].code.co_name != "synthesize"):
            ind -= 1
        orig_time = orig_prof.getstats()[ind].totaltime

        fbc_st = time.time()
        blocked_cell = (int(np.random.rand()*num_rows),
                        int(np.random.rand()*num_cols))
        while ((not Y.isEmpty(blocked_cell)) or (blocked_cell in Y.goal_list) or (blocked_cell in Y.init_list) or (len(aut.findAllAutPartState(Y.state(blocked_cell, nonbool=NONBOOL))) == 0)) and (time.time() - fbc_st <= find_blockedcell_timeout):
            blocked_cell = (int(np.random.rand()*num_rows),
                            int(np.random.rand()*num_cols))
        if time.time() - fbc_st > find_blockedcell_timeout:
            print "Timed out while looking for meaningful cell to block."
            continue

        Y_reglobal = Y.copy()
        Y_reglobal.setOccupied(blocked_cell)
        global_prof = Profile()
        (spec_reglobal, moves_N_reglobal) = gw.add_trolls(Y_reglobal, troll_list[:], nonbool=NONBOOL)
        global_prof.run("aut = gr1cint.synthesize(spec_reglobal, verbose=1)")
        ind = -1
        while not hasattr(global_prof.getstats()[ind].code, "co_name") or (global_prof.getstats()[ind].code.co_name != "synthesize"):
            ind -= 1
        globaltime = global_prof.getstats()[ind].totaltime

        if not gr1cint.check_realizable(spec_reglobal):
            print "b",
            continue
        num_it += 1

        print Y
        print troll_list
        print "Blocked cell: "+str(blocked_cell)

        st = time.time()
        for radius in range(1,max_radius+1):
            pat_prof = Profile()
            pat_prof.run("aut_patched = unreachable_cell_discrete(spec, aut, Y, blocked_cell, radius=radius, nonmetric_N=moves_N, nonbool=NONBOOL, verbose=2)")
            if aut_patched is not None:
                nbhd_radius = radius
                break
        total_patchingtime = time.time() - st
        if aut_patched is None:
            print "Patching failed"
            simdata.append((Y.dumps(), troll_list[:], blocked_cell, -1, globaltime, -1, -1, -1))
            continue
        

        ind = -1
        while not hasattr(pat_prof.getstats()[ind].code, "co_name") or (pat_prof.getstats()[ind].code.co_name != "unreachable_cell_discrete"):
            ind -= 1
        pat_time = pat_prof.getstats()[ind].totaltime

        simdata.append((Y.dumps(), troll_list[:], blocked_cell, 0, globaltime, nbhd_radius, pat_time, total_patchingtime))

        #print "Original time: "+str(orig_time)
        print "Patching time: "+str(pat_time)
        print "  Global time: "+str(globaltime)

        print "Saving...",
        with open(outfilename, "w") as f:
            cPickle.dump(simdata, f)
        print "Done."

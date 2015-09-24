#!/usr/bin/env python
"""
Results are pickled and saved to a file named

  simdata_hotswap_gw-YYYYMMDD-HHMMSS.pickle

where "YYYYMMDD-HHMMSS" is the timestamp at time of invocation in UTC
(which may differ from your local timezone).  The pickled data is a
list called "simdata", where each element is a tuple

  (Y_desc, troll_list, new_goals, orig_time, patch_times, re_times)

where

  - Y_desc : gridworld description string for the base problem,
             possibly without trolls;
  - troll_list : argument given to add_trolls(), possibly already
                 available via Y_desc;
  - new_goals : list of system goal cells that were added;
  - orig_time : time for synthesis before adding any goals;
  - patch_times : list of times required to patch on (add) new goal,
                  with order matching that of new_goals
  - re_times : list of times required to add new goal by global
               re-synthesis, with order matching that of new_goals

Experiment parameters can be adjusted near the top of the script.
E.g., (num_rows, num_cols) on line 48 defines the gridworld size.

Note that MGridWorld is still under development, hence the redundancy
of Y_desc and troll_list.


SCL; 2 Feb 2014.
"""

import sys
import time
import numpy as np

import tulip.gridworld as gw
from tulip.spec import GRSpec
from tulip import gr1cint

# Configure logging
import tulip
#tulip.log_setlevel("DEBUG")
tulip.log_echotofile()

import cPickle
from cProfile import Profile


if __name__ == "__main__":

    outfilename = "simdata_hotswap_gw-"+time.strftime("%Y%m%d-%H%M%S", time.gmtime())+".pickle"
    print "Results will be saved to "+outfilename+"..."

    # Experiment parameters
    total_it = 10
    (num_rows, num_cols) = (32, 32)
    num_trolls = 1
    num_goals = 10
    total_removed = 3


    simdata = []
    num_it = 0
    while num_it < total_it:
        Y = gw.random_world((num_rows, num_cols),
                            wall_density=0.2,
                            num_init=1, num_goals=num_goals, num_trolls=num_trolls,
                            prefix="Y")
        if isinstance(Y, gw.MGridWorld):
            troll_list = Y.troll_list
        else:
            troll_list = []
        if not gr1cint.check_realizable(Y.mspec()):
            print "o",
            continue

        new_goals = Y.goal_list[(num_goals-total_removed):]
        Y.goal_list = Y.goal_list[:(num_goals-total_removed)]

        print "Trial "+str(num_it)
        print Y
        print "Goal cells to be incrementally added: "+str(new_goals)

        spec = Y.mspec()
        orig_prof = Profile()
        orig_prof.run("aut = gr1cint.synthesize(spec)")
        ind = -1
        while not hasattr(orig_prof.getstats()[ind].code, "co_name") or (orig_prof.getstats()[ind].code.co_name != "synthesize"):
            ind -= 1
        orig_time = orig_prof.getstats()[ind].totaltime
        print "Original time:           "+str(orig_time)+"\n"

        patch_times = []
        re_times = []
        for i in range(len(new_goals)):
            print "Adding goal cell "+str(new_goals[i])+"..."

            patch_prof = Profile()
            patch_prof.run("aut_patched = gr1cint.add_sysgoal(spec, aut, Y[new_goals[i][0], new_goals[i][1]], metric_vars=spec.sys_vars)")
            ind = -1
            while not hasattr(patch_prof.getstats()[ind].code, "co_name") or (patch_prof.getstats()[ind].code.co_name != "add_sysgoal"):
                ind -= 1
            patch_times.append(patch_prof.getstats()[ind].totaltime)
            print "Patching time:           "+str(patch_times[-1])

            Y.goal_list.append(new_goals[i])
            spec = Y.mspec()
            re_prof = Profile()
            re_prof.run("aut = gr1cint.synthesize(spec)")
            ind = -1
            while not hasattr(re_prof.getstats()[ind].code, "co_name") or (re_prof.getstats()[ind].code.co_name != "synthesize"):
                ind -= 1
            re_times.append(re_prof.getstats()[ind].totaltime)
            print "Global resynthesis time: "+str(re_times[-1])+"\n"

        simdata.append((Y.dumps(), troll_list[:], new_goals[:], orig_time, patch_times[:], re_times[:]))
        print "Saving...",
        with open(outfilename, "w") as f:
            cPickle.dump(simdata, f)
        print "Done."

        # Increment trial count  (or "number of iterations")
        num_it += 1

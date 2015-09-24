#!/usr/bin/env python
"""
Small demo of rm_sysgoal applied to gridworlds.

SCL; 3 Feb 2014.
"""

import time
import sys
import tulip.gridworld as gw
from tulip.gr1cint import rm_sysgoal, synthesize
import matplotlib.pyplot as plt

import tulip
tulip.log_echotofile()


DESC="""
7 10
G        G
      *
I    **  *
  *      G
     *
*****
         G
"""

if __name__ == "__main__":
    mode_colors = {0:(1.,1.,.5), 1:(.5,1.,1.), 2:(1.,.5,1.), 3:(.5,.5,.5)}

    if "-h" in sys.argv:
        print "Usage: %s [R C]" % sys.argv[0]
        exit(1)

    if len(sys.argv) >= 3:
        (num_rows, num_cols) = (int(sys.argv[1]), int(sys.argv[2]))
    else:
        (num_rows, num_cols) = (30, 30)

    # Change the next line to troll_list = [] to obtain a non-adversarial example
    troll_list = [((0,1),1), ((0,6),1)]

    Z = gw.GridWorld(DESC, prefix="Z")
    (spec, moves_N) = gw.add_trolls(Z, troll_list)
    # Z = gw.random_world((num_rows, num_cols),
    #                     wall_density=0.2,
    #                     num_init=1,
    #                     num_goals=10)
    print spec.dumpgr1c()
    print Z.pretty(show_grid=True)
    print "The goals at cells "+str(Z.goal_list[-1])+" and "+str(Z.goal_list[-2])+" will be incrementally removed."

    aut = synthesize(spec)
    if aut is None:
        print "Original problem is not realizable."
        exit(0)
    aut.writeDotFileColor("tmp.dot", node_attrib=True, mode_colors=mode_colors,
                          env_vars=spec.env_vars, sys_vars=spec.sys_vars)

    # Remove the first goal
    delete_index = len(Z.goal_list)-1
    print "Removing system goal #"+str(delete_index)+"..."
    aut_patched = rm_sysgoal(spec, aut, delete_index, toollog=2)
    if aut_patched is None:
        print "Patching failed."
        exit(-1)
    else:
        aut_patched.writeDotFileColor("tmp-patched.dot", node_attrib=True, mode_colors=mode_colors,
                                      env_vars=spec.env_vars, sys_vars=spec.sys_vars)

    spec.sys_prog.pop()
    Z.goal_list.pop()

    # Remove the second goal
    delete_index = len(Z.goal_list)-1
    print "Removing system goal #"+str(delete_index)
    aut_patched = rm_sysgoal(spec, aut_patched, delete_index, toollog=2)
    if aut_patched is None:
        print "Second patching failed."
        exit(-1)
    else:
        aut_patched.writeDotFileColor("tmp-patched2.dot", node_attrib=True, mode_colors=mode_colors,
                                      env_vars=spec.env_vars, sys_vars=spec.sys_vars)


    Z.plot(font_pt=0, troll_list=troll_list)
    plt.savefig("tmp-Z.png")

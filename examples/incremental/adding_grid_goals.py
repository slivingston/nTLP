#!/usr/bin/env python
"""

SCL; 18 Apr 2013.
"""

import sys
import tulip.gridworld as gw
from tulip.gr1cint import add_sysgoal, synthesize
import matplotlib.pyplot as plt


DESC="""
7 10
G        G
      *
     **  *
  *      G
     *
*****
I        G
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

    troll_list = [((0,1),1), ((0,6),1)]

    Z = gw.GridWorld(DESC, prefix="Z")
    new_goals = [Z.goal_list.pop(), Z.goal_list.pop()]
    (spec, moves_N) = gw.add_trolls(Z, troll_list)
    # Z = gw.random_world((num_rows, num_cols),
    #                     wall_density=0.2,
    #                     num_init=1,
    #                     num_goals=10)
    print spec.dumpgr1c()
    print Z.pretty(show_grid=True)
    print "A new goal appears at cell "+str(new_goals[0]) + " and then at "+str(new_goals[1])

    #spec = Z.spec()
    aut = synthesize(spec)
    if aut is None:
        print "Original problem is not realizable."
        exit(0)
    aut.writeDotFileColor("tmp.dot", node_attrib=True, mode_colors=mode_colors,
                          env_vars=spec.env_vars, sys_vars=spec.sys_vars)

    # Add the first new goal
    aut_patched = add_sysgoal(spec, aut, Z[new_goals[0][0],new_goals[0][1]],
                              metric_vars=spec.sys_vars, verbose=1)
    if aut_patched is None:
        print "Patching failed."
    else:
        aut_patched.writeDotFileColor("tmp-patched.dot", node_attrib=True, mode_colors=mode_colors,
                                      env_vars=spec.env_vars, sys_vars=spec.sys_vars)


    # Add the second new goal
    spec.sys_prog.append(Z[new_goals[0][0],new_goals[0][1]])
    aut_patched2 = add_sysgoal(spec, aut_patched, Z[new_goals[1][0],new_goals[1][1]],
                               metric_vars=spec.sys_vars, verbose=1)
    if aut_patched2 is None:
        print "Patching failed."
    else:
        aut_patched2.writeDotFileColor("tmp-patched2.dot", node_attrib=True, mode_colors=mode_colors,
                                       env_vars=spec.env_vars, sys_vars=spec.sys_vars)

    Z.plot(font_pt=0, troll_list=troll_list)
    plt.savefig("tmp-Z.png")

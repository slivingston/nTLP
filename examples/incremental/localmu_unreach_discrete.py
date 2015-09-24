#!/usr/bin/env python
"""
Example of "local fixed point" algorithm for case of an unreachable
cell in an entirely discrete problem.

DOT dumps of the strategy before and after patching are to the files
named tmp-orig.dot and tmp-pat.dot, respectively.


SCL; 18 Apr 2013.
"""

import tulip.gridworld as gw
from tulip import gr1cint
from tulip.incremental import unreachable_cell_discrete

from cProfile import Profile


# DESC="""
# 7 10
#          G
#       *
#      **  *
#   *
#      *
# *****
# I        G
# """
DESC="""
2 20
IG
                   G
"""
NONBOOL=False

if __name__ == "__main__":
    mode_colors = {0:(1.,1.,.5), 1:(.5,1.,1.)}

    Y = gw.GridWorld(DESC, prefix="Y")
    print Y

    (spec, moves_N) = gw.add_trolls(Y, [((1,16),1)], nonbool=NONBOOL)

    orig_prof = Profile()
    orig_prof.run("aut = gr1cint.synthesize(spec)")
    ind = -1
    while not hasattr(orig_prof.getstats()[ind].code, "co_name") or (orig_prof.getstats()[ind].code.co_name != "synthesize"):
        ind -= 1
    orig_time = orig_prof.getstats()[ind].totaltime

    aut.writeDotFileColor("tmp-orig.dot", hideZeros=True, mode_colors=mode_colors, node_attrib=True)

    pat_prof = Profile()
    pat_prof.run("aut_patched = unreachable_cell_discrete(spec, aut, Y, (0,8), radius=2, nonmetric_N=moves_N, nonbool=NONBOOL, verbose=2)")
    if aut_patched is None:
        print "Patching failed"
        exit(-1)

    ind = -1
    while not hasattr(pat_prof.getstats()[ind].code, "co_name") or (pat_prof.getstats()[ind].code.co_name != "unreachable_cell_discrete"):
        ind -= 1
    pat_time = pat_prof.getstats()[ind].totaltime

    aut_patched.writeDotFileColor("tmp-pat.dot", hideZeros=True, mode_colors=mode_colors, node_attrib=True)


    print "Original time: "+str(orig_time)
    print "Patching time: "+str(pat_time)

    print "Original automaton size: "+str(len(aut))
    print " Patched automaton size: "+str(len(aut_patched))

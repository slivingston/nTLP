#!/usr/bin/env python
"""
Usage: solverand_spin.py [H W]

will generate a random deterministic gridworld problem of the height H
and width W (default is 5 by 10), try to solve it using the SPIN
interface and, if realizable, dump a DOT file named "random_grid.dot"
depicting the strategy automaton.  Example usage for 3 by 5 size is

  $ ./solverand_spin.py 3 5

The resulting PNG image built by dot is in the file named
"random_grid.png".  Note that other temporary files also have the base
name "random_grid".
"""

import sys, time
import tulip.gridworld as gw
from tulip import gr1cint
from tulip import solver
import tulip.automaton as automaton
from subprocess import call

if __name__ == "__main__":
    if len(sys.argv) > 3 or "-h" in sys.argv:
        print "Usage: solverand.py [H W]"
        exit(1)

    if len(sys.argv) >= 3:
        (height, width) = (int(sys.argv[1]), int(sys.argv[2]))
    else:
        (height, width) = (5, 10)

    Z = gw.random_world((height, width),
                        wall_density=0.2,
                        num_init=1,
                        num_goals=2)
    print Z
    
    start = time.time()
    gr1spec = Z.spec(nonbool=False)
    # generate SMV spec from discrete transitions
    print "Generating transition system"
    pp = Z.discreteTransitionSystem(nonbool=False)

    print "Assembling progress specification"
    sp = ["[]<>(" + x + ")" for x in gr1spec.sys_prog]
    initials = { k : True for k in [Z[x] for x in Z.init_list]}
    slvi = solver.generateSolverInput({}, ["", " & ".join(sp)],
                                      {}, pp, "random_grid.pml", initials,
                                      "SPIN")

    print "Computing strategy"
    if slvi.solve("random_grid.aut"):
        print "Writing automaton"
        aut = slvi.automaton()
        solver.restore_propositions(aut, pp)
        aut.stripNames()

        print Z.pretty(show_grid=True, path=gw.extract_path(aut))
        aut.writeDotFile("random_grid.dot", hideZeros=True)
        call("dot random_grid.dot -Tpng -o random_grid.png".split())
    else:
        print "Strategy cannot be realized."
    print "SPIN solved in " + str(time.time() - start) + "s"

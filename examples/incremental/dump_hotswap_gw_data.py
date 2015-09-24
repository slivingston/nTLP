#!/usr/bin/env python
"""
Parse and present simulation data generated from
stats_hotswap_gw.py
Try calling this script with "-h" for help.


SCL; 2 Feb 2014.
"""

import sys
import cPickle
import matplotlib.pyplot as plt

import tulip.gridworld as gw


def trial_print(Y_desc, troll_list, new_goals, orig_time, patch_times, re_times):
    Y = gw.MGridWorld(Y_desc)
    print Y
    print "Troll-list:", troll_list
    print "Goals added incrementally:", new_goals
    print "Original time: "+str(orig_time)+"\n"
    for i in range(len(new_goals)):
        print "Adding goal "+str(i)+": "+str(new_goals[i])
        print "\tpatching time:   ", patch_times[i]
        print "\tresynthesis time:", re_times[i]


if __name__ == "__main__":
    if ("-h" in sys.argv) or (len(sys.argv) < 2):
        print """Usage: %s [-hrp] FILE [TRIAL]

  -h  Display this help message
  -r  raw dump, suitable for reading with numpy.loadtxt
  -p  draw pretty figure; requires TRIAL

FILE is the simulation data file, and if given, TRIAL is the trial number
(in order found in FILE) about which to print details.
""" % sys.argv[0]
        exit(1)

    if "-r" in sys.argv:
        raw_dump = True
        sys.argv.remove("-r")
    else:
        raw_dump = False

    if "-p" in sys.argv:
        draw_fig = True
        sys.argv.remove("-p")
    else:
        draw_fig = False

    with open(sys.argv[1], "r") as f:
        simdata = cPickle.load(f)

    if raw_dump:
        # Print in form readable by numpy.loadtxt()
        for (Y_desc, troll_list, new_goals, orig_time, patch_times, re_times) in simdata:
            print str(len(new_goals))+" "+str(orig_time)+" "+" ".join([str(t) for t in patch_times])+" "+" ".join([str(t) for t in re_times])
        exit(0)

    print "Total trials:", len(simdata)
    if len(sys.argv) >= 3:
        if int(sys.argv[2]) < 0 or int(sys.argv[2]) > len(simdata)-1:
            print "trial number outside bounds (max is "+str(len(simdata)-1)+")"
            exit(1)
        print "### Trial number", int(sys.argv[2]), "###"
        trial_print(*simdata[int(sys.argv[2])])
        print "\n### gridworld description string ###"
        print simdata[int(sys.argv[2])][0]
        Y = gw.MGridWorld(simdata[int(sys.argv[2])][0])
        troll_list = simdata[int(sys.argv[2])][1]
        if draw_fig:
            Y.plot(font_pt=0, show_grid=True, troll_list=troll_list)
            plt.show()
    else:
        # Print summary of file
        counter = -1
        for (Y_desc, troll_list, new_goals, orig_time, patch_times, re_times) in simdata:
            counter += 1
            print "### Trial number", counter, "###"
            trial_print(Y_desc, troll_list, new_goals, orig_time, patch_times, re_times)
            print "="*70

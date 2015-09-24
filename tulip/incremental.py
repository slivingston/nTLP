# Copyright (c) 2012, 2013 by California Institute of Technology
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# 3. Neither the name of the California Institute of Technology nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL CALTECH
# OR THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
"""
Implementations of various incremental synthesis and patching algorithms.

In some cases, the core of the algorithm is implemented elsewhere,
while a TuLiP-flavored wrapper is provided here.
"""

import polytope as pc
from gr1cint import patch_localfixpoint


def unreachable_cell_discrete(spec, aut, Y, blocked_cell, radius=1, nonmetric_N=[], nonbool=True, verbose=0):
    """Patch strategy when a cell has become unreachable in discrete problem.
    
    @type spec: L{GRSpec}
    @param spec: GR(1) specification.
    @type aut: L{Automaton}
    @param aut: original strategy.
    @type Y: L{GridWorld<gridworld.GridWorld>}

    @param blocked_cell: (i,j) in gridworld; supports negative indices.
    @param radius: radius with which to determine neighborhood around
             the unreachable cell, measured using infinity-norm.

    @param nonmetric_N: a list of lists of partial states (where
             "state" is given as a dictionary with keys of variable
             names), where each element of nonmetric_N corresponds to
             possible values of a subset of problem variables, the
             product of which is to be taken with those of the given
             gridworld Y.  This can be used for including in the
             "neighborhood" N the domains of variables over which no
             distance is defined (hence the name).

    @rtype: Automaton or None
    @return: Returns patched strategy, or None if unrealizable (or error).
    """
    N = []
    (Y_num_rows, Y_num_cols) = Y.size()
    if len(blocked_cell) != len(Y.size()):
        raise ValueError("malformed gridworld blocked_cell key.")
    if blocked_cell[0] < -Y_num_rows or blocked_cell[1] < -Y_num_cols or blocked_cell[0] >= Y_num_rows or blocked_cell[1] >= Y_num_cols:
        raise ValueError("gridworld blocked_cell is out of bounds.")
    if blocked_cell[0] < 0:
        blocked_cell = (Y_num_rows+blocked_cell[0], blocked_cell[1])
    if blocked_cell[1] < 0:
        blocked_cell = (blocked_cell[0], Y_num_cols+blocked_cell[1])
    for i_offset in range(-radius, radius+1):
        if blocked_cell[0]+i_offset < 0 or blocked_cell[0]+i_offset >= Y_num_rows:
            continue
        for j_offset in range(-radius, radius+1):
            if blocked_cell[1]+j_offset < 0 or blocked_cell[1]+j_offset >= Y_num_cols:
                continue
            N.append(Y.state((blocked_cell[0]+i_offset, blocked_cell[1]+j_offset), nonbool=nonbool))

    # Take product with states as provided in nonmetric_N, which are
    # possible independent of Y.
    if len(nonmetric_N) == 0:
        final_N = N
    else:
        final_N = []
        for dep_move in N:
            final_N.append(dep_move.copy())
        for mN in nonmetric_N:
            next_final_N = []
            for indep_move in mN:
                for fN in final_N:
                    next_final_N.append(fN.copy())
                    next_final_N[-1].update(indep_move)
            final_N = [d.copy() for d in next_final_N]

    return patch_localfixpoint(spec, aut, final_N, [("blocksys", [Y.state(blocked_cell, nonbool=nonbool).copy()])], verbose=verbose)


def unreachable_cell(spec, aut, cells, blocked_cell_name, radius=1, abs_tol=1e-7, nonbool=False, verbose=0):
    """Patch strategy when a cell has become unreachable.

    This function finds a neighborhood by conservatively approximating
    (larger than exact) the blocked polytope inflated by the given
    radius and finding intersections with other polytopes in the given
    "cells" dictionary.

    The state is assumed to be entirely determined by occupancy of a
    cell in the "cells" dictionary.
    
    @type spec: L{GRSpec}
    @param spec: GR(1) specification.
    @type aut: L{Automaton}
    @param aut: original strategy.

    @param cells: dictionary describing the cell decomposition; keys
             are variable names (given as strings), and values are
             corresponding polytopes (instances of Polytope class).

    @type blocked_cell_name: string

    @param radius: radius with which to determine neighborhood around
             the unreachable cell.

    @rtype: Automaton or None
    @return: Returns patched strategy, or None if unrealizable (or error).
    """
    if nonbool:
        raise ValueError("incremental.unreachable_cell currently only supports boolean-based decompositions")

    statebase = dict([(k,0) for k in cells.keys()])

    inflated_bcell = cells[blocked_cell_name].copy()
    inflated_bcell.clear()
    inflated_bcell.b += radius

    N = []
    for (c,p) in cells.items():
        if pc.volume(pc.intersect(inflated_bcell, p, abs_tol=abs_tol)) > abs_tol:
            if verbose > 0:
                print "unreachable_cell: Including cell \""+c+"\" in N."
            N.append(statebase.copy())
            N[-1][c] = 1

    blocked_state = statebase.copy()
    blocked_state[blocked_cell_name] = 1
    return patch_localfixpoint(spec, aut, N, [("blocksys", [blocked_state])], verbose=verbose)


def refine_cell(spec, aut, cells, refinements, radius=1, abs_tol=1e-7, nonbool=False, verbose=0):
    """Patch strategy after partition refinement.

    Note that keys of the given refinements dictionary (i.e., names of
    cell variables that were refined) should not be in spec.  In other
    words, the specification should already incorporate the results of
    refinement.  By contrast, the given automaton aut should *not*
    contain any of the refining cells.

    @param cells: dictionary describing the cell decomposition before
             refinement; keys are variable names (given as strings),
             and values are corresponding polytopes (instances of
             Polytope class).

    @param refinements: dictionary describing the refinement to
             perform; keys are names of cells to be refined, and
             values are lists of pairs where for each pair (n,p), n is
             the name (string) of a refining cell and p is a Polytope
             defining it.
    """
    if nonbool:
        raise ValueError("incremental.refine_cell currently only supports boolean-based decompositions")

    spec.sys_vars.extend(refinements.keys())
    new_cell_names = []
    for v in refinements.values():
        for v_rcell in v:
            if v_rcell[0] not in new_cell_names:
                new_cell_names.append(v_rcell[0])
    for node in aut.states:
        node.state.update([(k,0) for k in new_cell_names])

    # Copy cell dict and expand to include refining cells
    cells = dict([(k,v.copy()) for (k,v) in cells.items()])
    for v in refinements.values():
        for v_rcell in v:
            cells[v_rcell[0]] = v_rcell[1].copy()

    # To make state vector construction easier, make a non-state of all zeros
    statebase = dict([(k,0) for k in cells.keys()])

    N = []
    for blocked_name in refinements.keys():
        inflated_bcell = cells[blocked_name].copy()
        inflated_bcell.clear()
        inflated_bcell.b += radius
        for (c,p) in cells.items():
            if pc.volume(pc.intersect(inflated_bcell, p, abs_tol=abs_tol)) > abs_tol:
                if verbose > 0:
                    print "refine_cell: Including cell \""+c+"\" in N."
                N.append(statebase.copy())
                N[-1][c] = 1

    blocked_states = []
    for k in refinements.keys():
        blocked_states.append(statebase.copy())
        blocked_states[-1][k] = 1
    
    aut_patched = patch_localfixpoint(spec, aut, N, [("blocksys", [bstate]) for bstate in blocked_states], verbose=verbose)
    if aut_patched is None:
        return None

    for node in aut_patched.states:
        for k in refinements.keys():
            del node.state[k]
    for k in refinements.keys():
        spec.sys_vars.remove(k)
    return aut_patched

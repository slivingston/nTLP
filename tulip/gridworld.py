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
Routines for working with gridworlds.

Note (24 June 2012): Several pieces of source code are taken or
derived from btsynth; see http://scottman.net/2012/btsynth
"""

import itertools
import time
import copy
import numpy as np
import matplotlib.patches as mpl_patches
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import matplotlib.cm as mpl_cm

import polytope as pc
from prop2part import prop2part2, PropPreservingPartition
from spec import GRSpec


class GridWorld:
    def __init__(self, gw_desc=None, prefix="Y"):
        """Load gridworld described in given string, or make empty instance.

        @param gw_desc: String containing a gridworld description, or
                 None to create an empty instance.
        @param prefix: String to be used as prefix for naming
                 gridworld cell variables.
        """
        if gw_desc is not None:
            self.loads(gw_desc)
        else:
            self.W = None
            self.init_list = []
            self.goal_list = []
        self.prefix = prefix
        self.offset = (0, 0)

    def __eq__(self, other):
        """Test for equality.

        Does not compare prefixes of cell variable names.
        """
        if self.W is None and other.W is None:
            return True
        if self.W is None or other.W is None:
            return False  # Only one of the two is undefined.
        if self.size() != other.size():
            return False
        if np.all(self.W != other.W):
            return False
        if self.goal_list != other.goal_list:
            return False
        if self.init_list != other.init_list:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.pretty(show_grid=True)

    def __getitem__(self, key, next=False, nonbool=True):
        """Return variable name corresponding to this cell.

        Supports negative wrapping, e.g., if Y is an instance of
        GridWorld, then Y[-1,-1] will return the variable name of the
        cell in the bottom-right corner, Y[0,-1] the name of the
        top-right corner cell, etc.  As usual in Python, you can only
        wrap around once.

        @param next: Use the primed (i.e., state at next time step)
                 form of the variable.
        @param nonbool: If True, then use gr1c support for nonboolean
                 variable domains.
        """
        if self.W is None:
            raise ValueError("Gridworld is empty; no names available.")
        if len(key) != len(self.W.shape):
            raise ValueError("malformed gridworld key.")
        if key[0] < -self.W.shape[0] or key[1] < -self.W.shape[1] or key[0] >= self.W.shape[0] or key[1] >= self.W.shape[1]:
            raise ValueError("gridworld key is out of bounds.")
        if key[0] < 0:
            key = (self.W.shape[0]+key[0], key[1])
        if key[1] < 0:
            key = (key[0], self.W.shape[1]+key[1])
        if nonbool:
            if next:
                return "(("+str(self.prefix)+"_r' = "+str(key[0] + self.offset[0])+") & ("+str(self.prefix)+"_c' = "+str(key[1] + self.offset[1])+"))"
            else:
                return "(("+str(self.prefix)+"_r = "+str(key[0] + self.offset[0])+") & ("+str(self.prefix)+"_c = "+str(key[1] + self.offset[1])+"))"
        else:
            out = str(self.prefix)+"_"+str(key[0] + self.offset[0])+"_"+str(key[1] + self.offset[1])
            if next:
                return out+"'"
            else:
                return out

    def __copy__(self):
        return GridWorld(self.dumps(), prefix=self.prefix)

    def copy(self):
        return self.__copy__()


    def state(self, key, offset=(0, 0), nonbool=True):
        """Return dictionary form of state with keys of variable names.

        Supports negative indices for key, e.g., as in __getitem__.

        The offset argument is motivated by the use-case of multiple
        agents whose moves are governed by separate "gridworlds" but
        who interact in a shared space; with an offset, we can make
        "sub-gridworlds" and enforce rules like mutual exclusion.

        @param nonbool: If True, then use gr1c support for nonboolean
                 variable domains.
        """
        if self.W is None:
            raise ValueError("Gridworld is empty; no cells exist.")
        if len(key) != len(self.W.shape):
            raise ValueError("malformed gridworld key.")
        if key[0] < -self.W.shape[0] or key[1] < -self.W.shape[1] or key[0] >= self.W.shape[0] or key[1] >= self.W.shape[1]:
            raise ValueError("gridworld key is out of bounds.")
        if key[0] < 0:
            key = (self.W.shape[0]+key[0], key[1])
        if key[1] < 0:
            key = (key[0], self.W.shape[1]+key[1])
        output = dict()
        if nonbool:
            output[self.prefix+"_r"] = key[0]+offset[0]
            output[self.prefix+"_c"] = key[1]+offset[1]
        else:
            for i in range(self.W.shape[0]):
                for j in range(self.W.shape[1]):
                    output[self.prefix+"_"+str(i+offset[0])+"_"+str(j+offset[1])] = 0
            output[self.prefix+"_"+str(key[0]+offset[0])+"_"+str(key[1]+offset[1])] = 1
        return output


    def isEmpty(self, coord, extend=False):
        """Is cell at coord empty?

        @param coord: (row, column) pair; supports negative indices.
        @param extend: If True, then do not wrap indices and treat any
                 cell outside the grid as being occupied.
        """
        if self.W is None:
            raise ValueError("Gridworld is empty; no cells exist.")
        if len(coord) != len(self.W.shape):
            raise ValueError("malformed gridworld coord.")
        if extend and (coord[0] < 0 or coord[1] < 0
                       or coord[0] > self.W.shape[0]-1
                       or coord[1] > self.W.shape[1]-1):
            return False
        if self.W[coord[0]][coord[1]] == 0:
            return True
        else:
            return False

    def setOccupied(self, coord):
        """Mark cell at coord as statically (permanently) occupied."""
        if self.W is None:
            raise ValueError("Gridworld is empty; no cells exist.")
        self.W[coord[0]][coord[1]] = 1

    def setEmpty(self, coord):
        """Mark cell at coord as empty."""
        if self.W is None:
            raise ValueError("Gridworld is empty; no cells exist.")
        self.W[coord[0]][coord[1]] = 0


    def isReachable(self, start, stop):
        """Decide whether there is a path from start cell to stop.

        Assume the gridworld is 4-connected.

        @param start: (row, column) pair; supports negative indices.
        @param stop: same as start argument.

        @return: True if there is a path, False otherwise.
        """
        # Check input values and handle negative coordinates
        if self.W is None:
            raise ValueError("Gridworld is empty; no names available.")

        if len(start) != len(self.W.shape):
            raise ValueError("malformed gridworld start coordinate.")
        if start[0] < -self.W.shape[0] or start[1] < -self.W.shape[1] or start[0] >= self.W.shape[0] or start[1] >= self.W.shape[1]:
            raise ValueError("gridworld start coordinate is out of bounds.")
        if start[0] < 0:
            start = (self.W.shape[0]+start[0], start[1])
        if start[1] < 0:
            start = (start[0], self.W.shape[1]+start[1])

        if len(stop) != len(self.W.shape):
            raise ValueError("malformed gridworld stop coordinate.")
        if stop[0] < -self.W.shape[0] or stop[1] < -self.W.shape[1] or stop[0] >= self.W.shape[0] or stop[1] >= self.W.shape[1]:
            raise ValueError("gridworld stop coordinate is out of bounds.")
        if stop[0] < 0:
            stop = (self.W.shape[0]+stop[0], stop[1])
        if stop[1] < 0:
            stop = (stop[0], self.W.shape[1]+stop[1])

        # Quick sanity check
        if not (self.isEmpty(start) and self.isEmpty(stop)):
            return False

        # Similar to depth-first search
        OPEN = [start]
        CLOSED = []
        while len(OPEN) > 0:
            current = OPEN.pop()
            if current == stop:
                return True
            for (i,j) in [(1,0), (-1,0), (0,1), (0,-1)]:
                if (current[0]+i < 0 or current[0]+i >= self.W.shape[0]
                    or current[1]+j < 0 or current[1]+j >= self.W.shape[1]):
                    continue
                if self.isEmpty((current[0]+i, current[1]+j)) and (current[0]+i, current[1]+j) not in CLOSED and (current[0]+i, current[1]+j) not in OPEN:
                    OPEN.append((current[0]+i, current[1]+j))
            CLOSED.append(current)
        return False


    def plot(self, font_pt=18, show_grid=False, grid_width=2, troll_list=[]):
        """Draw figure depicting this gridworld.

        Figure legend (symbolic form in parenthesis):
          - "I" ('m+') : possible initial position;
          - "G" ('r*') : goal;
          - "E" ('gx') : goal of a troll; its extent is indicated by gray cells

        @param font_pt: size (in points) for rendering text in the
                 figure.  If 0, then use symbols instead (see legend above).
        @param troll_list: ...same as the argument with the same name
                 given to L{add_trolls}.
        """
        W = self.W.copy()
        W = np.ones(shape=W.shape) - W
        fig = plt.figure()
        ax = plt.subplot(111)
        plt.imshow(W, cmap=mpl_cm.gray, aspect="equal", interpolation="nearest",
                   vmin=0., vmax=1.)
        xmin, xmax, ymin, ymax = plt.axis()
        x_steps = np.linspace(xmin, xmax, W.shape[1]+1)
        y_steps = np.linspace(ymin, ymax, W.shape[0]+1)
        if show_grid:
            for k in x_steps:
                plt.plot([k, k], [ymin, ymax], 'k-', linewidth=grid_width)
            for k in y_steps:
                plt.plot([xmin, xmax], [k, k], 'k-', linewidth=grid_width)
            plt.axis([xmin, xmax, ymin, ymax])
        for p in self.init_list:
            if font_pt > 0:
                plt.text(p[1], p[0], "I", size=font_pt)
            else:
                plt.plot(p[1], p[0], 'm+')
        for p in self.goal_list:
            if font_pt > 0:
                plt.text(p[1], p[0], "G", size=font_pt)
            else:
                plt.plot(p[1], p[0], 'r*')
        for (center, radius) in troll_list:
            if font_pt > 0:
                plt.text(center[1], center[0], "E", size=font_pt)
            else:
                plt.plot(center[1], center[0], 'gx')
            if center[0] >= W.shape[0] or center[0] < 0 or center[1] >= W.shape[1] or center[1] < 0:
                raise ValueError("troll center is outside of gridworld")
            t_offset = (max(0, center[0]-radius), max(0, center[1]-radius))
            t_size = [center[0]-t_offset[0]+radius+1, center[1]-t_offset[1]+radius+1]
            if t_offset[0]+t_size[0] >= W.shape[0]:
                t_size[0] = W.shape[0]-t_offset[0]
            if t_offset[1]+t_size[1] >= W.shape[1]:
                t_size[1] = W.shape[1]-t_offset[1]
            t_size = (t_size[0], t_size[1])
            for i in range(t_size[0]):
                for j in range(t_size[1]):
                    if self.W[i+t_offset[0]][j+t_offset[1]] == 0:
                        ax.add_patch(mpl_patches.Rectangle((x_steps[j+t_offset[1]], y_steps[W.shape[0]-(i+t_offset[0])]),1,1, color=(.8,.8,.8)))
        plt.axis([xmin, xmax, ymin, ymax])

    def pretty(self, show_grid=False, line_prefix="", path=[], goal_order=False, troll_list=[]):
        """Return pretty-for-printing string.

        @param show_grid: If True, then grid the pretty world and show
                 row and column labels along the outer edges.
        @param line_prefix: prefix each line with this string.
        @param troll_list: ...same as the argument with the same name
                 given to L{add_trolls}.
        """
        compress = lambda p: [ p[n] for n in range(len(p)-1) if p[n] != p[n+1] ]
        # See comments in code for the method loads regarding values in W
        if self.W is None:
            return ""
        
        # LEGEND:
        #  * - wall (as used in original world matrix definition);
        #  G - goal location;
        #  I - possible initial location.
        #  E - goal of a troll (if troll_list is nonempty);
        #      its extent is indicated by "+"
        out_str = line_prefix
        def direct(c1, c2):
            (y1, x1) = c1
            (y2, x2) = c2
            if x1 > x2:
                return "<"
            elif x1 < x2:
                return ">"
            elif y1 > y2:
                return "^"
            elif y1 < y2:
                return "v"
            else: # c1 == c2
                return "."
        # Temporarily augment world map W to indicate troll positions
        for (center, radius) in troll_list:
            if self.W[center[0]][center[1]] == 0:
                self.W[center[0]][center[1]] = -1
            if center[0] >= self.W.shape[0] or center[0] < 0 or center[1] >= self.W.shape[1] or center[1] < 0:
                raise ValueError("troll center is outside of gridworld")
            t_offset = (max(0, center[0]-radius), max(0, center[1]-radius))
            t_size = [center[0]-t_offset[0]+radius+1, center[1]-t_offset[1]+radius+1]
            if t_offset[0]+t_size[0] >= self.W.shape[0]:
                t_size[0] = self.W.shape[0]-t_offset[0]
            if t_offset[1]+t_size[1] >= self.W.shape[1]:
                t_size[1] = self.W.shape[1]-t_offset[1]
            t_size = (t_size[0], t_size[1])
            for i in range(t_size[0]):
                for j in range(t_size[1]):
                    if self.W[i+t_offset[0]][j+t_offset[1]] == 0:
                        self.W[i+t_offset[0]][j+t_offset[1]] = -2
        if show_grid:
            out_str += "  " + "".join([str(k).rjust(2) for k in range(self.W.shape[1])]) + "\n"
        else:
            out_str += "-"*(self.W.shape[1]+2) + "\n"
        #if path:
        #    path = compress(path)
        for i in range(self.W.shape[0]):
            out_str += line_prefix
            if show_grid:
                out_str += "  " + "-"*(self.W.shape[1]*2+1) + "\n"
                out_str += line_prefix
                out_str += str(i).rjust(2)
            else:
                out_str += "|"
            for j in range(self.W.shape[1]):
                if show_grid:
                    out_str += "|"
                if self.W[i][j] == 0:
                    if (i,j) in self.init_list:
                        out_str += "I"
                    elif (i,j) in self.goal_list:
                        if goal_order:
                            out_str += str(self.goal_list.index((i,j)))
                        else:
                            out_str += "G"
                    elif (i,j) in path:
                        indices = (n for (n,c) in enumerate(path) if c == (i,j))
                        for x in indices:
                            d = direct((i,j), path[(x+1) % len(path)])
                            if d != ".":
                                break
                        out_str += d
                    else:
                        out_str += " "
                elif self.W[i][j] == 1:
                    out_str += "*"
                elif self.W[i][j] == -1:
                    out_str += "E"
                elif self.W[i][j] == -2:
                    out_str += "+"
                else:
                    raise ValueError("Unrecognized internal world W encoding.")
            out_str += "|\n"
        out_str += line_prefix
        if show_grid:
            out_str += "  " + "-"*(self.W.shape[1]*2+1) + "\n"
        else:
            out_str += "-"*(self.W.shape[1]+2) + "\n"
        # Delete temporary mark-up to world map W
        self.W[self.W == -1] = 0
        self.W[self.W == -2] = 0
        return out_str

    def size(self):
        """Return size of gridworld as a tuple in row-major order."""
        if self.W is None:
            return (0, 0)
        else:
            return self.W.shape

    def loads(self, gw_desc):
        """Reincarnate using given gridworld description string.
        
        @param gw_desc: String containing a gridworld description.

        In a gridworld description, any line beginning with # is
        ignored (regarded as a comment). The first non-blank and
        non-comment line must give the grid size as two positive
        integers separated by whitespace, with the first being the
        number of rows and the second the number of columns.

        Each line after the size line is used to construct a row of
        the gridworld. These are read in order with maximum number of
        lines being the number of rows in the gridworld.  A row
        definition is whitespace-sensitive up to the number of columns
        (any characters beyond the column count are ignored, so in
        particular trailing whitespace is allowed) and can include the
        following symbols:

          - C{ } : an empty cell,
          - C{*} : a statically occupied cell,
          - C{I} : possible initial cell,
          - C{G} : goal cell (must be visited infinitely often).

        If the end of file is reached before all rows have been
        constructed, then the remaining rows are assumed to be empty.
        After all rows have been constructed, the remainder of the
        file is ignored.
        """
        ###################################################
        # Internal format notes:
        #
        # W is a matrix of integers with the same shape as the
        # gridworld.  Each element has value indicating properties of
        # the corresponding cell, according the following key.
        #
        # 0 - empty,
        # 1 - statically (permanently) occupied.
        ###################################################
        W = None
        init_list = []
        goal_list = []
        row_index = -1
        for line in gw_desc.splitlines():
            if row_index != -1:
                # Size has been read, so we are processing row definitions
                if row_index >= W.shape[0]:
                    break
                for j in range(min(len(line), W.shape[1])):
                    if line[j] == " ":
                        W[row_index][j] = 0
                    elif line[j] == "*":
                        W[row_index][j] = 1
                    elif line[j] == "I":
                        init_list.append((row_index, j))
                    elif line[j] == "G":
                        goal_list.append((row_index, j))
                    else:
                        raise ValueError("unrecognized row symbol \""+str(line[j])+"\".")
                row_index += 1
            else:
                # Still looking for gridworld size in the given string
                if len(line.strip()) == 0 or line.lstrip()[0] == "#":
                    continue  # Ignore blank and comment lines
                line_el = line.split()
                W = np.zeros((int(line_el[0]), int(line_el[1])),
                             dtype=np.int32)
                row_index = 0

        if W is None:
            raise ValueError("malformed gridworld description.")

        # Arrived here without errors, so actually reincarnate
        self.W = W
        self.init_list = init_list
        self.goal_list = goal_list


    def load(self, gw_file):
        """Read description from given file.

        Merely a convenience wrapper for the L{loads} method.
        """
        with open(gw_file, "r") as f:
            self.loads(f.read())

    def dumps(self, line_prefix=""):
        """Dump gridworld description string.

        @param line_prefix: prefix each line with this string.
        """
        if self.W is None:
            raise ValueError("Gridworld does not exist.")
        out_str = line_prefix+" ".join([str(i) for i in self.W.shape])+"\n"
        for i in range(self.W.shape[0]):
            out_str += line_prefix
            for j in range(self.W.shape[1]):
                if self.W[i][j] == 0:
                    if (i,j) in self.init_list:
                        out_str += "I"
                    elif (i,j) in self.goal_list:
                        out_str += "G"
                    else:
                        out_str += " "
                elif self.W[i][j] == 1:
                    out_str += "*"
                else:
                    raise ValueError("Unrecognized internal world W encoding.")
            out_str += "\n"
        return out_str


    def dumpsubworld(self, size, offset=(0, 0), prefix="Y", extend=False):
        """Generate new GridWorld instance from part of current one.

        Does not perform automatic truncation (to make desired
        subworld fit); instead a ValueError exception is raised.
        However, the "extend" argument can be used to achieve
        something similar.

        Possible initial positions and goals are not included in the
        returned GridWorld instance.

        @param size: (height, width)
        @param prefix: String to be used as prefix for naming
                 subgridworld cell variables.
        @param extend: If True, then any size and offset is permitted,
                 where any positions outside the actual gridworld are
                 assumed to be occupied.

        @rtype: L{GridWorld}
        """
        if self.W is None:
            raise ValueError("Gridworld does not exist.")
        if len(size) != len(self.W.shape) or len(offset) != len(self.W.shape):
            raise ValueError("malformed size or offset.")
        if not extend:
            if offset[0] < 0 or offset[0] >= self.W.shape[0] or offset[1] < 0 or offset[1] >= self.W.shape[1]:
                raise ValueError("offset is out of bounds.")
            if size[0] < 1 or size[1] < 1 or offset[0]+size[0] > self.W.shape[0] or offset[1]+size[1] > self.W.shape[1]:
                raise ValueError("unworkable subworld size, given offset.")
            sub = GridWorld(prefix=prefix)
            sub.W = self.W[offset[0]:(offset[0]+size[0]), offset[1]:(offset[1]+size[1])].copy()
        else:
            sub = GridWorld(prefix=prefix)
            sub.W = np.ones(size)
            self_offset = (max(offset[0],0), max(offset[1],0))
            self_offset = (min(self_offset[0],self.W.shape[0]-1), min(self_offset[1],self.W.shape[1]-1))
            sub_offset = (max(-offset[0],0), max(-offset[1],0))
            sub_offset = (min(sub_offset[0], sub.W.shape[0]-1), min(sub_offset[1], sub.W.shape[1]-1))
            actual_size = (min(size[0], self.W.shape[0]-self_offset[0], sub.W.shape[0]-sub_offset[0]),
                           min(size[1], self.W.shape[1]-self_offset[1], sub.W.shape[1]-sub_offset[1]))
            sub.W[sub_offset[0]:(sub_offset[0]+actual_size[0]), sub_offset[1]:(sub_offset[1]+actual_size[1])] = self.W[self_offset[0]:(self_offset[0]+actual_size[0]), self_offset[1]:(self_offset[1]+actual_size[1])]
        return sub


    def dumpPPartition(self, side_lengths=(1., 1.), offset=(0., 0.), nonbool=True):
        """Return proposition-preserving partition from this gridworld.

        In setting the initial transition matrix, we assume the
        gridworld is 4-connected.

        @param side_lengths: pair (W, H) giving width and height of
                 each cell, assumed to be the same across the grid.
        @param offset: 2-dimensional coordinate declaring where the
                 bottom-left corner of the gridworld should be placed
                 in the continuous space; default places it at the origin.

        @rtype: L{PropPreservingPartition<prop2part.PropPreservingPartition>}
        """
        if self.W is None:
            raise ValueError("Gridworld does not exist.")
        domain = pc.Polytope(A=np.array([[0,-1],
                                         [0,1],
                                         [-1,0],
                                         [1,0]], dtype=np.float64),
                             b=np.array([-offset[1],
                                          offset[1]+self.W.shape[0]*side_lengths[1],
                                          -offset[0],
                                          offset[0]+self.W.shape[1]*side_lengths[0]],
                                        dtype=np.float64))
        cells = {}
        for i in range(self.W.shape[0]):
            for j in range(self.W.shape[1]):
                if nonbool:
                    cell_var = self.__getitem__((i,j))
                else:
                    cell_var = self.prefix+"_"+str(i)+"_"+str(j)
                cells[cell_var] \
                    = pc.Polytope(A=np.array([[0,-1],
                                              [0,1],
                                              [-1,0],
                                              [1,0]], dtype=np.float64),
                                  b=np.array([-offset[1]-(self.W.shape[0]-i-1)*side_lengths[1],
                                               offset[1]+(self.W.shape[0]-i)*side_lengths[1],
                                               -offset[0]-j*side_lengths[0],
                                               offset[0]+(j+1)*side_lengths[0]],
                                          dtype=np.float64))
        part = prop2part2(domain, cells)

        adjacency = np.zeros((self.W.shape[0]*self.W.shape[1], self.W.shape[0]*self.W.shape[1]), dtype=np.int8)
        for this_ind in range(len(part.list_region)):
            (prefix, i, j) = extract_coord(part.list_prop_symbol[part.list_region[this_ind].list_prop.index(1)],
                                           nonbool=nonbool)
            if self.W[i][j] != 0:
                continue  # Static obstacle cells are not traversable
            adjacency[this_ind, this_ind] = 1
            if i > 0 and self.W[i-1][j] == 0:
                row_index = i-1
                col_index = j
            if j > 0 and self.W[i][j-1] == 0:
                row_index = i
                col_index = j-1
            if i < self.W.shape[0]-1 and self.W[i+1][j] == 0:
                row_index = i+1
                col_index = j
            if j < self.W.shape[1]-1 and self.W[i][j+1] == 0:
                row_index = i
                col_index = j+1
            if nonbool:
                symbol_ind = part.list_prop_symbol.index(self.__getitem__((row_index, col_index)))
            else:
                symbol_ind = part.list_prop_symbol.index(prefix+"_"+str(row_index)+"_"+str(col_index))
            ind = 0
            while part.list_region[ind].list_prop[symbol_ind] == 0:
                ind += 1
            adjacency[ind, this_ind] = 1
        part.adj = adjacency
        return part
    
    def discreteTransitionSystem(self, nonbool=True):
        """ Write a discrete transition system suitable for synthesis.
        Unlike dumpPPartition, this does not create polytopes; it is 
        nonetheless useful and computationally less expensive.

        @param nonbool: If True, then use gr1c support for nonboolean
                 variable domains.  In particular this affects region
                 naming, as achieved with L{__getitem__}.
        
        @rtype: L{PropPreservingPartition<prop2part.PropPreservingPartition>}
        """
        disc_dynamics = PropPreservingPartition(list_region=[],
                            list_prop_symbol=[], trans=[])
        num_cells = self.W.shape[0] * self.W.shape[1]
        for i in range(self.W.shape[0]):
            for j in range(self.W.shape[1]):
                flat = lambda x, y: x*self.W.shape[1] + y
                # Proposition
                prop = self.__getitem__((i,j), nonbool=nonbool)
                disc_dynamics.list_prop_symbol.append(prop)
                # Region
                r = [ 0 for x in range(0, num_cells) ]
                r[flat(i,j)] = 1
                disc_dynamics.list_region.append(pc.Region("R_" + prop, r))
                # Transitions
                # trans[p][q] if q -> p
                t = [ 0 for x in range(0, num_cells) ]
                t[flat(i,j)] = 1
                if self.W[i][j] == 0:
                    if i > 0: t[flat(i-1,j)] = 1
                    if j > 0: t[flat(i,j-1)] = 1
                    if i < self.W.shape[0]-1: t[flat(i+1,j)] = 1
                    if j < self.W.shape[1]-1: t[flat(i,j+1)] = 1
                disc_dynamics.trans.append(t)
        disc_dynamics.num_prop = len(disc_dynamics.list_prop_symbol)
        disc_dynamics.num_regions = len(disc_dynamics.list_region)
        return disc_dynamics
    
    def deterministicMovingObstacle(self, path):
        trans = []
        num_cells = self.W.shape[0] * self.W.shape[1]
        for i in range(self.W.shape[0]):
            for j in range(self.W.shape[1]):
                flat = lambda x, y: x*self.W.shape[1] + y
                t = [ 0 for x in range(0, num_cells) ]
                if (i,j) in path:
                    n = path.index((i,j))
                    # path[n-1] -> path[n], path[L-1] -> path[0]
                    t[flat(*path[(n-1)%len(path)])] = 1
                trans.append(t)
        return trans
        
    def spec(self, offset=(0, 0), controlled_dyn=True, nonbool=True):
        """Return GRSpec instance describing this gridworld.

        The offset argument is motivated by the use-case of multiple
        agents whose moves are governed by separate "gridworlds" but
        who interact in a shared space; with an offset, we can make
        "sub-gridworlds" and enforce rules like mutual exclusion.

        Syntax is that of gr1c; in particular, "next" variables are
        primed. For example, x' refers to the variable x at the next
        time step.

        If nonbool is False, then variables are named according to
        prefix_R_C, where prefix is given (attribute of this GridWorld
        object), R is the row, and C is the column of the cell
        (0-indexed).  If nonbool is True (default), cells are
        identified with subformulae of the form::

          ((prefix_r = R) & (prefix_c = C))

        L{GridWorld.__getitem__} and L{extract_coord} provide
        reference implementations.

        For incorporating this gridworld into an existing
        specification (e.g., respecting external references to cell
        variable names), see the method L{GRSpec.importGridWorld}.

        @param offset: index offset to apply when generating the
                 specification; e.g., given prefix of "Y",
                 offset=(2,1) would cause the variable for the cell at
                 (0,3) to be named Y_2_4.

        @param controlled_dyn: whether to treat this gridworld as
                 describing controlled ("system") or uncontrolled
                 ("environment") variables.

        @param nonbool: If True, then use gr1c support for nonboolean
                 variable domains.

        @rtype: L{GRSpec}
        """
        if self.W is None:
            raise ValueError("Gridworld does not exist.")
        row_low = 0
        row_high = self.W.shape[0]
        col_low = 0
        col_high = self.W.shape[1]
        spec_trans = []
        orig_offset = copy.copy(self.offset)
        if nonbool:
            self.offset = (0,0)
        else:
            self.offset = offset
        # Safety, transitions
        for i in range(row_low, row_high):
            for j in range(col_low, col_high):
                if self.W[i][j] == 1:
                    continue  # Cannot start from an occupied cell.
                spec_trans.append(self.__getitem__((i,j), nonbool=nonbool)+" -> (")
                # Normal transitions:
                spec_trans[-1] += self.__getitem__((i,j), next=True, nonbool=nonbool)
                if i > row_low and self.W[i-1][j] == 0:
                    spec_trans[-1] += " | " + self.__getitem__((i-1,j), next=True, nonbool=nonbool)
                if j > col_low and self.W[i][j-1] == 0:
                    spec_trans[-1] += " | " + self.__getitem__((i,j-1), next=True, nonbool=nonbool)
                if i < row_high-1 and self.W[i+1][j] == 0:
                    spec_trans[-1] += " | " + self.__getitem__((i+1,j), next=True, nonbool=nonbool)
                if j < col_high-1 and self.W[i][j+1] == 0:
                    spec_trans[-1] += " | " + self.__getitem__((i,j+1), next=True, nonbool=nonbool)
                spec_trans[-1] += ")"

        # Safety, static
        for i in range(row_low, row_high):
            for j in range(col_low, col_high):
                if self.W[i][j] == 1:
                    spec_trans.append("!(" + self.__getitem__((i,j), next=True, nonbool=nonbool) + ")")

        # Safety, mutex; only needed when using boolean variables for cells
        if not nonbool:
            pos_indices = [k for k in itertools.product(range(row_low, row_high), range(col_low, col_high))]
            disj = []
            for outer_ind in pos_indices:
                conj = []
                if outer_ind != (-1, -1) and self.W[outer_ind[0]][outer_ind[1]] == 1:
                    continue
                if outer_ind == (-1, -1):
                    conj.append(self.prefix+"_n_n'")
                else:
                    conj.append(self.__getitem__((outer_ind[0], outer_ind[1]), next=True, nonbool=nonbool))
                for inner_ind in pos_indices:
                    if ((inner_ind != (-1, -1) and self.W[inner_ind[0]][inner_ind[1]] == 1)
                        or outer_ind == inner_ind):
                        continue
                    if inner_ind == (-1, -1):
                        conj.append("(!" + self.prefix+"_n_n')")
                    else:
                        conj.append("(!" + self.__getitem__((inner_ind[0], inner_ind[1]), next=True, nonbool=nonbool)+")")
                disj.append("(" + " & ".join(conj) + ")")
            spec_trans.append("\n| ".join(disj))

        if nonbool:
            sys_vars = [self.prefix+"_r", self.prefix+"_c"]
            sys_domains = [(0, self.W.shape[0]-1), (0, self.W.shape[1]-1)]
        else:
            sys_vars = []
            for i in range(row_low, row_high):
                for j in range(col_low, col_high):
                    sys_vars.append(self.__getitem__((i,j), nonbool=nonbool))
            sys_domains = None  # Default to boolean

        if nonbool:
            initspec = [self.__getitem__(loc, nonbool=nonbool) for loc in self.init_list]
        else:
            initspec = []
            for loc in self.init_list:
                mutex = [self.__getitem__((loc[0],loc[1]), nonbool=nonbool)]
                mutex.extend(["!"+ovar for ovar in sys_vars if ovar != self.__getitem__(loc, nonbool=nonbool)])
                initspec.append("(" + " & ".join(mutex) + ")")
        init_str = " | ".join(initspec)

        spec_goal = []
        for loc in self.goal_list:
            spec_goal.append(self.__getitem__(loc, nonbool=nonbool))
        
        self.offset = orig_offset
        if controlled_dyn:
            return GRSpec(sys_vars=sys_vars, sys_domains=sys_domains,
                          sys_init=init_str, sys_safety=spec_trans, sys_prog=spec_goal)
        else:
            return GRSpec(env_vars=sys_vars, env_domains=sys_domains,
                          env_init=init_str, env_safety=spec_trans, env_prog=spec_goal)

    
    def scale(self, xf=1, yf=1):
        """Return a new gridworld equivalent to this but scaled by integer
        factor (xf, yf). In the new world, obstacles are increased in size but
        initials and goals change their position only. If this world is of size
        (h, w) then the returned world will be of size (h*yf, w*xf).
        
        @param xf: integer scaling factor for rows
        @param yf: integer scaling factor for columns
        
        @rtype: L{GridWorld}
        """
        shape_scaled = (self.W.shape[0]*yf, self.W.shape[1]*xf)
        scaleW = np.zeros(shape_scaled, dtype=np.int32)
        scale_goal = []
        scale_init = []
        for row in range(shape_scaled[0]):
            for col in range(shape_scaled[1]):
                (y,x) = (row/yf, col/xf)
                (yr, xr) = (row % yf, col % xf)
                if self.W[y,x] == 1:
                    scaleW[row, col] = 1
                if (yr, xr) == (0, 0):
                    if (y,x) in self.goal_list:
                        scale_goal.append((row,col))
                    if (y,x) in self.init_list:
                        scale_init.append((row,col))
        scale_gw = GridWorld(prefix=self.prefix)
        scale_gw.W = scaleW
        scale_gw.goal_list = scale_goal
        scale_gw.init_list = scale_init
        return scale_gw
        
def place_features(W, n):
    """Place n features randomly in 1D array W"""
    try:
        avail_inds = np.arange(W.size)[W==0]
        np.random.shuffle(avail_inds)
        return avail_inds[:n]
    except IndexError:
        raise ValueError("Unable to place features: no empty space left")
        
def world_from_1D(W, size, goal_list, init_list, prefix="Y"):
    W = W.reshape(size)
    row_col = lambda k: (k/size[1], k%size[1])
    goal_list = [row_col(k) for k in goal_list]
    init_list = [row_col(k) for k in init_list]
    gw = GridWorld(prefix=prefix)
    gw.W = W
    gw.goal_list = goal_list
    gw.init_list = init_list
    return gw


class MGridWorld(GridWorld):
    """Gridworld with support for models of moving obstacles.
    """
    def __init__(self, gw_desc=None, prefix="Y"):
        """(See documentation for L{GridWorld.__init__}.)

        The first argument can be an instance of GridWorld from which
        a new instance of MGridWorld should be built.  In this case,
        the prefix argument is ignored.
        """
        if isinstance(gw_desc, GridWorld):
            GridWorld.__init__(self, gw_desc=gw_desc.dumps(), prefix=gw_desc.prefix)
        else:
            GridWorld.__init__(self, gw_desc=None, prefix=prefix)
            self.troll_list = []
            if gw_desc is not None:
                self.loads(gw_desc)

    def __eq__(self, other):
        """Test for equality.

        Does not compare prefixes of cell variable names.
        """
        if not GridWorld.__eq__(self, other) or self.troll_list != other.troll_list:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.pretty(show_grid=True)

    def pretty(self, show_grid=False, line_prefix="", path=[], goal_order=False):
        """Wrap L{GridWorld.pretty}, using troll_list of this object.
        """
        return GridWorld.pretty(self, show_grid=show_grid, line_prefix=line_prefix, path=path, goal_order=goal_order, troll_list=self.troll_list)

    def plot(self, font_pt=18, show_grid=False, grid_width=2):
        """Wrap L{GridWorld.plot}, using troll_list of this object.
        """
        return GridWorld.plot(self, font_pt=font_pt, show_grid=show_grid, grid_width=grid_width, troll_list=self.troll_list)

    def loads(self, gw_desc):
        """Reincarnate using obstacle-annotated gridworld description string.

        Cf. L{GridWorld.loads}.  The core description string format is
        extended to support the following:

          - C{E} : a base cell to which a troll must always return;
             default radius is 1.
        """
        W = None
        init_list = []
        goal_list = []
        troll_list = []
        row_index = -1
        for line in gw_desc.splitlines():
            if row_index != -1:
                # Size has been read, so we are processing row definitions
                if row_index >= W.shape[0]:
                    break
                for j in range(min(len(line), W.shape[1])):
                    if line[j] == " ":
                        W[row_index][j] = 0
                    elif line[j] == "*":
                        W[row_index][j] = 1
                    elif line[j] == "I":
                        init_list.append((row_index, j))
                    elif line[j] == "G":
                        goal_list.append((row_index, j))
                    elif line[j] == "E":
                        troll_list.append(((row_index, j), 1))
                    else:
                        raise ValueError("unrecognized row symbol \""+str(line[j])+"\".")
                row_index += 1
            else:
                # Still looking for gridworld size in the given string
                if len(line.strip()) == 0 or line.lstrip()[0] == "#":
                    continue  # Ignore blank and comment lines
                line_el = line.split()
                W = np.zeros((int(line_el[0]), int(line_el[1])),
                             dtype=np.int32)
                row_index = 0

        if W is None:
            raise ValueError("malformed gridworld description.")

        # Arrived here without errors, so actually reincarnate
        self.W = W
        self.init_list = init_list
        self.goal_list = goal_list
        self.troll_list = troll_list

    def dumps(self, line_prefix=""):
        """Dump obstacle-annotated gridworld description string

        Cf. L{loads} of this class and L{GridWorld.dumps}.
        """
        if self.W is None:
            raise ValueError("Gridworld does not exist.")
        out_str = line_prefix+" ".join([str(i) for i in self.W.shape])+"\n"
        for i in range(self.W.shape[0]):
            out_str += line_prefix
            for j in range(self.W.shape[1]):
                if self.W[i][j] == 0:
                    if (i,j) in self.init_list:
                        out_str += "I"
                    elif (i,j) in self.goal_list:
                        out_str += "G"
                    elif ((i,j),1) in self.troll_list:
                        out_str += "E"
                    else:
                        out_str += " "
                elif self.W[i][j] == 1:
                    out_str += "*"
                else:
                    raise ValueError("Unrecognized internal world W encoding.")
            out_str += "\n"
        return out_str

    def mspec(self, troll_prefix="X"):
        """

        Cf. L{GridWorld.spec} and L{add_trolls}.
        """
        return add_trolls(self, self.troll_list, get_moves_lists=False, prefix=troll_prefix)


class CGridWorld(GridWorld):
    """Gridworld with intrinsic relation to continuous space partition.
    """
    def __init__(self, gw_desc=None, prefix="Y",
                 side_lengths=(1., 1.), offset=(0., 0.)):
        """(See documentation for L{GridWorld.__init__} and L{GridWorld.dumpPPartition}.)"""
        GridWorld.__init__(self, gw_desc=gw_desc, prefix=prefix)
        self.part = self.dumpPPartition(side_lengths=side_lengths, offset=offset, nonbool=False)
        self.side_lengths = copy.copy(side_lengths)
        self.offset = np.array(offset, dtype=np.float64)

    def __copy__(self):
        return self.copy()

    def copy(self):
        Y = GridWorld.copy(self)
        Y.part = self.part.copy()
        return Y

    def remap(self, side_lengths=(1., 1.), offset=(0., 0.)):
        """Change associated continuous space partition.
        """
        self.part = self.dumpPPartition(side_lengths=side_lengths, offset=offset, nonbool=False)

    def get_cell(self, x):
        """Return discrete coordinate (i,j) of cell that contains x.

        ...or None if x is outside the gridworld.
        """
        if not (isinstance(x, np.ndarray) and
                len(x.shape) == 1 and x.shape[0] == 2):
            raise TypeError("continuous state must be 2-d vector.")
        for r in self.part.list_region:
            # Assume there is only one polytope per region
            if pc.is_inside(r.list_poly[0], x):
                # ...and only one symbol associated with it
                (prefix, i, j) = extract_coord(self.part.list_prop_symbol[r.list_prop.index(1)], nonbool=False)
                return (i,j)
        return None

    def get_bbox(self, coord):
        """Return bounding box for cell with given discrete coordinate.

        @param coord: (row, column) pair; supports negative indices.

        @return: L{numpy.ndarray} (size 2 by 2), first row is the
                 lower-left point, second row is the upper-right point.
        """
        if self.W is None:
            raise ValueError("Gridworld is empty; no cells exist.")
        if len(coord) != len(self.W.shape):
            raise ValueError("malformed gridworld coord.")
        # lower-left
        coord = (coord[0]%self.W.shape[0], coord[1]%self.W.shape[1])
        ll = np.array([float(coord[1])*self.side_lengths[0],
                       float(self.W.shape[0]-(coord[0]+1))*self.side_lengths[1]])
        # upper-right
        ur = np.array([float(coord[1]+1)*self.side_lengths[0],
                       float(self.W.shape[0]-coord[0])*self.side_lengths[1]])
        return np.array([self.offset+ll, self.offset+ur])

    def get_ccenter(self, coord):
        """Get continuous position center for cell from discrete coordinate.

        ...merely a convenience wrapper using get_bbox()
        """
        return np.mean(self.get_bbox(coord), axis=0)


def random_world(size, wall_density=.2, num_init=1, num_goals=2, prefix="Y",
                 ensure_feasible=False, timeout=None,
                 num_trolls=0):
    """Generate random gridworld of given size.

    While an instance of GridWorld is returned, other views of the
    result are possible; e.g., to obtain a description string, use
    L{GridWorld.dumps}.

    @param size: a pair, indicating number of rows and columns.
    @param wall_density: the ratio of walls to total number of cells.
    @param num_init: number of possible initial positions.
    @param num_goals: number of positions to be visited infinitely often.
    @param prefix: string to be used as prefix for naming gridworld
             cell variables.

    @param num_trolls: number of random trolls to generate, each
             occupies an area of radius 1.  If nonzero, then an
             instance of MGridWorld will be returned.

    @param ensure_feasible: guarantee that all goals and initial
             positions are mutually reachable, assuming a 4-connected
             grid. This method may not be complete, i.e., may fail to
             return a feasible random gridworld with the given
             parameters.  Note that "feasibility" does not account for
             nondeterminism (in particular, nonzero num_trolls
             argument has no effect.)

    @param timeout: if ensure_feasible, then quit if no correct random
             world is found before timeout seconds.  If timeout is
             None (default), then do not impose time constraints.

    @rtype: L{GridWorld}, or None if timeout occurs.
    """
    if ensure_feasible and timeout is not None:
        st = time.time()
    num_cells = size[0]*size[1]
    goal_list = []
    init_list = []
    troll_list = []
    W = np.zeros(num_cells, dtype=np.int32)
    num_blocks = int(np.round(wall_density*num_cells))
    for i in range(num_goals):
        avail_inds = np.array(range(num_cells))[W==0]
        avail_inds = [k for k in avail_inds if k not in goal_list]
        goal_list.append(avail_inds[np.random.randint(low=0, high=len(avail_inds))])
    for i in range(num_init):
        avail_inds = np.array(range(num_cells))[W==0]
        avail_inds = [k for k in avail_inds if k not in goal_list and k not in init_list]
        init_list.append(avail_inds[np.random.randint(low=0, high=len(avail_inds))])
    for i in range(num_trolls):
        avail_inds = np.array(range(num_cells))[W==0]
        avail_inds = [k for k in avail_inds if k not in goal_list and k not in init_list and k not in troll_list]
        troll_list.append(avail_inds[np.random.randint(low=0, high=len(avail_inds))])
    bcounter = 0
    while bcounter < num_blocks:  # Add blocks (or "wall cells")
        avail_inds = np.array(range(num_cells))[W==0]
        avail_inds = [k for k in avail_inds if k not in goal_list and k not in init_list and k not in troll_list]
        changed_index = np.random.randint(low=0, high=len(avail_inds))
        W[avail_inds[changed_index]] = 1
        bcounter += 1
        if ensure_feasible:
            if (timeout is not None) and (time.time()-st > timeout):
                return None
            # If feasibility must be guaranteed, then check whether
            # the newly unreachable cell is permissible.
            W_tmp = W.reshape(size)
            goal_list_tmp = [(k/size[1], k%size[1]) for k in goal_list]
            init_list_tmp = [(k/size[1], k%size[1]) for k in init_list]
            troll_list_tmp = [(k/size[1], k%size[1]) for k in troll_list]
            world = GridWorld(prefix=prefix)
            world.W = W_tmp
            chain_of_points = init_list_tmp[:]
            chain_of_points.extend(goal_list_tmp)
            is_feasible = True
            for i in range(len(chain_of_points)):
                if not world.isReachable(chain_of_points[i], chain_of_points[(i+1)%len(chain_of_points)]):
                    is_feasible = False
                    break
            if not is_feasible:
                W[avail_inds[changed_index]] = 0
                bcounter -= 1
    # Reshape the gridworld to final form; build and return the result.
    W = W.reshape(size)
    goal_list = [(k/size[1], k%size[1]) for k in goal_list]
    init_list = [(k/size[1], k%size[1]) for k in init_list]
    troll_list = [((k/size[1], k%size[1]), 1) for k in troll_list]
    world = GridWorld(prefix=prefix)
    world.W = W
    world.goal_list = goal_list
    world.init_list = init_list
    if num_trolls > 0:
        world = MGridWorld(world)
        world.troll_list = troll_list
    return world

    
def narrow_passage(size, passage_width=1, num_init=1, num_goals=2,
            passage_length=0.4, ptop=None, prefix="Y"):
    """Generate a narrow-passage world: this is a world containing 
    two zones (initial, final) with a tube connecting them.
    
    @param size: a pair, indicating number of rows and columns.
    @param passage_width: the width of the connecting passage in cells.
    @param passage_length: the length of the passage as a proportion of the
                           width of the world.
    @param num_init: number of possible initial positions.
    @param num_goals: number of positions to be visited infinitely often.
    @param ptop: row number of top of passage, default (None) is random
    @param prefix: string to be used as prefix for naming gridworld
                   cell variables.
                   
    @rtype: L{GridWorld}
    """
                   
    (w, h) = size
    if w < 3 or h < 3:
        raise ValueError("Gridworld too small: minimum dimension 3")
    Z = unoccupied(size, prefix)
    # Zone width is 30% of world width by default
    zone_width = ((1.0-passage_length)/2.0)*size[1]
    izone = int(max(1, zone_width)) # boundary of left zone
    gzone = size[1] - int(max(1, zone_width)) # boundary of right zone
    if izone * size[0] < num_init or gzone * size[0] < num_goals:
        raise ValueError("Too many initials/goals for grid size")
    if ptop is None:
        ptop = np.random.randint(0, size[0]-passage_width)
    passage = range(ptop, ptop+passage_width)
    print passage, ptop
    for y in range(0, size[0]):
        if y not in passage:
            for x in range(izone, gzone):
                Z.W[y][x] = 1
    avail_cells = [(y,x) for y in range(size[0]) for x in range(izone)]
    Z.init_list = random.sample(avail_cells, num_init)
    avail_cells = [(y,x) for y in range(size[0]) for x in range(gzone, size[1])]
    Z.goal_list = random.sample(avail_cells, num_goals)
    return Z


def add_trolls(Y, troll_list, prefix="X", start_anywhere=False, nonbool=True,
               get_moves_lists=True):
    """Create GR(1) specification with troll-like obstacles.

    Trolls are introduced into the specification with names derived
    from the given prefix and a number (matching the order in
    troll_list).  Note that mutual exclusion is only between the
    controlled "Y gridworld" position and each troll, but not
    between trolls.

    @type Y: L{GridWorld}
    @param Y: The controlled gridworld, describing in particular
             static obstacles that must be respected by the trolls.

    @param troll_list: List of pairs of center position, to which the
             troll must always eventually return, and radius defining
             the extent of the trollspace.  The radius is measured
             using infinity-norm.
    @param start_anywhere: If True, then initial troll position can be
             anywhere in its trollspace.  Else (default), the troll is
             assumed to begin each game at its center position.
    @param nonbool: If True, then use gr1c support for nonboolean
                 variable domains.
    @param get_moves_lists: Consult returned value description below.
    
    @rtype: (L{GRSpec}, list)

    @return: If get_moves_lists is True, then returns (spec, moves_N)
             where spec is the specification incorporating all of the
             trolls, and moves_N is a list of lists of states (where
             "state" is given as a dictionary with keys of variable
             names), where the length of moves_N is equal to the
             number of trolls, and each element of moves_N is a list
             of possible states of that the corresponding troll
             (dynamic obstacle).  If get_moves_lists is False, then
             moves_N is not returned and not computed.
    """
    X = []
    X_ID = -1
    if get_moves_lists:
        moves_N = []
    (num_rows, num_cols) = Y.size()
    for (center, radius) in troll_list:
        if center[0] >= num_rows or center[0] < 0 or center[1] >= num_cols or center[1] < 0:
            raise ValueError("troll center is outside of gridworld")
        t_offset = (max(0, center[0]-radius), max(0, center[1]-radius))
        t_size = [center[0]-t_offset[0]+radius+1, center[1]-t_offset[1]+radius+1]
        if t_offset[0]+t_size[0] >= num_rows:
            t_size[0] = num_rows-t_offset[0]
        if t_offset[1]+t_size[1] >= num_cols:
            t_size[1] = num_cols-t_offset[1]
        t_size = (t_size[0], t_size[1])
        X_ID += 1
        X.append((t_offset, Y.dumpsubworld(t_size, offset=t_offset, prefix=prefix+"_"+str(X_ID))))
        X[-1][1].goal_list = [(center[0]-t_offset[0], center[1]-t_offset[1])]
        if start_anywhere:
            X[-1][1].init_list = []
            for i in range(X[-1][1].size()[0]):
                for j in range(X[-1][1].size()[1]):
                    if X[-1][1].isEmpty((i,j)):
                        X[-1][1].init_list.append((i,j))
        else:
            X[-1][1].init_list = [(center[0]-t_offset[0], center[1]-t_offset[1])]
        if get_moves_lists:
            moves_N.append([])
            for i in range(t_size[0]):
                for j in range(t_size[1]):
                    moves_N[-1].append(X[-1][1].state((i,j), offset=t_offset, nonbool=nonbool))

    spec = GRSpec()
    spec.importGridWorld(Y, controlled_dyn=True, nonbool=nonbool)
    for Xi in X:
        spec.importGridWorld(Xi[1], offset=(-Xi[0][0], -Xi[0][1]), controlled_dyn=False, nonbool=nonbool)

    # Mutual exclusion
    for i in range(Y.size()[0]):
        for j in range(Y.size()[1]):
            for Xi in X:
                if i >= Xi[0][0] and i < Xi[0][0]+Xi[1].size()[0] and j >= Xi[0][1] and j < Xi[0][1]+Xi[1].size()[1]:
                    if nonbool:
                        Xivar = "(("+Xi[1].prefix+"_r' = "+str(i-Xi[0][0])+") & ("+Xi[1].prefix+"_c' = "+str(j-Xi[0][1])+"))"
                    else:
                        Xivar = Xi[1].prefix+"_"+str(i)+"_"+str(j)+"'"
                    spec.sys_safety.append("!("+Y.__getitem__((i,j), nonbool=nonbool, next=True)+" & "+Xivar+")")

    if get_moves_lists:
        return (spec, moves_N)
    return spec


def unoccupied(size, prefix="Y"):
    """Generate entirely unoccupied gridworld of given size.
    
    @param size: a pair, indicating number of rows and columns.
    @param prefix: String to be used as prefix for naming gridworld
             cell variables.
    @rtype: L{GridWorld}
    """
    if len(size) < 2:
        raise TypeError("invalid gridworld size.")
    return GridWorld(str(size[0])+" "+str(size[1]), prefix="Y")


def extract_coord(subf, nonbool=True):
    """Extract (prefix,row,column) tuple from given subformula.

    If nonbool is False, then assume prefix_R_C format. prefix is of
    type string; row and column are integers.  The "nowhere" coordinate
    has form prefix_n_n. To indicate this, (-1, -1) is returned as the
    row, column position.

    If nonbool is True (default), then assume
    C{((prefix_r = R) & (prefix_c = C))} format.

    Also consult L{GridWorld.__getitem__} and L{GridWorld.spec}.

    If error, return None or throw exception.
    """
    if not isinstance(subf, str):
        raise TypeError("extract_coord: invalid argument type; must be string.")
    if nonbool:
        subf_frags = [s.strip().strip(")(").strip() for s in subf.split("=")]
        if (len(subf_frags) != 3) or not ((subf_frags[0].endswith("_r") and subf_frags[1].endswith("_c")) or (subf_frags[1].endswith("_r") and subf_frags[0].endswith("_c"))):
            return None
        prefix = subf_frags[0][:subf_frags[0].rfind("_")]
        row = int(subf_frags[1][:subf_frags[1].find(")")])
        col = int(subf_frags[2])
        if not subf_frags[0].endswith("_r"):
            row, col = col, row  # Swap
        return (prefix, row, col)
    else:
        name_frags = subf.split("_")
        if len(name_frags) < 3:
            return None
        try:
            if name_frags[-1] == "n" and name_frags[-2] == "n":
                # Special "nowhere" case
                return ("_".join(name_frags[:-2]), -1, -1)
            col = int(name_frags[-1])
            row = int(name_frags[-2])
        except ValueError:
            return None
        return ("_".join(name_frags[:-2]), row, col)

def prefix_filt(d, prefix):
    """Return all items in dictionary d with key with given prefix."""
    match_list = []
    for k in d.keys():
        if isinstance(k, str):
            if k.startswith(prefix):
                match_list.append(k)
    return dict([(k, d[k]) for k in match_list])
    
def extract_path(aut, prefix=None):
    """Extract a path from a gridworld automaton"""
    n = 0  # Node with ID of 0
    last = None
    path = []
    visited = [0]
    while 1:
        updated = False
        for p in aut.node[n]["state"]:
            if (not prefix or p.startswith(prefix)) and aut.node[n]["state"][p]:
                try:
                    c = extract_coord(p, nonbool=False)
                    if c:
                        path.append(c[1:])
                        last = c[1:]
                        updated = True
                except:
                    pass
        if not updated:
            # Robot has not moved, even out path lengths
            path.append(last)
        # next state
        if len(aut.successors(n)) > 0:
            if aut.successors(n)[0] in visited:
                # loop detected
                break
            visited.append(aut.successors(n)[0])
            n = aut.successors(n)[0]
        else:
            # dead-end, return
            break
    try:
        first = [ x for x in path if x ][0]
    except IndexError:
        return []
    for i in range(len(path)):
        if path[i] is None:
            path[i] = first
        else:
            break
    return path
    
def verify_path(W, path, seq=False):
    goals = W.goal_list[:]
    print goals
    print path
    if seq:
        # Check if path visits all goals in gridworld W in the correct order
        for p in path:
            if not goals: break
            if goals[0] == p:
                del(goals[0])
            elif p in goals:
                return False
        if goals:
            return False
    else:
        # Check if path visits all goals
        for g in goals:
            if not g in path:
                assert_message = "Path does not visit goal " + str(g)
                print assert_message
                return False
    # Ensure that path does not intersect an obstacle
    for p in path:
        if not W.isEmpty(p):
            assert_message = "Path intersects obstacle at " + str(p)
            print assert_message
            return False
    return True
    
def verify_mutex(paths):
    # sanity check - all paths same length
    if not all(len(p) == len(paths[0]) for p in paths):
        assert_message = "Paths are different lengths"
        return False
    for t in zip(*paths):
        # Coordinates in each tuple must be unique
        if not len(set(t)) == len(t):
            assert_message = "Non-unique coordinates in tuple " + str(t)
            return False
    return True
    
def animate_paths(Z, paths, jitter=0.0, save_prefix=None):
    """Animate a list of paths simultaneously in world Z using matplotlib.
    
    @param Z: Gridworld for which paths were generated.
    @param paths: List of paths to animate (one per robot).
    @param jitter: Random jitter added to each coordinate value in animation.
                   Makes the robot's path more visible by avoiding overlap.
    @param save_prefix: If not None, do not show an animation but produce a 
                        series of images "<save_prefix>nnn.png" which can be 
                        compiled into an animated GIF.
    """
    colors = 'rgbcmyk'
    fig = plt.figure()
    ax = fig.add_subplot(111)
    Z.plot(font_pt=min(288/Z.W.shape[1], 48), show_grid=True)
    def update_line(num, dlist, lines):
        for (p,t), d in zip(lines, dlist):
            t.set_data(d[...,:num+1])
            p.set_data(d[...,num])
        if save_prefix:
            fig.savefig(save_prefix + "%03d.png" % num)
        return lines,

    data = []
    lines = []
    for n,path in enumerate(paths):
        arr = np.array([[x,y] for (y,x) in path]).transpose()
        arr = np.add(arr, jitter*(np.random.rand(*arr.shape) - 0.5))
        data.append(arr)
        l, = ax.plot([], [], 'o', color=colors[n], markersize=10.0, zorder=2)
        l_trail, = ax.plot([], [], '-', color=colors[n], zorder=1)
        lines.append((l, l_trail))
    
    if not save_prefix:
        ani = anim.FuncAnimation(fig, update_line, len(paths[0]), fargs=(data,lines),
            interval=500)
        plt.show()
    else:
        print "Writing %s000.png - %s%03d.png" % (save_prefix, save_prefix, len(paths[0]))
        for n in range(len(paths[0])):
            update_line(n, data, lines)
    
def compress_paths(paths):
    """Remove insignificant path-element tuples from a path list
    
    Given a list of paths [[p11, p12, ..., p1n], [p21, p22, ..., p2n], ...]
    a path-element tuple (p1k, p2k, ...) is insignificant if p1k = p1(k+1),
    p2k = p2(k+1), ...; (p1n, p2n, ...) is always significant.
    
    @param paths: A list of paths, where each path is a list of tuples, each
                  representing a coordinate in the world.
    
    @rtype: list of lists of (x,y) tuples
    """
    pzip = zip(*paths)
    if pzip == []: return []
    acc = []
    for n in range(len(pzip)-1):
        if not pzip[n] == pzip[n+1]:
            acc.append(pzip[n])
    acc.append(pzip[-1])
    return zip(*acc)

# Copyright (c) 2011-2014 by California Institute of Technology
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
Automaton class and supporting methods
"""

import re, copy, os, random
import xml.etree.ElementTree as ET
import numpy as np
import networkx as nx

import conxml

import logging
logger = logging.getLogger(__name__)


class Automaton(nx.DiGraph):
    """Automaton class for representing a finite state automaton.

    Nodes of the Automaton are labeled ("annotated") with:

      - C{state}: a dictionary whose keys are the names of the variables
        and whose values are the values of the variables.
      - C{mode}: goal mode of the strategy at this node.
      - C{rgrad}: value of a reach annotation.
    """
    def __init__(self, states_or_file="", varnames=[], verbose=0):
        """

        Automaton([states_or_file, varnames, verbose]) constructs an
        Automaton object based on the following optional input:

          - C{states_or_file}: a string containing the name of the aut
            file to be loaded, or an (open) file-like object.

          - C{varname}: a list of all the variable names. If it is not empty
            and states_or_file is a string representing the name of the aut
            file to be loaded, then this function will also check whether
            the variables in aut_file are in varnames.
        """
        nx.DiGraph.__init__(self)
        # Construct this automaton from a JTLV-style "aut" file
        if not (isinstance(states_or_file, str) and (len(states_or_file) == 0)):
            self.loadFile(states_or_file, varnames=varnames, verbose=verbose)

    def __le__(self, other):
        """Check sub-automaton relationship.

        A <= B ("A is a sub-automaton of B") if A is a subgraph of B,
        and their nodes agree on labeling.  This method assumes that
        node IDs are the same; in particular, it does not check for
        graph isomorphisms.
        """
        if (not isinstance(other, Automaton)) or (len(self) > len(other)):
            return False
        if len(self) == 0:  # Trivial case
            return True
        for (n, d) in self.nodes_iter(data=True):
            if not other.has_node(n):
                return False
            if d["state"] != other.node[n]["state"]:
                return False
        for e in self.edges_iter():
            if not other.has_edge(*e):
                return False
        return True

    def __eq__(self, other):
        """Automaton equality comparison.

        Two instances of Automaton are said to be equal if their nodes
        may be identified: there is a bijection, and nodes of equal ID
        agree on outgoing edge set and state (labelling).
        """
        if self.__le__(other) and other.__le__(self):
            return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return self.copy()

    def copy(self):
        """Return copy of this Automaton."""
        A = nx.DiGraph.copy(self)
        for n in A.nodes_iter():
            A.node[n]["state"] = A.node[n]["state"].copy()
        return A
        
    def loadSPINAut(self, aut_file, varnames=[], verbose=0):
        self.loadLinearAut(aut_file, '\(state (\d+)\)', '^\s*((?:\w+\(\d+\):)?\w+) = (\w+)',
                    "<<<<<START OF CYCLE>>>>>", varnames, verbose)
        
    def loadSMVAut(self, aut_file, varnames=[], verbose=0):
        self.loadLinearAut(aut_file, 'State: \d+\.(\d+)', '([\w.]+) = (\w+)',
                     "-- Loop starts here", varnames, verbose)
        
    def loadLinearAut(self, aut_file, state_regex, assign_regex, loop_text,
                    varnames=[], verbose=0):
        self.clear()  # By clearing now, we cannot recover in case of error
        
        try:
            f = open(aut_file, 'r')
            closable = True
        except IOError:
            logger.warn("Could not open " + aut_file + " for reading")
            return
        except TypeError:
            # assume aut_file is already a file object
            f = aut_file
            # don't close a file we didn't open
            closable = False
            
        nodeID = -1
        valuation = {}
        loopState = None
        val_change = True
        for (lineno, line) in enumerate(f, 1):
            if re.search(state_regex, line) is not None:
                # Only write a new state if the valuation has changed
                if val_change:
                    # conclude a previous state
                    if nodeID >= 0:
                        self.add_node(nodeID, state=valuation.copy(),
                                      mode=-1, rgrad=-1)
                        self.add_edge(nodeID, nodeID+1)
                    nodeID += 1
                val_change = False
            elif loop_text in line:
                loopState = nodeID + 1
            else:
                try:
                    # variable assignment
                    (var, val) = re.search(assign_regex, line).group(1,2)
                except AttributeError:
                    # probably a comment line, ignore
                    continue
                if varnames and not var in varnames:
                    logger.warn("Unknown variable " + var)
                try:
                    if var not in valuation or not valuation[var] == int(val):
                        val_change = True
                    valuation[var] = int(val)
                except:
                    if var not in valuation or not valuation[var] == val:
                        val_change = True
                    valuation[var] = val
        self.add_node(nodeID, state=valuation.copy(), mode=-1, rgrad=-1)
        if loopState is not None:
            self.add_edge(nodeID, loopState)
        else:
            self.remove_edges_from(self.successors(nodeID))
        if closable:
            f.close()

    def loadFile(self, aut_file, varnames=[], verbose=0):
        """
        Construct an automation from aut_file.

        Input:

        - `aut_file`: the name of the text file containing the
          automaton, or an (open) file-like object.

        - `varnames`: a list of all the variable names. If it is not empty, then this 
          function will also check whether the variables in aut_file are in varnames.
        """
        if isinstance(aut_file, str):
            f = open(aut_file, 'r')
            closable = True
        else:
            f = aut_file  # Else, assume aut_file behaves as file object.
            closable = False
        nodeID = -1
        for line in f:
            # parse states
            if (line.find('State ') >= 0):
                nodeID = re.search('State (\d+)', line)
                nodeID = int(nodeID.group(1))
                state = dict(re.findall('(\w+):(\w+)', line))
                for var, val in state.iteritems():
                    try:
                        state[var] = int(val)
                    except:
                        state[var] = val
                    if (len(varnames) > 0):
                        if not var in varnames:
                            logger.warn("Unknown variable " + var)
                if (len(state.keys()) < len(varnames)):
                    for var in varnames:
                        var_found = False
                        for var2 in state.keys():
                            if (var == var2):
                                var_found = True
                        if (not var_found):
                            logger.warn("Variable "+var+" not assigned")
                self.add_node(nodeID, state=state, mode=-1, rgrad=-1)

            # parse transitions
            if (line.find('successors') >= 0):
                transition = re.findall(' (\d+)', line)
                for i in xrange(0,len(transition)):
                    self.add_edge(nodeID, int(transition[i]))
        if closable:
            f.close()


    def writeFile(self, destfile):
        """
        Write an aut file that is readable by 'self.loadFile'. Note that this
        is not a true automaton file.
        
        Input:
        
        - 'destfile': the file name to be written to.
        """
        output = ""
        for (n, d) in self.nodes_iter(data=True):
            output += 'State ' + str(n) + ' with rank # -> <'
            for (k, v) in d["state"].items():
                output += str(k) + ':' + str(v) + ', '
            succ = self.successors(n)
            if len(succ) == 0:
                output += '>\n	With no successors.\n'
            else:
                output = output[:-2] + '>\n	With successors : '
                output += str(succ)[1:-1] + '\n'
        
        print 'Writing output to %s.' % destfile
        f = open(destfile, 'w')
        f.write(output)


    def trimDeadStates(self):
        """Recursively delete states with no outgoing transitions.
        """
        changed = True
        while changed:
            changed = False
            for n in self.nodes_iter():
                if self.out_degree(n) == 0:
                    self.remove_node(n)
                    changed = True
                    break

    def trimUnconnectedStates(self, aut_state_id):
        """Delete all states that are inaccessible from the given state.
        """
        # Delete nodes that are unconnected to 'aut_state_id'.
        # N.B., weak connectivity.
        comp = nx.node_connected_component(nx.Graph(self), aut_state_id)
        self.remove_nodes_from(set(self.nodes())-set(comp))

    def writeDotFileEdged(self, fname, env_vars, sys_vars,
                          hideZeros=False, hideAgentNames=True):
        """Write edge-labeled automaton to Graphviz DOT file.

        I forked the method writeDotFile for fear of feature creep.
        At least now the features will creep upon us from separate
        methods, rather than a single complicated argument list.

        env_vars and sys_vars should be lists of variable names (type
        string) describing environment and system variables,
        respectively.

        The intent is to view nodes labeled with a system decision,
        and edges labeled with an environment decision, thus better
        expressing the game.  Recall the automaton is a strategy.

        Return False on failure; True otherwise (success).
        """
        if len(env_vars) == 0 or len(sys_vars) == 0:
            return False

        # Make looping possible
        agents = {"env" : env_vars,
                  "sys" : sys_vars}
        
        output = "digraph A {\n"

        # Prebuild sane state names
        state_labels = dict()
        for (node, label) in self.nodes_iter(data=True):
            for agent_name in agents.keys():
                state_labels[str(node)+agent_name] = ''
            for (k,v) in label["state"].items():
                if (not hideZeros) or (v != 0):
                    agent_name = None
                    for agent_candidate in agents.keys():
                        if k in agents[agent_candidate]:
                            agent_name = agent_candidate
                            break
                    if agent_name is None:
                        logger.warn("variable \""+k+"\" does not belong to an agent in distinguishedTurns")
                        return False

                    if len(state_labels[str(node)+agent_name]) == 0:
                        if len(agent_name) > 0 and not hideAgentNames:
                            state_labels[str(node)+agent_name] += str(node)+"::"+agent_name+";\\n" + k+": "+str(v)
                        else:
                            state_labels[str(node)+agent_name] += str(node)+";\\n" + k+": "+str(v)
                    else:
                        state_labels[str(node)+agent_name] += ", "+k+": "+str(v)
            
            for agent_name in agents.keys():
                if len(state_labels[str(node)+agent_name]) == 0:
                    if not hideAgentNames:
                        state_labels[str(node)+agent_name] = str(node)+"::"+agent_name+";\\n {}"
                    else:
                        state_labels[str(node)+agent_name] = str(node)+";\\n {}"

        # Initialization point
        output += "    \"\" [shape=circle,style=filled,color=black];\n"
        
        # All nodes and edges
        for node in self.nodes_iter():
            if len(self.getAutInSet(node)) == 0:
                # Treat init nodes specially
                output += "    \"\" -> \"" \
                    + state_labels[str(node)+"sys"] +"\" [label=\""
                output += state_labels[str(node)+"env"] + "\"];\n"
            for next_node in self.successors_iter(node):
                output += "    \""+ state_labels[str(node)+"sys"] +"\" -> \"" \
                    + state_labels[str(next_node)+"sys"] +"\" [label=\""
                output += state_labels[str(next_node)+"env"] + "\"];\n"

        output += "\n}\n"
        with open(fname, "w") as f:
            f.write(output)
        return True


    def dumpDOTcolor(self, hideZeros=False, mode_colors=None,
                     node_attrib=False, env_vars=None, sys_vars=None):
        """Fork of dumpDOT with support for coloring nodes based on mode.

        @param mode_colors: a dictionary with keys of goal modes and
                 values of red-green-blue triplets, where each
                 component color range is 0 through 1.  If mode_colors
                 is None (the default), then a random color is
                 selected for each mode.

        @param node_attrib: flag (Boolean) whether to include extra
                 node attributes; specifically, the label includes (m,r)
                 following the node ID, where m is goal mode and r is
                 reach annotation value.
        """
        output = "digraph A {\n"

        # Prebuild sane state names
        state_labels = dict()
        for node, ndata in self.nodes_iter(data=True):
            state_labels[str(node)] = ''
            if env_vars is None and sys_vars is None:
                kv_list = ndata["state"].items()
            else:
                if env_vars is None:
                    env_vars = []
                if sys_vars is None:
                    sys_vars = []
                kv_list = []
                for v in env_vars+sys_vars:
                    kv_list.append((v, ndata["state"][v]))
            for (k,v) in kv_list:
                if (not hideZeros) or (v != 0):
                    agent_name = ''
                    if len(state_labels[str(node)+agent_name]) == 0:
                        if len(agent_name) > 0:
                            if node_attrib:
                                state_labels[str(node)+agent_name] += str(node)+" ("+str(ndata["mode"])+", "+str(ndata["rgrad"])+")::"+agent_name+";\\n" + k+": "+str(v)
                            else:
                                state_labels[str(node)+agent_name] += str(node)+"::"+agent_name+";\\n" + k+": "+str(v)
                        else:
                            if node_attrib:
                                state_labels[str(node)+agent_name] += str(node)+" ("+str(ndata["mode"])+", "+str(ndata["rgrad"])+");\\n" + k+": "+str(v)
                            else:
                                state_labels[str(node)+agent_name] += str(node)+";\\n" + k+": "+str(v)
                    else:
                        state_labels[str(node)+agent_name] += ", "+k+": "+str(v)
            if len(state_labels[str(node)]) == 0:
                if node_attrib:
                    state_labels[str(node)] = str(node)+" ("+str(ndata["mode"])+", "+str(ndata["rgrad"])+");\\n {}"
                else:
                    state_labels[str(node)] = str(node)+";\\n {}"

        if mode_colors is None:
            mode_colors = dict()
        for node, ndata in self.nodes_iter(data=True):
            if ndata["mode"] not in mode_colors.keys():
                mode_colors[ndata["mode"]] = (np.random.rand(), np.random.rand(), np.random.rand())
                mode_colors[ndata["mode"]] = (mode_colors[ndata["mode"]][0]/max(mode_colors[ndata["mode"]]), mode_colors[ndata["mode"]][1]/max(mode_colors[ndata["mode"]]), mode_colors[ndata["mode"]][2]/max(mode_colors[ndata["mode"]]))
        for (mode, mcolor) in mode_colors.items():
            print "Goal mode "+str(mode)+" color: "+str(mcolor[0])+" "+str(mcolor[1])+" "+str(mcolor[2])
        for node, ndata in self.nodes_iter(data=True):
            
            output += "    \""+ state_labels[str(node)] +"\" [style=filled,color=\""+str(mode_colors[ndata["mode"]][0])+" "+str(mode_colors[ndata["mode"]][1])+" "+str(mode_colors[ndata["mode"]][2])+"\"];\n"
            for next_node in self.successors_iter(node):
                output += "    \""+ state_labels[str(node)] +"\" -> \"" \
                    + state_labels[str(next_node)] +"\";\n"

        output += "\n}\n"
        return output

    def writeDotFileColor(self, fname, hideZeros=False, mode_colors=None,
                          node_attrib=False, env_vars=None, sys_vars=None):
        """Wrap dumpDOTcolor, redirecting its output to a file called fname.

        See docstrings of L{dumpDOTcolor} and L{dumpDOT} for details.
        """
        with open(fname, "w") as f:
            f.write(self.dumpDOTcolor(hideZeros=hideZeros, mode_colors=mode_colors, node_attrib=node_attrib, env_vars=env_vars, sys_vars=sys_vars))
        return True


    def dumpDOT(self, hideZeros=False, distinguishTurns=None, turnOrder=None,
                env_vars=None, sys_vars=None):
        """Dump automaton to string in Graphviz DOT format.

        In each state, the node ID and nonzero variables and their
        value (in that state) are listed.  This style is motivated by
        Boolean variables, but applies to all variables, including
        those taking arbitrary integer values.

        N.B., to allow for trace memory (manifested as ``rank'' in
        JTLV output), we include an ID for each node.  Thus, identical
        valuation of variables does *not* imply state equivalency
        (confusingly).

        If hideZeros is True, then for each vertex (in the DOT
        diagram) variables taking the value 0 are *not* shown.  This
        may lead to more succinct diagrams when many boolean variables
        are involved.  The default if False, i.e. show all variable
        values.

        It is possible to break states into a linear sequence of steps
        for visualization purposes using the argument
        distinguishTurns.  If not None, distinguishTurns should be a
        dictionary with keys as strings indicating the agent
        (e.g. "env" and "sys"), and values as lists of variable names
        that belong to that agent.  These lists should be disjoint.
        Note that variable names are case sensitive!

        If distinguishTurns is not None, state labels (in the DOT
        digraph) now have a preface of the form ID::agent, where ID is
        the original state identifier and "agent" is a key from
        distinguishTurns.

        N.B., if distinguishTurns is not None and has length 1, it is
        ignored (i.e. treated as None).

        turnOrder is only applicable if distinguishTurns is not None.
        In this case, if turnOrder is None, then use whatever order is
        given by default when listing keys of distinguishTurns.
        Otherwise, if turnOrder is a list (or list-like), then each
        element is key into distinguishTurns and state decompositions
        take that order.

        The order in which variables are printed can be fixed by
        passing env_vars and sys_vars as lists of variable names
        (strings).  If only one of env_vars or sys_vars is given, then
        the other is assumed empty.

        Return the resulting string.  Raise exception on failure.
        Note that dumpDOT returns True or False depending on the
        occurrence of a ValueError exception.
        """
        if (distinguishTurns is not None) and (len(distinguishTurns) <= 1):
            # This is a fringe case and seemingly ok to ignore.
            distinguishTurns = None

        output = "digraph A {\n"

        # Prebuild sane state names
        state_labels = dict()
        for (node, label) in self.nodes_iter(data=True):
            if distinguishTurns is None:
                state_labels[str(node)] = ''
            else:
                # If distinguishTurns is not a dictionary with
                # items of the form string -> list, it should
                # simulate that behavior.
                for agent_name in distinguishTurns.keys():
                    state_labels[str(node)+agent_name] = ''
            if env_vars is None and sys_vars is None:
                kv_list = label["state"].items()
            else:
                if env_vars is None:
                    env_vars = []
                if sys_vars is None:
                    sys_vars = []
                kv_list = []
                for v in env_vars+sys_vars:
                    kv_list.append((v, label["state"][v]))
            for (k,v) in kv_list:
                if (not hideZeros) or (v != 0):
                    if distinguishTurns is None:
                        agent_name = ''
                    else:
                        agent_name = None
                        for agent_candidate in distinguishTurns.keys():
                            if k in distinguishTurns[agent_candidate]:
                                agent_name = agent_candidate
                                break
                        if agent_name is None:
                            raise ValueError("variable \""+k+"\" does not belong to an agent in distinguishedTurns")

                    if len(state_labels[str(node)+agent_name]) == 0:
                        if len(agent_name) > 0:
                            state_labels[str(node)+agent_name] += str(node)+"::"+agent_name+";\\n" + k+": "+str(v)
                        else:
                            state_labels[str(node)+agent_name] += str(node)+";\\n" + k+": "+str(v)
                    else:
                        state_labels[str(node)+agent_name] += ", "+k+": "+str(v)
            if distinguishTurns is None:
                if len(state_labels[str(node)]) == 0:
                    state_labels[str(node)] = str(node)+";\\n {}"
            else:
                for agent_name in distinguishTurns.keys():
                    if len(state_labels[str(node)+agent_name]) == 0:
                        state_labels[str(node)+agent_name] = str(node)+"::"+agent_name+";\\n {}"

        if (distinguishTurns is not None) and (turnOrder is None):
            if distinguishTurns is not None:
                turnOrder = distinguishTurns.keys()
        for node in self.nodes_iter():
            if distinguishTurns is not None:
                output += "    \""+ state_labels[str(node)+turnOrder[0]] +"\" -> \"" \
                    + state_labels[str(node)+turnOrder[1]] +"\";\n"
                for agent_ind in range(1, len(turnOrder)-1):
                    output += "    \""+ state_labels[str(node)+turnOrder[agent_ind]] +"\" -> \"" \
                        + state_labels[str(node)+turnOrder[agent_ind+1]] +"\";\n"
            for next_node in self.successors_iter(node):
                if distinguishTurns is None:
                    output += "    \""+ state_labels[str(node)] +"\" -> \"" \
                        + state_labels[str(next_node)] +"\";\n"
                else:
                    output += "    \""+ state_labels[str(node)+turnOrder[-1]] +"\" -> \"" \
                        + state_labels[str(next_node)+turnOrder[0]] +"\";\n"

        output += "\n}\n"
        return output


    def writeDotFile(self, fname, hideZeros=False,
                     distinguishTurns=None, turnOrder=None,
                     env_vars=None, sys_vars=None):
        """Wrap dumpDOT, redirecting its output to a file called fname.

        See docstring of L{dumpDOT} for details.
        """
        try: 
            with open(fname, "w") as f:
                f.write(self.dumpDOT(hideZeros=hideZeros,
                                     distinguishTurns=distinguishTurns, turnOrder=turnOrder,
                                     env_vars=env_vars, sys_vars=sys_vars))
        except ValueError:
            return False
        return True

    def dumpgr1c(self, env_vars, sys_vars):
        """Return string conforming to "gr1c automaton" format.
        """
        output = "1\n"  # version 1 of the format
        for (node, label) in self.nodes_iter(data=True):
            output += str(node)
            for v in env_vars:
                output += " "+str(label["state"][v])
            for v in sys_vars:
                output += " "+str(label["state"][v])
            output += " "+str(label["initial"])+" "+str(label["mode"])+" "+str(label["rgrad"])
            for out_node in self.successors_iter(node):
                output += " "+str(out_node)
            output += "\n"
        return output
    
    def dumpXML(self, pretty=True, idt_level=0):
        """Return string of automaton conforming to tulipcon XML, version 1

        If pretty is True, then use indentation and newlines to make
        the resulting XML string more visually appealing.  idt_level
        is the base indentation level on which to create automaton
        string.  This level is only relevant if pretty=True.

        Note that the <anno> element is used to store the goal mode
        and reach annotation value of each node.  This usage is
        experimental; if it is shown to be useful, a dedicated element
        will be introduced into the XML Schema.
        """
        if pretty:
            nl = "\n"  # Newline
            idt = "  "  # Indentation
        else:
            nl = ""
            idt = ""
        output = idt_level*idt+'<aut type="basic">'+nl
        idt_level += 1
        for (node, label) in self.nodes_iter(data=True):
            output += idt_level*idt+'<node>'+nl
            idt_level += 1
            output += idt_level*idt+'<id>' + str(node) + '</id><anno>'+str(label["mode"])+' '+str(label["rgrad"])+'</anno>'+nl
            output += idt_level*idt+conxml.taglist("child_list", self.successors(node))+nl
            output += idt_level*idt+conxml.tagdict("state", label["state"])+nl
            idt_level -= 1
            output += idt_level*idt+'</node>'+nl
        idt_level -= 1
        output += idt_level*idt+'</aut>'+nl
        return output

    def loadXML(self, x, namespace="", version=1):
        """Read an automaton from given tulipcon XML string, versions 0 or 1
        
        N.B., on a successful processing of the given string, the
        original Automaton instance to which this method is attached
        is replaced with the new structure.  On failure, however, the
        original Automaton is untouched.

        The argument x can also be an instance of
        xml.etree.ElementTree._ElementInterface ; this is mainly for
        internal use, e.g. by the function untagpolytope and some
        load/dumpXML methods elsewhere.

        For each node, if two integers are found in the <name>
        element, then they are treated as the goal mode and
        reach annotation value, in that order; otherwise, the
        goal mode and reach annotation value are both set to -1.
        This usage is experimental; if it is shown to be useful, a
        dedicated element will be introduced into the XML Schema.
        
        Return True on success; on failure, return False or raise
        exception.
        """
        if not isinstance(x, str) and not isinstance(x, ET._ElementInterface):
            raise ValueError("given automaton XML must be a string or ElementTree._ElementInterface.")
        if version not in [0, 1]:
            raise ValueError("only tulipcon XML versions 0 and 1 are supported.")

        if (namespace is None) or (len(namespace) == 0):
            ns_prefix = ""
        else:
            ns_prefix = "{"+namespace+"}"

        if isinstance(x, str):
            etf = ET.fromstring(x)
        else:
            etf = x
        if etf.tag != ns_prefix+"aut":
            raise ValueError("loadXML invoked with root tag other than <aut>.")

        if version == 1:
            if etf.attrib["type"] != "basic":
                raise ValueError("Automaton class only recognizes type \"basic\".")

        node_list = etf.findall(ns_prefix+"node")
        id_list = []  # For more convenient searching, and to catch redundancy
        A = nx.DiGraph()
        for node in node_list:
            this_id = int(node.find(ns_prefix+"id").text)
            logger.debug("Automaton.loadXML: parsing node with ID "+str(this_id))
            if version == 0:
                this_name = node.find(ns_prefix+"name").text
                (tag_name, this_name_list) = conxml.untaglist(node.find(ns_prefix+"name"),
                                                              cast_f=int)
            else: # version == 1
                this_name = node.find(ns_prefix+"anno").text
                (tag_name, this_name_list) = conxml.untaglist(node.find(ns_prefix+"anno"),
                                                              cast_f=int)
            if len(this_name_list) == 2:
                (mode, rgrad) = this_name_list
            else:
                (mode, rgrad) = (-1, -1)
            (tag_name, this_child_list) = conxml.untaglist(node.find(ns_prefix+"child_list"),
                                                           cast_f=int)
            if tag_name != ns_prefix+"child_list":
                # This really should never happen and may not even be
                # worth checking.
                raise ValueError("failure of consistency check while processing aut XML string.")
            (tag_name, this_state) = conxml.untagdict(node.find(ns_prefix+"state"),
                                                      cast_f_values=int,
                                                      namespace=namespace)

            if tag_name != ns_prefix+"state":
                raise ValueError("failure of consistency check while processing aut XML string.")
            if this_id in id_list:
                logger.warn("duplicate nodes found: "+str(this_id)+"; ignoring...")
                continue
            id_list.append(this_id)
            A.add_node(this_id, state=copy.copy(this_state),
                       mode=mode, rgrad=rgrad)
            for next_node in this_child_list:
                A.add_edge(this_id, next_node)

        self.clear()  # Finally, commit.
        self.add_nodes_from(A.nodes(data=True))
        self.add_edges_from(A.edges())
        return True

    def loadJSON(self, json_aut):
        """gr1c JSON format"""

        A = Automaton()
        id_map = dict()
        for i, node_ID in enumerate(json_aut["nodes"].iterkeys()):
            id_map[node_ID] = i
        for node_ID in json_aut["nodes"].iterkeys():
            node_label = dict([(k, json_aut["nodes"][node_ID][k]) \
                               for k in ("mode", "rgrad")])
            node_label["initial"] = 1 if json_aut["nodes"][node_ID]["initial"] else 0
            node_label["state"] = dict()
            i = 0
            for ev in json_aut["ENV"]:
                node_label["state"][ev.keys()[0]] = json_aut["nodes"][node_ID]["state"][i]
                i += 1
            for sv in json_aut["SYS"]:
                node_label["state"][sv.keys()[0]] = json_aut["nodes"][node_ID]["state"][i]
                i += 1
            A.add_node(id_map[node_ID], node_label)
        for node_id in json_aut["nodes"].iterkeys():
            for to_node in json_aut["nodes"][node_id]["trans"]:
                A.add_edge(id_map[node_id], id_map[to_node])

        # Finally, commit
        self.clear()
        self.add_nodes_from(A.nodes(data=True))
        self.add_edges_from(A.edges())
        return True

    def size(self):
        return self.__len__()

    def addAutState(self, node_id, state, transitions, mode=-1, rgrad=-1):
        """Add a node to this automaton.

        Not really needed given methods provided by NetworkX DiGraph class,
        but included for backwards support of old TuLiP usage.
        """
        self.add_node(node_id, state=copy.copy(state), mode=mode, rgrad=rgrad)
        for next_node in transitions:
            self.add_edge(node_id, next_node)

    def getAutInSet(self, aut_state_id):
        """Find all nodes that include given ID in their outward transitions.

        Merely wraps predecessors() method of NetworkX DiGraph class
        Return list of nodes (each as an integer "ID"), or None on error.
        """
        if not self.has_node(aut_state_id):
            return None
        return self.predecessors(aut_state_id)

    def findAllAutState(self, state):
        """Return all nodes labeled with given state.

        Input:

        - `state`: a dictionary whose keys are the names of the variables
          and whose values are the values of the variables.
        """
        matching_nodes = []
        for (n,d) in self.nodes_iter(data=True):
            if d["state"] == state:
                matching_nodes.append(n)
        return matching_nodes

    def getAutInit(self):
        """Return list of nodes that are initial, i.e., have empty In set.

        N.B., the set of initial nodes is not saved, so every time you
        call getAutInit, all nodes are checked for empty inward edge
        sets, which itself incurs a search cost (cf. doc for method
        getAutInSet).
        """
        init_nodes = []
        for n in self.nodes_iter():
            if self.in_degree(n) == 0:
                init_nodes.append(n)
        return init_nodes

    def findAllAutPartState(self, state_frag):
        """Return list of nodes consistent with the given fragment.

        state_frag should be a dictionary.  We say the state in a node
        is "consistent" with the fragment if for every variable
        appearing in state_frag, the valuations in state_frag and the
        node are the same.

        E.g., let aut be an instance of Automaton.  Then
        aut.findAllAutPartState({"foobar" : 1}) would return a list of
        nodes (each as an integer "ID") in which the variable
        "foobar" is 1 (true).
        """
        matching_nodes = []
        for (n,d) in self.nodes_iter(data=True):
            match_flag = True
            for k in state_frag.items():
                if k not in d["state"].items():
                    match_flag = False
                    break
            if match_flag:
                matching_nodes.append(n)
        return matching_nodes

    def findAutState(self, state):
        """Return first node with given state label; if none, return -1.

        Input:

        - `state`: a dictionary whose keys are the names of the variables
          and whose values are the values of the variables.
          """
        for (n,d) in self.nodes_iter(data=True):
            if d["state"] == state:
                return n
        return -1

    def findNextAutState(self, current_aut_state, env_state={},
                         deterministic_env=True):
        """Return the next node based on `env_state`, or -1 if none found.

        Input:

        - `current_aut_state`: the current node (as an integer
          "ID"). Use current_aut_state = None for unknown current or
          initial automaton state.

        - `env_state`: a dictionary whose keys are the names of the
          environment variables and whose values are the values of the
          variables.

        - 'deterministic_env': specifies whether to choose the
          environment state deterministically.
        """
        if current_aut_state is None:
            transition = range(self.size())
        else:
            transition = self.successors(current_aut_state)
        
        def stateSatisfiesEnv(next_aut_id):
            for var in env_state.keys():
                if not (self.node[next_aut_id]["state"][var] == env_state[var]):
                    return False
            return True
        transition = filter(stateSatisfiesEnv, transition)
        
        if len(transition) == 0:
            return -1
        elif (deterministic_env):
            return transition[0]
        else:
            return random.choice(transition)
            
    def stripNames(self):
        for n in self.nodes_iter():
            for k in self.node[n]["state"].keys():
                stripped = k.split(".")[-1]
                self.node[n]["state"][stripped] = self.node[n]["state"][k]
                del(self.node[n]["state"][k])

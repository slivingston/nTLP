# Copyright (c) 2011, 2012 by California Institute of Technology
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
# 
# $Id$
""" 
----------------
Automaton Module
----------------
"""

import re, copy, os, random
import xml.etree.ElementTree as ET

from errorprint import printWarning, printError
import conxml

try:
    from pygraph.classes.digraph import digraph
    from pygraph.algorithms.accessibility import connected_components
except ImportError:
    print "python-graph package not found.\nHence some methods in Automaton class are unavailable."
    # python-graph package not found. Disable dependent methods.
    digraph = None
    connected_components = None
    

###################################################################

class AutomatonState:
    """AutomatonState class for representing a state in a finite state
    automaton.  An AutomatonState object contains the following
    fields:

    - `id`: an integer specifying the id of this AutomatonState object.
    - `state`: a dictionary whose keys are the names of the variables
      and whose values are the values of the variables.
    - `transition`: a list of id's of the AutomatonState objects to
      which this AutomatonState object can transition.
    """
    def __init__(self, id=-1, state={}, transition=[]):
        self.id = id
        self.state = copy.copy(state)
        self.transition = transition[:]
    def __repr__(self):
        return "State: " + str(self.state) + "\n" + \
                "Transitions: " + str(self.transition)

    def __copy__(self):
        return AutomatonState(self.id, self.state, self.transition)
        
    def copy(self):
        """Return copy of this automaton node."""
        return self.__copy__()


###################################################################

class Automaton:
    """Automaton class for representing a finite state automaton.
    An Automaton object contains the following field:

    - `states`: a list of AutomatonState objects.

    Automaton([states_or_file, varname, verbose]) constructs an
    Automaton object based on the following input:

    - `states_or_file`: a string containing the name of the aut file
      to be loaded or a list of AutomatonState objects to be assigned
      to the `states` of this Automaton object, or an (open) file-like
      object.

    - `varname`: a list of all the variable names. If it is not empty
      and states_or_file is a string representing the name of the aut
      file to be loaded, then this function will also check whether
      the variables in aut_file are in varnames.
    """
    def __init__(self, states_or_file=[], varnames=[], verbose=0):
        # Construct this automaton from a list of AutomatonState objects
        if (isinstance(states_or_file, list)): 
            self.states = copy.deepcopy(states_or_file)
        # Construct this automaton from file
        else:
            if isinstance(states_or_file, str) and (len(states_or_file) == 0):
                self.states = []
            else:
                self.loadFile(states_or_file, varnames=varnames, verbose=verbose)

    def __eq__(self, other):
        """Automaton equality comparison.

        Two instances of Automaton are said to be equal if their nodes
        may be identified: there is a bijection, and nodes of equal ID
        agree on outgoing edge set and state (labelling).
        """
        if (not isinstance(other, Automaton)) or (len(self) != len(other)):
            return False
        if len(self) == 0: # Trivial case, both empty
            return True
        for node in self.states:
            other_ind = 0
            while (other.states[other_ind].id != node.id) and (other_ind < len(other)):
                other_ind += 1
            if other_ind >= len(other):
                return False
            sorted_transition = node.transition[:]
            sorted_transition.sort()
            other_sorted_transition = other.states[other_ind].transition[:]
            other_sorted_transition.sort()
            if sorted_transition != other_sorted_transition:
                return False
            if node.state.items() != other.states[other_ind].state.items():
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        """Return number of nodes."""
        return len(self.states)

    def __copy__(self):
        return Automaton(states_or_file=[s.copy() for s in self.states])

    def copy(self):
        """Return copy of this Automaton."""
        return self.__copy__()
        
    def loadSPINAut(self, aut_file, varnames=[], verbose=0):
        self.loadLinearAut(aut_file, '\(state (\d+)\)', '^\s*((?:\w+\(\d+\):)?\w+) = (\w+)',
                    "<<<<<START OF CYCLE>>>>>", varnames, verbose)
        
    def loadSMVAut(self, aut_file, varnames=[], verbose=0):
        self.loadLinearAut(aut_file, 'State: \d+\.(\d+)', '([\w.]+) = (\w+)',
                     "-- Loop starts here", varnames, verbose)
        
    def loadLinearAut(self, aut_file, state_regex, assign_regex, loop_text,
                    varnames=[], verbose=0):
        self.states = []
        
        try:
            f = open(aut_file, 'r')
            closable = True
        except IOError:
            printWarning("Could not open " + aut_file + " for reading")
            return
        except TypeError:
            # assume aut_file is already a file object
            f = aut_file
            # don't close a file we didn't open
            closable = False
            
        stateID = -1
        valuation = {}
        loopState = None
        val_change = True
        for (lineno, line) in enumerate(f, 1):
            if re.search(state_regex, line) is not None:
                # Only write a new state if the valuation has changed
                if val_change:
                    # conclude a previous state
                    if stateID >= 0:
                        self.setAutStateState(stateID, valuation, verbose)
                        self.setAutStateTransition(stateID, [stateID+1], verbose)
                    stateID += 1
                val_change = False
                #try:
                #    stateID = int(stateID.group(1)) - 1 # start numbering from 0
                #except:
                #    printWarning("SMV aut parsing failed on line " + str(lineno) +
                #                ":\n\t" + line)
                #    return
            elif loop_text in line:
                loopState = stateID + 1
            else:
                try:
                    # variable assignment
                    (var, val) = re.search(assign_regex, line).group(1,2)
                except AttributeError:
                    # probably a comment line, ignore
                    continue
                if varnames and not var in varnames:
                    printWarning('Unknown variable ' + var, obj=self)
                try:
                    if var not in valuation or not valuation[var] == int(val):
                        val_change = True
                    valuation[var] = int(val)
                except:
                    if var not in valuation or not valuation[var] == val:
                        val_change = True
                    valuation[var] = val
        self.setAutStateState(stateID, valuation, verbose)
        if loopState is not None:
            self.setAutStateTransition(stateID, [loopState], verbose)
        else:
            self.setAutStateTransition(stateID, [], verbose)
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
        self.states = []
        if isinstance(aut_file, str):
            f = open(aut_file, 'r')
            closable = True
        else:
            f = aut_file  # Else, assume aut_file behaves as file object.
            closable = False
        stateID = -1
        for line in f:
            # parse states
            if (line.find('State ') >= 0):
                stateID = re.search('State (\d+)', line)
                stateID = int(stateID.group(1))
                state = dict(re.findall('(\w+):(\w+)', line))
                for var, val in state.iteritems():
                    try:
                        state[var] = int(val)
                    except:
                        state[var] = val
                    if (len(varnames) > 0):
                        if not var in varnames:
                            printWarning('Unknown variable ' + var, obj=self)
                for var in varnames:
                    if not var in state.keys():
                        printWarning('Variable ' + var + ' not assigned', obj=self)
                self.setAutStateState(stateID, state, verbose)

            # parse transitions
            if (line.find('successors') >= 0):
                transition = re.findall(' (\d+)', line)
                for i in xrange(0,len(transition)):
                    transition[i] = int(transition[i])
                self.setAutStateTransition(stateID, list(set(transition)), verbose)
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
        for state in self.states:
            output += 'State ' + str(state.id) + ' with rank # -> <'
            for (k, v) in state.state.items():
                output += str(k) + ':' + str(v) + ', '
            if state.transition == []:
                output += '>\n	With no successors.\n'
            else:
                output = output[:-2] + '>\n	With successors : '
                output += str(state.transition)[1:-1] + '\n'
        
        print 'Writing output to %s.' % destfile
        f = open(destfile, 'w')
        f.write(output)
                      

    def trimRedundantStates(self):
        """DEFUNCT UNTIL FURTHER NOTICE!

        Combine states whose valuation of variables is identical

        Merge and update transition listings as needed.  N.B., this
        method will change IDs after trimming to ensure indexing still
        works (since self.states attribute is a list).

        Return False on failure; True otherwise (success).
        """
        if len(self.states) == 0:
            return True  # Empty state set; do nothing
        for current_id in range(len(self.states)):
            # See if flag set, i.e. this state already processed as duplicate
            if self.states[current_id].id == -1:
                continue
            # Look for duplicates
            dup_list = []
            for k in range(len(self.states)):
                if k == current_id:
                    continue
                if self.states[k].state == self.states[current_id].state:
                    dup_list.append(k)
            # Trim the fat; mark duplicate states as such (to be
            # deleted after search finishes).
            if len(dup_list) != 0:
                for state in self.states:
                    for trans_ind in range(len(state.transition)):
                        if state.transition[trans_ind] in dup_list:
                            state.transition[trans_ind] = current_id
                for k in dup_list:
                    self.states[current_id].transition.extend(self.states[k].transition)
                    self.states[k].id = -1  # Flag for deletion
                self.states[current_id].transition = list(set(self.states[current_id].transition))
        # Delete flagged (redundant) states
        current_id = 0
        while current_id < len(self.states):
            if self.states[current_id].id == -1:
                del self.states[current_id]
            else:
                current_id += 1
        # Shift down other IDs, which are off-place due to the deletions
        for current_id in range(len(self.states)):
            if self.states[current_id].id == current_id:
                continue
            for state in self.states:
                for trans_ind in range(len(state.transition)):
                    if state.transition[trans_ind] == self.states[current_id].id:
                        state.transition[trans_ind] = current_id
            self.states[current_id].id = current_id
        # Finally, remove any remaining redundant references in
        # transition lists.
        for current_id in range(len(self.states)):
            self.states[current_id].transition = list(set(self.states[current_id].transition))
        return True


    def trimDeadStates(self):
        """
        Recursively delete states with no outgoing transitions.

        Merge and update transition listings as needed.  N.B., this
        method will change IDs after trimming to ensure indexing still
        works (since self.states attribute is a list).
        """
        if digraph is None:
            print "WARNING: attempted to call unavailable method trimDeadStates."
            return

        self.createPygraphRepr()
        
        # Delete nodes with no outbound transitions.
        changed = True  # Becomes False when no deletions have been made.
        while changed:
            changed = False
            for node in self.pygraph.nodes():
                if self.pygraph.neighbors(node) == []:
                    changed = True
                    self.pygraph.del_node(node)
        
        self.loadPygraphRepr()
        
    def trimUnconnectedStates(self, aut_state_id):
        """
        Delete all states that are inaccessible from the given state.
        
        Merge and update transition listings as needed.  N.B., this
        method will change IDs after trimming to ensure indexing still
        works (since self.states attribute is a list).
        """
        if connected_components is None:
            print "WARNING: attempted to call unavailable method trimUnconnectedStates."
            return

        self.createPygraphRepr()
        
        # Delete nodes that are unconnected to 'aut_state_id'.
        connected = connected_components(self.pygraph)
        main_component = connected[aut_state_id]
        for node in self.pygraph.nodes():
            if connected[node] != main_component:
                self.pygraph.del_node(node)
        
        self.loadPygraphRepr()

    def createPygraphRepr(self):
        """
        Generate a python-graph representation of this automaton, stored
        in 'self.pygraph'
        """
        if digraph is None:
            print "WARNING: attempted to call unavailable method createPygraphRepr."
            return

        # Create directed graph in pygraph.
        self.pygraph = digraph()
        
        # Add nodes to graph.
        for state in self.states:
            self.pygraph.add_node(state.id, state.state.items())
        
        # Add edges to graph.
        for state in self.states:
            for trans in state.transition:
                self.pygraph.add_edge((state.id, trans))
     
    def loadPygraphRepr(self):
        """
        Recreate automaton states from 'self.pygraph'.
        
        Merge and update transition listings as needed.  N.B., this
        method will change IDs after trimming to ensure indexing still
        works (since self.states attribute is a list).
        """
        if digraph is None:
            print "WARNING: attempted to call unavailable method loadPygraphRepr."
            return

        # Reorder nodes by setting 'new_state_id'.
        for (i, node) in enumerate(self.pygraph.nodes()):
            self.pygraph.add_node_attribute(node, ('new_state_id', i))
        
        # Recreate automaton from graph.
        self.states = []
        for node in self.pygraph.nodes():
            node_attr = dict(self.pygraph.node_attributes(node))
            id = node_attr.pop('new_state_id')
            transition = [dict(self.pygraph.node_attributes(neighbor))['new_state_id']
                          for neighbor in self.pygraph.neighbors(node)]
            self.states.append(AutomatonState(id=id, state=node_attr,
                                              transition=transition))
        

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
        for state in self.states:
            for agent_name in agents.keys():
                state_labels[str(state.id)+agent_name] = ''
            for (k,v) in state.state.items():
                if (not hideZeros) or (v != 0):
                    agent_name = None
                    for agent_candidate in agents.keys():
                        if k in agents[agent_candidate]:
                            agent_name = agent_candidate
                            break
                    if agent_name is None:
                        printWarning("variable \""+k+"\" does not belong to an agent in distinguishedTurns")
                        return False

                    if len(state_labels[str(state.id)+agent_name]) == 0:
                        if len(agent_name) > 0 and not hideAgentNames:
                            state_labels[str(state.id)+agent_name] += str(state.id)+"::"+agent_name+";\\n" + k+": "+str(v)
                        else:
                            state_labels[str(state.id)+agent_name] += str(state.id)+";\\n" + k+": "+str(v)
                    else:
                        state_labels[str(state.id)+agent_name] += ", "+k+": "+str(v)
            
            for agent_name in agents.keys():
                if len(state_labels[str(state.id)+agent_name]) == 0:
                    if not hideAgentNames:
                        state_labels[str(state.id)+agent_name] = str(state.id)+"::"+agent_name+";\\n {}"
                    else:
                        state_labels[str(state.id)+agent_name] = str(state.id)+";\\n {}"

        # Initialization point
        output += "    \"\" [shape=circle,style=filled,color=black];\n"
        
        # All nodes and edges
        for state in self.states:
            if len(self.getAutInSet(state.id)) == 0:
                # Treat init nodes specially
                output += "    \"\" -> \"" \
                    + state_labels[str(state.id)+"sys"] +"\" [label=\""
                output += state_labels[str(state.id)+"env"] + "\"];\n"
            for trans in state.transition:
                output += "    \""+ state_labels[str(state.id)+"sys"] +"\" -> \"" \
                    + state_labels[str(self.states[trans].id)+"sys"] +"\" [label=\""
                output += state_labels[str(self.states[trans].id)+"env"] + "\"];\n"

        output += "\n}\n"
        with open(fname, "w") as f:
            f.write(output)
        return True

    def writeDotFile(self, fname, hideZeros=False,
                     distinguishTurns=None, turnOrder=None):
        """Write automaton to Graphviz DOT file.

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

        Return False on failure; True otherwise (success).
        """
        if (distinguishTurns is not None) and (len(distinguishTurns) <= 1):
            # This is a fringe case and seemingly ok to ignore.
            distinguishTurns = None

        output = "digraph A {\n"

        # Prebuild sane state names
        state_labels = dict()
        for state in self.states:
            if distinguishTurns is None:
                state_labels[str(state.id)] = ''
            else:
                # If distinguishTurns is not a dictionary with
                # items of the form string -> list, it should
                # simulate that behavior.
                for agent_name in distinguishTurns.keys():
                    state_labels[str(state.id)+agent_name] = ''
            for (k,v) in state.state.items():
                if not (hideZeros and (v == 0 or v == "FALSE")):
                    if distinguishTurns is None:
                        agent_name = ''
                    else:
                        agent_name = None
                        for agent_candidate in distinguishTurns.keys():
                            if k in distinguishTurns[agent_candidate]:
                                agent_name = agent_candidate
                                break
                        if agent_name is None:
                            printWarning("variable \""+k+"\" does not belong to an agent in distinguishedTurns")
                            return False

                    if len(state_labels[str(state.id)+agent_name]) == 0:
                        if len(agent_name) > 0:
                            state_labels[str(state.id)+agent_name] += str(state.id)+"::"+agent_name+";\\n" + k+": "+str(v)
                        else:
                            state_labels[str(state.id)+agent_name] += str(state.id)+";\\n" + k+": "+str(v)
                    else:
                        state_labels[str(state.id)+agent_name] += ", "+k+": "+str(v)
            if distinguishTurns is None:
                if len(state_labels[str(state.id)]) == 0:
                    state_labels[str(state.id)] = str(state.id)+";\\n {}"
            else:
                for agent_name in distinguishTurns.keys():
                    if len(state_labels[str(state.id)+agent_name]) == 0:
                        state_labels[str(state.id)+agent_name] = str(state.id)+"::"+agent_name+";\\n {}"

        if (distinguishTurns is not None) and (turnOrder is None):
            if distinguishTurns is not None:
                turnOrder = distinguishTurns.keys()
        for state in self.states:
            if distinguishTurns is not None:
                output += "    \""+ state_labels[str(state.id)+turnOrder[0]] +"\" -> \"" \
                    + state_labels[str(state.id)+turnOrder[1]] +"\";\n"
                for agent_ind in range(1, len(turnOrder)-1):
                    output += "    \""+ state_labels[str(state.id)+turnOrder[agent_ind]] +"\" -> \"" \
                        + state_labels[str(state.id)+turnOrder[agent_ind+1]] +"\";\n"
            for trans in state.transition:
                if distinguishTurns is None:
                    output += "    \""+ state_labels[str(state.id)] +"\" -> \"" \
                        + state_labels[str(self.states[trans].id)] +"\";\n"
                else:
                    output += "    \""+ state_labels[str(state.id)+turnOrder[-1]] +"\" -> \"" \
                        + state_labels[str(self.states[trans].id)+turnOrder[0]] +"\";\n"

        output += "\n}\n"
        with open(fname, "w") as f:
            f.write(output)
        return True
    
    def dumpXML(self, pretty=True, idt_level=0):
        """Return string of automaton conforming to tulipcon XML.

        If pretty is True, then use indentation and newlines to make
        the resulting XML string more visually appealing.  idt_level
        is the base indentation level on which to create automaton
        string.  This level is only relevant if pretty=True.

        Note that name subtags within aut tag are left blank.
        """
        if pretty:
            nl = "\n"  # Newline
            idt = "  "  # Indentation
        else:
            nl = ""
            idt = ""
        output = idt_level*idt+'<aut>'+nl
        idt_level += 1
        for node in self.states:
            output += idt_level*idt+'<node>'+nl
            idt_level += 1
            output += idt_level*idt+'<id>' + str(node.id) + '</id><name></name>'+nl
            output += idt_level*idt+conxml.taglist("child_list", node.transition)+nl
            output += idt_level*idt+conxml.tagdict("state", node.state)+nl
            idt_level -= 1
            output += idt_level*idt+'</node>'+nl
        idt_level -= 1
        output += idt_level*idt+'</aut>'+nl
        return output

    def loadXML(self, x, namespace=""):
        """Read an automaton from given string conforming to tulipcon XML.
        
        N.B., on a successful processing of the given string, the
        original Automaton instance to which this method is attached
        is replaced with the new structure.  On failure, however, the
        original Automaton is untouched.

        The argument x can also be an instance of
        xml.etree.ElementTree._ElementInterface ; this is mainly for
        internal use, e.g. by the function untagpolytope and some
        load/dumpXML methods elsewhere.
        
        Return True on success; on failure, return False or raise
        exception.
        """
        if not isinstance(x, str) and not isinstance(x, ET._ElementInterface):
            raise ValueError("given automaton XML must be a string or ElementTree._ElementInterface.")

        if (namespace is None) or (len(namespace) == 0):
            ns_prefix = ""
        else:
            ns_prefix = "{"+namespace+"}"

        if isinstance(x, str):
            etf = ET.fromstring(x)
        else:
            etf = x
        if etf.tag != ns_prefix+"aut":
            return False

        node_list = etf.findall(ns_prefix+"node")
        states = []
        id_list = []  # For more convenient searching, and to catch redundancy
        for node in node_list:
            this_id = int(node.find(ns_prefix+"id").text)
            this_name = node.find(ns_prefix+"name").text
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
                printWarning("duplicate nodes found: "+str(this_id)+"; ignoring...")
                continue
            id_list.append(this_id)
            states.append(AutomatonState(id=this_id,
                                         state=copy.copy(this_state),
                                         transition=copy.copy(this_child_list)))
        
        # Sort the mess
        ordered_states = []
        num_states = len(states)
        for this_id in range(num_states):
            ind = 0
            while (ind < len(states)) and (states[ind].id != this_id):
                ind += 1
            if ind >= len(states):
                raise ValueError("missing states in automaton.")
            ordered_states.append(states.pop(ind))

        self.states = ordered_states  # Finally, commit.
        return True

    def size(self):
        return self.__len__()

    def addAutState(self, aut_state):
        """
        Add an AutomatonState object to this automaton.
        
        Input:

        - `aut_state`: an AutomatonState object to be added to this Automaton object.
        """
        if (isinstance(aut_state, AutomatonState)):
            self.states.append(aut_state)
        else:
            printError("Input to addAutState must be of type AutomatonState", obj=self)

    def getAutState(self, aut_state_id):
        """
        Return an AutomatonState object stored in this Automaton object 
        whose id is `aut_state_id`. 
        Raise IndexError if such AutomatonState object does not exist.

        Input:

        - `aut_state_id`: an integer specifying the id of the AutomatonState object
          to be returned by this function.
        """
        if (aut_state_id < self.size() and self.states[aut_state_id].id == aut_state_id):
            return self.states[aut_state_id]
        else:
            aut_state_index = self.size() - 1
            while (aut_state_index >= 0 and aut_state_id != self.states[aut_state_index].id):
                aut_state_index -= 1
            if (aut_state_index >= 0):
                return self.states[aut_state_index]
            else:
                raise IndexError("State ID " + str(aut_state_id) + " not found.")

    def getAutInSet(self, aut_state_id):
        """Find all nodes that include given ID in their outward transitions.

        If the automaton is viewed as a directed graph, and the given
        ID corresponds to node v, then we are interested in all v'\in V
        such that (v',v) is an edge in the graph.

        (Comments on efficiency.)  The automaton is stored as a tree,
        where parents connect to children as in a linked list. Thus
        given a node, finding the set of outward edges takes constant
        time, whereas finding the inward set (as done by this method)
        requires searching the set of nodes and their respective
        transition sets; so, O(N*M) time, where N is the number of
        nodes and M is the average number of outward edges.

        Return list of nodes (instances of AutomatonState),
        or None on error.
        """
        try:
            this_node = self.getAutState(aut_state_id)
        except IndexError:
            return None
        if not isinstance(this_node, AutomatonState):
            return None
        inward_list = []
        for k in range(len(self.states)):
            if aut_state_id in self.states[k].transition:
                inward_list.append(self.states[k])
        return inward_list
    
    def setAutStateState(self, aut_state_id, aut_state_state, verbose=0):
        """ 
        Set the state of the AutomatonState object whose id is `aut_state_id` to 
        `aut_state_state`.
        If such an AutomatoSstate object does not exist, an AutomatonState object 
        whose id is `aut_state_id` and whose state is `aut_state_state` will be added.

        Input:

        - `aut_state_id`: an integer that specifies the id of the AutomatonState 
          object to be set.
        - `aut_state_state`: a dictionary that represents the new state of the 
          AutomatonState object.
        """
        try:
            aut_state = self.getAutState(aut_state_id)
            aut_state.state = aut_state_state
            if (verbose > 0):
                print 'Setting state of AutomatonState ' + str(aut_state_id) + \
                    ': ' + str(aut_state_state)
        except IndexError:
            # State does not already exist, add it
            self.addAutState(AutomatonState(id=aut_state_id, state=aut_state_state, \
                                                transition=[]))
            if (verbose > 0):
                print 'Adding state ' + str(aut_state_id) + ': ' + str(aut_state_state)
    
    def setAutStateTransition(self, aut_state_id, aut_state_transition, verbose=0):
        """
        Set the transition of the AutomatonState object whose id is `aut_state_id` to 
        `aut_state_transition`. If such automaton state does not exist, an 
        AutomatonState whose id is aut_state_id and whose transition is 
        aut_state_transition will be added.

        Input:

        - `aut_state_id`: an integer that specifies the id of the AutomatonState 
          object to be set.
        - `aut_state_transition`: a list of id's of the AutomatonState objects to which 
          the AutomatonState object with id `aut_state_id` can transition.
        """
        aut_state = self.getAutState(aut_state_id)
        if (isinstance(aut_state, AutomatonState)):
            aut_state.transition = aut_state_transition
            if (verbose > 0):
                print 'Setting transition of AutomatonState ' + str(aut_state_id) + \
                    ': ' + str(aut_state_transition)
        else:
            self.addAutState(AutomatonState(id=aut_state_id, state={}, \
                                                transition=aut_state_transition))
            if (verbose > 0):
                print 'Adding AutomatonState ' + str(aut_state_id) + \
                    ' with transition ' + str(aut_state_transition)

    def findAllAutState(self, state):
        """
        Return all the AutomatonState objects stored in this automaton whose state 
        matches `state`.
        Return -1 if such an AutomatonState objects is not found.

        Input:

        - `state`: a dictionary whose keys are the names of the variables
          and whose values are the values of the variables.
        """
        all_aut_states = []
        for aut_state in self.states:
            if (aut_state.state == state):
                all_aut_states.append(aut_state)
        return all_aut_states

    def getAutInit(self):
        """Return list of nodes that are initial, i.e., have empty In set.

        N.B., the set of initial nodes is not saved, so every time you
        call getAutInit, all nodes are checked for empty inward edge
        sets, which itself incurs a search cost (cf. doc for method
        getAutInSet).
        """
        init_nodes = []
        for k in range(len(self.states)):
            if len(self.getAutInSet(self.states[k].id)) == 0:
                init_nodes.append(self.states[k])
        return init_nodes

    def findAllAutPartState(self, state_frag):
        """Return list of nodes consistent with the given fragment.

        state_frag should be a dictionary.  We say the state in a node
        is ``consistent'' with the fragment if for every variable
        appearing in state_frag, the valuations in state_frag and the
        node are the same.

        E.g., let aut be an instance of Automaton.  Then
        aut.findAllAutPartState({"foobar" : 1}) would return a list of
        nodes (instances of AutomatonState) in which the variable
        "foobar" is 1 (true).
        """
        all_aut_states = []
        for aut_state in self.states:
            match_flag = True
            for k in state_frag.items():
                if k not in aut_state.state.items():
                    match_flag = False
                    break
            if match_flag:
                all_aut_states.append(aut_state)
        return all_aut_states

    def findAutState(self, state):
        """
        Return the first AutomatonState object stored in this automaton whose state 
        matches `state`.
        Return -1 if such an AutomatonState objects is not found.

        Input:

        - `state`: a dictionary whose keys are the names of the variables
          and whose values are the values of the variables.
          """
        for aut_state in self.states:
            if (aut_state.state == state):
                return aut_state
        return -1

    def findNextAutState(self, current_aut_state, env_state={},
                         deterministic_env=True):
        """
        Return the next AutomatonState object based on `env_state`.
        Return -1 if such an AutomatonState object is not found.

        Input:

        - `current_aut_state`: the current AutomatonState. Use current_aut_state = None
          for unknown current or initial automaton state.
        - `env_state`: a dictionary whose keys are the names of the environment 
          variables and whose values are the values of the variables.
        - 'deterministic_env': specifies whether to choose the environment state deterministically.
        """
        if (current_aut_state is None):
            transition = range(self.size())
        else:
            transition = current_aut_state.transition[:]
        
        def stateSatisfiesEnv(next_aut_id):
            for var in env_state.keys():
                if not (self.states[next_aut_id].state[var] == env_state[var]):
                    return False
            return True
        transition = filter(stateSatisfiesEnv, transition)
        
        if len(transition) == 0:
            return -1
        elif (deterministic_env):
            return self.states[transition[0]]
        else:
            return self.states[random.choice(transition)]
            
    def stripNames(self):
        for state in self.states:
            for k in state.state.keys():
                stripped = k.split(".")[-1]
                state.state[stripped] = state.state[k]
                del(state.state[k])


###################################################################

def createAut(aut_file, varnames=[], verbose=0):
    """
    Construct an automation from aut_file.

    Input:

    - `aut_file`: the name of the text file containing the automaton.
    - `varnames`: a list of all the variable names. If it is not empty, then this 
      function will also check whether the variables in aut_file are in varnames.
    """
    automaton = Automaton(states_or_file=aut_file, varnames=[], verbose=verbose)
    return automaton

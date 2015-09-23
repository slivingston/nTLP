#!/usr/bin/env python
"""
SCL; 15 August 2012.
"""

from StringIO import StringIO
import copy
from tulip.automaton import Automaton, AutomatonState


# Useful for regression testing; may be good to later provide
# backwards-compatibility testing for prior tulipcon XML Schema versions.
REFERENCE_XMLFRAGMENT = """  <aut>
    <node>
      <id>0</id><name></name>
      <child_list>1 2</child_list>
      <state><item key="y" value="0" /><item key="x" value="1" /></state>
    </node>
    <node>
      <id>1</id><name></name>
      <child_list>1 2</child_list>
      <state><item key="y" value="0" /><item key="x" value="0" /></state>
    </node>
    <node>
      <id>2</id><name></name>
      <child_list>1 0</child_list>
      <state><item key="y" value="1" /><item key="x" value="1" /></state>
    </node>
  </aut>
"""


REFERENCE_AUTFILE = """
smv file: /Users/scott/scott_centre/scm/tulip-xml-branch/examples/specs/robot_simple.smv
spc file: /Users/scott/scott_centre/scm/tulip-xml-branch/examples/specs/robot_simple.spc
priority kind: 3
Specification is realizable...
==== Building an implementation =========
-----------------------------------------
State 0 with rank 0 -> <park:1, cellID:0, X0reach:0>
	With successors : 1, 2
State 1 with rank 1 -> <park:0, cellID:0, X0reach:0>
	With successors : 3, 4
State 2 with rank 1 -> <park:1, cellID:0, X0reach:0>
	With successors : 3, 4
State 3 with rank 1 -> <park:0, cellID:1, X0reach:0>
	With successors : 5, 6
State 4 with rank 1 -> <park:1, cellID:1, X0reach:0>
	With successors : 5, 6
State 5 with rank 1 -> <park:0, cellID:4, X0reach:0>
	With successors : 7, 6
State 6 with rank 1 -> <park:1, cellID:4, X0reach:0>
	With successors : 7, 6
State 7 with rank 1 -> <park:0, cellID:3, X0reach:0>
	With successors : 8, 9
State 8 with rank 1 -> <park:0, cellID:4, X0reach:1>
	With successors : 15, 16
State 9 with rank 1 -> <park:1, cellID:4, X0reach:1>
	With successors : 10, 11
State 10 with rank 0 -> <park:0, cellID:4, X0reach:0>
	With successors : 12, 13
State 11 with rank 0 -> <park:1, cellID:4, X0reach:0>
	With successors : 12, 13
State 12 with rank 0 -> <park:0, cellID:1, X0reach:0>
	With successors : 14, 0
State 13 with rank 0 -> <park:1, cellID:1, X0reach:0>
	With successors : 14, 0
State 14 with rank 0 -> <park:0, cellID:0, X0reach:0>
	With successors : 1, 2, 1, 2
State 15 with rank 0 -> <park:0, cellID:4, X0reach:1>
	With successors : 17, 18
State 16 with rank 0 -> <park:1, cellID:4, X0reach:1>
	With successors : 12, 13
State 17 with rank 0 -> <park:0, cellID:1, X0reach:1>
	With successors : 19, 20
State 18 with rank 0 -> <park:1, cellID:1, X0reach:1>
	With successors : 14, 0
State 19 with rank 0 -> <park:0, cellID:0, X0reach:1>
	With successors : 21, 22
State 20 with rank 0 -> <park:1, cellID:0, X0reach:1>
	With successors : 1, 2
State 21 with rank 1 -> <park:0, cellID:0, X0reach:1>
	With successors : 19, 20
State 22 with rank 1 -> <park:1, cellID:0, X0reach:1>
	With successors : 14, 0
-----------------------------------------
Games time: 12
Checking realizability time: 14
Strategy time: 240
"""


def automaton2xml_test():
    ref_aut = Automaton(states_or_file=StringIO(REFERENCE_AUTFILE))
    aut = Automaton()
    aut.loadXML(ref_aut.dumpXML())
    assert aut == ref_aut
    aut.states[0].transition = []
    assert aut != ref_aut

def loadXML_test():
    aut = Automaton()
    aut.loadXML(REFERENCE_XMLFRAGMENT)
    assert len(aut) == 3
    assert (len(aut.states[0].state.keys()) == 2) and ("x" in aut.states[0].state.keys()) and ("y" in aut.states[0].state.keys())
    node0 = aut.findAutState({"x": 1, "y": 0})
    node1 = aut.findAutState({"x": 0, "y": 0})
    node2 = aut.findAutState({"x": 1, "y": 1})
    assert (len(node0.transition) == 2) and (node1 in [aut.states[node0.transition[0]], aut.states[node0.transition[1]]]) and (node2 in [aut.states[node0.transition[0]], aut.states[node0.transition[1]]])
    assert node0.transition == node1.transition
    assert len(node1.transition) == 2 and len(node2.transition) == 2


# Close the loop
def loaddumpXML_test():
    aut_first = Automaton()
    aut_first.loadXML(REFERENCE_XMLFRAGMENT)
    aut_second = Automaton()
    aut_second.loadXML(aut_first.dumpXML())
    assert aut_first == aut_second
    aut_first.states[0].transition = []
    assert aut_first != aut_second
    # Comparing string outputs seems too fragile to be a meaningful test
    #assert aut_first.dumpXML(pretty=True, idt_level=1) == REFERENCE_XMLFRAGMENT


def node_copy_test():
    node1 = AutomatonState(id=0, state={"nyan":0, "cat":1}, transition=[0])
    node2 = node1.copy()
    assert node2 is not node1
    assert node2.id == 0
    assert node2.state == {"nyan":0, "cat":1}
    assert node2.transition == [0]


class basic_Automaton_test():
    def setUp(self):
        self.empty_aut = Automaton()
        self.singleton = Automaton(states_or_file=[AutomatonState(id=0, state={"x":0}, transition=[0])])
        self.small_env = Automaton()
        self.small_env.loadXML(REFERENCE_XMLFRAGMENT)
        self.chain_len = 8
        base_state = dict([("x"+str(k),0) for k in range(self.chain_len)])
        self.chain_aut = Automaton()
        for k in range(self.chain_len):
            base_state["x"+str(k)] = 1
            self.chain_aut.addAutState(AutomatonState(id=k, state=base_state, transition=[(k+1)%self.chain_len]))
            base_state["x"+str(k)] = 0

    def tearDown(self):
        pass

    def test_equality(self):
        assert self.empty_aut == self.empty_aut
        assert self.singleton == self.singleton
        assert self.empty_aut != self.singleton

    def test_size(self):
        assert len(self.empty_aut) == 0  # Should give same result as size()
        assert self.empty_aut.size() == 0
        assert self.singleton.size() == 1
        assert len(self.small_env) == 3
        assert len(self.chain_aut) == self.chain_len

    def test_copy(self):
        A = self.singleton.copy()
        assert len(A) == 1
        B = copy.copy(self.singleton)
        assert A == B
        assert A is not B

        C = self.chain_aut.copy()
        assert len(C) == self.chain_len
        assert C == self.chain_aut
        base_state = dict([("x"+str(k),0) for k in range(self.chain_len)])
        base_state["x0"] = 1
        assert C.findAutState(base_state) != -1
        C.findAutState(base_state).state["x0"] = 0
        assert C != self.chain_aut

    def test_getAutInSet(self):
        assert self.empty_aut.getAutInSet(0) is None
        result = self.singleton.getAutInSet(0)
        assert len(result) == 1
        assert result[0].state == self.singleton.states[0].state
        assert result[0].transition == [0]
        for k in range(self.chain_len):
            result = self.chain_aut.getAutInSet(k)
            assert len(result) == 1
            assert result[0].id == (k-1)%self.chain_len
            assert result[0].transition == [k]

    def test_findAllAutPartState(self):
        assert len(self.empty_aut.findAllAutPartState({})) == 0
        assert len(self.singleton.findAllAutPartState({"x":1})) == 0
        result = self.singleton.findAllAutPartState({"x":0})
        assert (len(result) == 1) and (result[0].state == {"x":0})
        result_glob = self.singleton.findAllAutPartState({})
        assert result == result_glob

        # The chain automaton (with length at least 2) has slightly
        # more interesting structure to test.
        assert len(self.chain_aut.findAllAutPartState({})) == self.chain_len
        result = self.chain_aut.findAllAutPartState({"x0":0})
        assert len(result) == self.chain_len-1
        base_state = dict([(k,0) for k in result[0].state.keys()])
        base_state["x0"] = 1
        assert base_state not in [node.state for node in result]
        base_state["x0"] = 0; base_state["x1"] = 1
        assert base_state in [node.state for node in result]
        assert len(self.chain_aut.findAllAutPartState({"x0":0, "x1":0})) == self.chain_len-2

    def test_findNextAutState(self):
        node0 = self.small_env.findAutState({"x": 1, "y": 0})
        result_if_0 = self.small_env.findNextAutState(node0, env_state={"x":0})
        result_if_1 = self.small_env.findNextAutState(node0, env_state={"x":1})
        assert result_if_0.state == {"x":0, "y":0}
        assert result_if_1.state == {"x":1, "y":1}

    def test_trimDeadStates(self):
        self.chain_aut.states[-1].transition = []
        assert len(self.chain_aut) == self.chain_len
        self.chain_aut.trimDeadStates()
        assert len(self.chain_aut) == 0

    def test_trimUnconnectedStates(self):
        # Assume that chain automaton has length at least 3;
        # otherwise, it is not useful for testing this method.
        assert self.chain_len >= 3
        out_ID = self.chain_aut.states[-1].transition[0]
        self.chain_aut.states[-1].transition = []
        head_ID = self.chain_aut.states[out_ID].transition[0]
        head_state = self.chain_aut.states[head_ID].state.copy()
        self.chain_aut.states[out_ID].transition = []

        # At this step, the node out_ID has been orphaned
        self.chain_aut.trimUnconnectedStates(head_ID)
        assert len(self.chain_aut) == self.chain_len-1

        # trimUnconnectedStates does not preserve node IDs, so find
        # the "head" anew based on state.  Recall that each node has a
        # unique state in our chain automaton for testing.
        head_node = self.chain_aut.findAutState(head_state)
        out_ID = head_node.transition.pop()
        self.chain_aut.trimUnconnectedStates(out_ID)
        assert len(self.chain_aut) == self.chain_len-2

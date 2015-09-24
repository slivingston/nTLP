#!/usr/bin/env python
"""
Test the interface with gr1c.

SCL; 21 March 2013.
"""

import os

from tulip.conxml import loadXML
from tulip.spec import GRSpec
from tulip.gr1cint import *


REFERENCE_SPECFILE = """
# For example, regarding states as bitvectors, 1011 is not in winning
# set, while 1010 is. (Ordering is x ze y zs.)

ENV: x ze;
SYS: y zs;

ENVINIT: x & !ze;
ENVTRANS: [] (zs -> ze') & []((!ze & !zs) -> !ze');
ENVGOAL: []<>x;

SYSINIT: y;
SYSTRANS:;
SYSGOAL: []<>y&x & []<>!y & []<> !ze;
"""

REFERENCE_TRIVIALRG_AUTXML_v0 = """<?xml version="1.0" encoding="UTF-8"?>
<tulipcon xmlns="http://tulip-control.sourceforge.net/ns/0" version="0">
  <env_vars><item key="x" value="boolean" /></env_vars>
  <sys_vars><item key="y" value="boolean" /></sys_vars>
  <spec><env_init></env_init><env_safety></env_safety><env_prog></env_prog><sys_init></sys_init><sys_safety></sys_safety><sys_prog></sys_prog></spec>
  <aut>
    <node>
      <id>0</id><name></name><child_list></child_list>
      <state><item key="x" value="1" /><item key="y" value="1" /></state>
    </node>
    <node>
      <id>1</id><name></name><child_list></child_list>
      <state><item key="x" value="0" /><item key="y" value="1" /></state>
    </node>
    <node>
      <id>2</id><name></name><child_list> 1 0</child_list>
      <state><item key="x" value="1" /><item key="y" value="0" /></state>
    </node>
  </aut>
  <extra></extra>
</tulipcon>
"""

REFERENCE_TRIVIALRG_AUTXML_v1 = """<?xml version="1.0" encoding="UTF-8"?>
<tulipcon xmlns="http://tulip-control.sourceforge.net/ns/1" version="1">
  <env_vars><item key="x" value="boolean" /></env_vars>
  <sys_vars><item key="y" value="boolean" /></sys_vars>
  <spec><env_init></env_init><env_safety></env_safety><env_prog></env_prog><sys_init></sys_init><sys_safety></sys_safety><sys_prog></sys_prog></spec>
  <aut type="basic">
    <node>
      <id>0</id><anno></anno><child_list></child_list>
      <state><item key="x" value="1" /><item key="y" value="1" /></state>
    </node>
    <node>
      <id>1</id><anno></anno><child_list></child_list>
      <state><item key="x" value="0" /><item key="y" value="1" /></state>
    </node>
    <node>
      <id>2</id><anno></anno><child_list> 1 0</child_list>
      <state><item key="x" value="1" /><item key="y" value="0" /></state>
    </node>
  </aut>
  <extra></extra>
</tulipcon>
"""


REFERENCE_AUTXML_v0 = """<?xml version="1.0" encoding="UTF-8"?>
<tulipcon xmlns="http://tulip-control.sourceforge.net/ns/0" version="0">
  <spec><env_init></env_init><env_safety></env_safety><env_prog></env_prog><sys_init></sys_init><sys_safety></sys_safety><sys_prog></sys_prog></spec>
  <aut>
    <node>
      <id>0</id><name></name><child_list> 1 2</child_list>
      <state><item key="x" value="1" /><item key="y" value="0" /></state>
    </node>
    <node>
      <id>1</id><name></name><child_list> 1 2</child_list>
      <state><item key="x" value="0" /><item key="y" value="0" /></state>
    </node>
    <node>
      <id>2</id><name></name><child_list> 1 0</child_list>
      <state><item key="x" value="1" /><item key="y" value="1" /></state>
    </node>
  </aut>
  <extra></extra>
</tulipcon>
"""

REFERENCE_AUTXML_v1 = """<?xml version="1.0" encoding="UTF-8"?>
<tulipcon xmlns="http://tulip-control.sourceforge.net/ns/1" version="1">
  <env_vars><item key="x" value="boolean" /></env_vars>
  <sys_vars><item key="y" value="boolean" /></sys_vars>
  <spec><env_init></env_init><env_safety></env_safety><env_prog></env_prog><sys_init></sys_init><sys_safety></sys_safety><sys_prog></sys_prog></spec>
  <aut type="basic">
    <node>
      <id>0</id><anno></anno><child_list> 1 2</child_list>
      <state><item key="x" value="1" /><item key="y" value="0" /></state>
    </node>
    <node>
      <id>1</id><anno></anno><child_list> 1 2</child_list>
      <state><item key="x" value="0" /><item key="y" value="0" /></state>
    </node>
    <node>
      <id>2</id><anno></anno><child_list> 1 0</child_list>
      <state><item key="x" value="1" /><item key="y" value="1" /></state>
    </node>
  </aut>
  <extra></extra>
</tulipcon>
"""


class gr1cint_test:
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_check_syntax(self):
        assert check_syntax(REFERENCE_SPECFILE, verbose=1)
        assert not check_syntax("[]foo", verbose=1)

    def test_dumpgr1c(self):
        spec = GRSpec(env_vars="x", sys_vars="y",
                      env_init="x", env_prog="x",
                      sys_init="y", sys_safety=["y -> !y'", "!y -> y'"],
                      sys_prog="y & x")
        assert check_syntax(spec.dumpgr1c(), verbose=1)

    def test_check_realizable(self):
        spec = GRSpec(env_vars="x", sys_vars="y",
                      env_init="x", env_prog="x",
                      sys_init="y", sys_safety=["y -> !y'", "!y -> y'"],
                      sys_prog="y & x")
        assert not check_realizable(spec)
        spec.sys_safety = []
        assert check_realizable(spec)
        
    def test_synthesize(self):
        spec = GRSpec(env_vars="x", sys_vars="y",
                      env_init="x", env_prog="x",
                      sys_init="y",
                      sys_prog=["y & x", "!y"])
        aut = synthesize(spec)
        print spec.dumpgr1c()
        assert aut is not None
        (prob, sys_dyn, aut_ref) = loadXML(REFERENCE_AUTXML_v1)
        assert aut == aut_ref

    def test_synthesize_reachgame(self):
        # Corresponds to REFERENCE_TRIVIALRG_AUTXML above.
        spec = GRSpec(env_vars="x", sys_vars="y",
                      env_init="x", env_prog="x&y",
                      sys_init="!y", sys_prog="y")
        aut = synthesize_reachgame(spec)
        assert aut is not None
        (prob, sys_dyn, aut_ref) = loadXML(REFERENCE_TRIVIALRG_AUTXML_v1)
        assert aut == aut_ref


class GR1CSession_test:
    def setUp(self):
        self.spec_filename = "trivial_partwin.spc"
        with open(self.spec_filename, "w") as f:
            f.write(REFERENCE_SPECFILE)
        self.gs = GR1CSession(self.spec_filename, env_vars=["x","ze"], sys_vars=["y","zs"])

    def tearDown(self):
        self.gs.close()
        os.remove(self.spec_filename)

    def test_numgoals(self):
        assert self.gs.numgoals() == 3

    def test_getindex(self):
        assert self.gs.getindex({"x":0, "y":0, "ze":0, "zs":0}, 0) == 1
        assert self.gs.getindex({"x":0, "y":0, "ze":0, "zs":0}, 1) == 1

    def test_iswinning(self):
        assert self.gs.iswinning({"x":1, "y":1, "ze":0, "zs":0})
        assert not self.gs.iswinning({"x":1, "y":1, "ze":0, "zs":1})

    def test_env_next(self):
        assert self.gs.env_next({"x":1, "y":1, "ze":0, "zs":0}) == [{'x': 0, 'ze': 0}, {'x': 1, 'ze': 0}]
        assert self.gs.env_next({"x":1, "y":1, "ze":0, "zs":1}) == [{'x': 0, 'ze': 1}, {'x': 1, 'ze': 1}]

    def test_sys_nexta(self):
        assert self.gs.sys_nexta({"x":1, "y":1, "ze":0, "zs":0}, {"x":0, "ze":0}) == [{'y': 0, 'zs': 0}, {'y': 0, 'zs': 1}, {'y': 1, 'zs': 0}, {'y': 1, 'zs': 1}]

    def test_sys_nextfeas(self):
        assert self.gs.sys_nextfeas({"x":1, "y":1, "ze":0, "zs":0}, {"x":0, "ze":0}, 0) == [{'y': 0, 'zs': 0}, {'y': 1, 'zs': 0}]

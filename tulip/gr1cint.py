# Copyright (c) 2012-2014 by California Institute of Technology
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
Interface to gr1c

  - U{http://scottman.net/2012/gr1c}
  - release documentation at U{http://slivingston.github.io/gr1c/}

All functions that directly invoke gr1c include an argument toollog
that defaults to 1.  It concerns what level of logging, if any, to
request from gr1c.  The interpretation is, in terms of flags to gr1c,

  - 0 : No logging (no additional flags provided)
  - 1 : Logging (-l)
  - 2 : Verbose logging (-l -vv)

Verbose logging has the potential to substantially slow down the
process due to frequent writing to hard disk.
"""

import copy
import subprocess
import tempfile
import os
import json

from conxml import loadXML
from automaton import Automaton
from spec import GRSpec

import logging
logger = logging.getLogger(__name__)

GR1C_BIN_PREFIX=""


def check_syntax(spec_str, toollog=1):
    """Check whether given string has correct gr1c specification syntax.

    Return True if syntax check passed, False on error.
    """
    if toollog < 0:
        raise ValueError("Argument toollog must be nonnegative")
    if toollog == 0:
        log_settings = []
    elif toollog == 1:
        log_settings = ["-l"]
    else:
        log_settings = ["-l", "-vv"]

    f = tempfile.TemporaryFile()
    f.write(spec_str)
    f.seek(0)
    p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c", "-s"]+log_settings,
                         stdin=f,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    if p.returncode == 0:
        return True
    else:
        if toollog > 0:
            logger.debug(p.stdout.read())
        return False


def check_realizable(spec, toollog=1):
    """Decide realizability of specification defined by given GRSpec object.

    Return True if realizable, False if not, or an error occurs.
    """
    if toollog < 0:
        raise ValueError("Argument toollog must be nonnegative")
    if toollog == 0:
        log_settings = []
    elif toollog == 1:
        log_settings = ["-l"]
    else:
        log_settings = ["-l", "-vv"]

    f = tempfile.TemporaryFile()
    f.write(spec.dumpgr1c())
    f.seek(0)
    p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c", "-r"]+log_settings,
                         stdin=f,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    if p.returncode == 0:
        return True
    else:
        if toollog > 0:
            logger.debug(p.stdout.read())
        return False


def synthesize_reachgame(spec, toollog=1):
    """Synthesize strategy for a "reachability game."

    Return strategy as instance of Automaton class, or None if
    unrealizable or error occurs.
    """
    if toollog < 0:
        raise ValueError("Argument toollog must be nonnegative")
    if toollog == 0:
        log_settings = []
    else:
        # rg does not provide for -vv (more verbose)
        log_settings = ["-l"]
    p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c", "rg", "-t", "tulip"]+log_settings,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutdata, stderrdata) = p.communicate(spec.dumpgr1c_rg())
    if p.returncode == 0:
        (prob, sys_dyn, aut) = loadXML(stdoutdata)
        return aut
    else:
        if toollog > 0:
            logger.debug(stdoutdata)
        return None


def synthesize(spec, toollog=1):
    """Synthesize strategy.

    Return strategy as instance of Automaton class, or None if
    unrealizable or error occurs.
    """
    if toollog < 0:
        raise ValueError("Argument toollog must be nonnegative")
    if toollog == 0:
        log_settings = []
    elif toollog == 1:
        log_settings = ["-l"]
    else:
        log_settings = ["-l", "-vv"]
    p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c", "-t", "json"]+log_settings,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutdata, stderrdata) = p.communicate(spec.dumpgr1c())
    if p.returncode == 0:
        json_aut = json.loads(stdoutdata)
        aut = Automaton()
        aut.loadJSON(json_aut)
        return aut
    else:
        if toollog > 0:
            logger.debug(stdoutdata)
        return None

def patch_localfixpoint(spec, aut, N, change_list,
                        base_filename="patch_localfixpoint", toollog=1):
    """Use an experimental patching algorithm, available through gr1c.

      S.C. Livingston, P. Prabhakar, A.B. Jose, R.M. Murray.
      Patching task-level robot controllers based on a local
      mu-calculus formula. to appear at ICRA in May 2013.
      (The original Caltech CDS technical report is
       http://resolver.caltech.edu/CaltechCDSTR:2012.003)

    spec is an instance of GRSpec, aut is the nominal strategy
    automaton, and N is a list of states considered to be in the local
    neighborhood.  As usual, states in N are defined by dictionaries
    with variable names (strings) as keys.

    change_list describes the changes to the edge set of the game
    graph.  It is a list of pairs with the first element of each a
    command and the second element a list of (entire or partial)
    states, as defined in the documentation for gr1c.

    The intermediate files are named by appending "_changefile.edc",
    "_specfile.spc", and "_strategyfile.xml" to base_filename.  If any
    file already exists, then it is overwritten.

    Returns patched strategy, or None if unrealizable (or error).
    """
    if toollog < 0:
        raise ValueError("Argument toollog must be nonnegative")
    if toollog == 0:
        log_settings = []
    elif toollog == 1:
        log_settings = ["-l"]
    else:
        log_settings = ["-l", "-vv"]

    chg_filename = base_filename+"_changefile.edc"
    spc_filename = base_filename+"_specfile.spc"
    if len(N) == 0:  # Trivially unrealizable
        return None
    if change_list is None or len(change_list) == 0:
        return aut  # Pass back given reference, untouched

    with open(chg_filename, "w") as f:
        for state in N:
            state_vector = range(len(state))
            for ind in range(len(spec.env_vars)):
                state_vector[ind] = state[spec.env_vars[ind]]
            for ind in range(len(spec.sys_vars)):
                state_vector[len(spec.env_vars)+ind] = state[spec.sys_vars[ind]]
            f.write(" ".join([str(i) for i in state_vector])+"\n")
        for (cmd, cmd_args) in change_list:
            if cmd == "blocksys":
                state_vector = range(len(cmd_args[0]))
                for ind in range(len(spec.sys_vars)):
                    state_vector[ind] = cmd_args[0][spec.sys_vars[ind]]
                f.write(cmd+" ")
                f.write(" ".join([str(i) for i in state_vector])+"\n")
            elif cmd == "restrict" or cmd == "relax":
                state_vector1 = range(len(cmd_args[0]))
                for ind in range(len(spec.env_vars)):
                    state_vector1[ind] = cmd_args[0][spec.env_vars[ind]]
                for ind in range(len(spec.sys_vars)):
                    state_vector1[len(spec.env_vars)+ind] = cmd_args[0][spec.sys_vars[ind]]
                state_vector2 = range(len(cmd_args[1]))
                for ind in range(len(spec.env_vars)):
                    state_vector2[ind] = cmd_args[1][spec.env_vars[ind]]
                if len(cmd_args[1]) > len(spec.env_vars):
                    for ind in range(len(spec.sys_vars)):
                        state_vector2[len(spec.env_vars)+ind] = cmd_args[1][spec.sys_vars[ind]]
                f.write(cmd+" ")
                f.write(" ".join([str(i) for i in state_vector1])+" ")
                f.write(" ".join([str(i) for i in state_vector2])+"\n")
            else:
                raise ValueError("unrecognized command: \""+str(cmd)+"\"")

    with open(spc_filename, "w") as f:
        f.write(spec.dumpgr1c())
    aut_in_f = tempfile.TemporaryFile()
    aut_in_f.write(aut.dumpgr1c(env_vars=spec.env_vars, sys_vars=spec.sys_vars))
    aut_in_f.seek(0)
    aut_out_f = tempfile.TemporaryFile()
    p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c", "patch"] \
                         +log_settings \
                         +["-t", "json", "-a", "-", "-e", chg_filename,
                           spc_filename],
                         stdin=aut_in_f, stdout=aut_out_f,
                         stderr=subprocess.STDOUT)
    p.wait()
    aut_out_f.seek(0)
    if p.returncode == 0:
        json_aut = json.loads(aut_out_f.read())
        patched_aut = Automaton()
        patched_aut.loadJSON(json_aut)
        return patched_aut
    else:
        if toollog > 0:
            logger.debug(aut_out_f.read())
        return None


def add_sysgoal(spec, aut, new_sysgoal, metric_vars=None,
                base_filename="add_sysgoal", toollog=1):
    """Use an experimental patching algorithm, available through gr1c

    spec is an instance of GRSpec, aut is the nominal strategy
    automaton, and new_sysgoal is a formula defining a new system
    goal, given as a string, as would expected of an element in the
    ``sys_prog`` attribute of the GRSpec class.  If metric_vars is not
    None, it should be a list of variable names to use in distance
    computations, where the value of each variable is interpreted as
    an element of a coordinate in a Euclidean space.

    base_filename is treated as in patch_localfixpoint().

    Return patched strategy, or None if unrealizable (or error).
    """
    if toollog < 0:
        raise ValueError("Argument toollog must be nonnegative")
    if toollog == 0:
        log_settings = []
    elif toollog == 1:
        log_settings = ["-l"]
    else:
        log_settings = ["-l", "-vv"]
    if metric_vars is None:
        metric_vars = []
    spc_filename = base_filename+"_specfile.spc"
    with open(spc_filename, "w") as f:
        f.write(spec.dumpgr1c())
    aut_in_f = tempfile.TemporaryFile()
    aut_in_f.write(aut.dumpgr1c(env_vars=spec.env_vars, sys_vars=spec.sys_vars))
    aut_in_f.seek(0)
    aut_out_f = tempfile.TemporaryFile()
    p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c", "patch"] \
                         +log_settings \
                         +["-t", "json", "-a", "-", "-f", new_sysgoal,
                           "-m", " ".join(metric_vars), spc_filename],
                         stdin=aut_in_f,
                         stdout=aut_out_f, stderr=subprocess.STDOUT)

    p.wait()
    aut_out_f.seek(0)
    if p.returncode == 0:
        json_aut = json.loads(aut_out_f.read())
        patched_aut = Automaton()
        patched_aut.loadJSON(json_aut)
        return patched_aut
    else:
        if toollog > 0:
            logger.debug(aut_out_f.read())
        return None


def rm_sysgoal(spec, aut, delete_index, base_filename="rm_sysgoal", toollog=1):
    if toollog < 0:
        raise ValueError("Argument toollog must be nonnegative")
    if toollog == 0:
        log_settings = []
    elif toollog == 1:
        log_settings = ["-l"]
    else:
        log_settings = ["-l", "-vv"]
    spc_filename = base_filename+"_specfile.spc"
    with open(spc_filename, "w") as f:
        f.write(spec.dumpgr1c())
    aut_in_f = tempfile.TemporaryFile()
    aut_in_f.write(aut.dumpgr1c(env_vars=spec.env_vars, sys_vars=spec.sys_vars))
    aut_in_f.seek(0)
    aut_out_f = tempfile.TemporaryFile()
    p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c", "patch"] \
                         +log_settings \
                         +["-t", "json", "-a", "-", "-r", str(delete_index),
                           spc_filename],
                         stdin=aut_in_f,
                         stdout=aut_out_f, stderr=subprocess.STDOUT)

    p.wait()
    aut_out_f.seek(0)
    if p.returncode == 0:
        aut_out_json = aut_out_f.read()
        logger.debug("rm_sysgoal received from grpatch:\n"+aut_out_json)
        json_aut = json.loads(aut_out_json)
        patched_aut = Automaton()
        patched_aut.loadJSON(json_aut)
        return patched_aut
    else:
        if toollog > 0:
            logger.debug(aut_out_f.read())
        return None


class GR1CSession:
    """Manage interactive session with gr1c.

    Given lists of environment and system variable names determine the
    order of values in state vectors for communication with the gr1c
    process.  Eventually there may be code to infer this directly from
    the spec file.

    **gr1c is assumed not to use GNU Readline.**

    Please compile it that way if you are using this class.
    (Otherwise, GNU Readline will echo commands and make interaction
    with gr1c more difficult.)

    The argument `prompt` is the string printed by gr1c to indicate it
    is ready for the next command.  The default value is a good guess.

    Unless otherwise indicated, command methods return True on
    success, False if error.
    """
    def __init__(self, spec_filename, sys_vars, env_vars=[], prompt=">>> "):
        self.spec_filename = spec_filename
        self.sys_vars = sys_vars[:]
        self.env_vars = env_vars[:]
        self.prompt = prompt
        if self.spec_filename is not None:
            self.p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c",
                                       "-i", self.spec_filename],
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
        else:
            self.p = None


    def iswinning(self, state):
        """Return True if given state is in winning set, False otherwise.

        state should be a dictionary with keys of variable names
        (strings) and values of the value taken by that variable in
        this state, e.g., as in nodes of the Automaton class.
        """
        state_vector = range(len(state))
        for ind in range(len(self.env_vars)):
            state_vector[ind] = state[self.env_vars[ind]]
        for ind in range(len(self.sys_vars)):
            state_vector[ind+len(self.env_vars)] = state[self.sys_vars[ind]]
        self.p.stdin.write("winning "+" ".join([str(i) for i in state_vector])+"\n")
        if "True\n" in self.p.stdout.readline():
            return True
        else:
            return False


    def getindex(self, state, goal_mode):
        if goal_mode < 0 or goal_mode > self.numgoals()-1:
            raise ValueError("Invalid goal mode requested: "+str(goal_mode))
        state_vector = range(len(state))
        for ind in range(len(self.env_vars)):
            state_vector[ind] = state[self.env_vars[ind]]
        for ind in range(len(self.sys_vars)):
            state_vector[ind+len(self.env_vars)] = state[self.sys_vars[ind]]
        self.p.stdin.write("getindex "+" ".join([str(i) for i in state_vector])+" "+str(goal_mode)+"\n")
        line = self.p.stdout.readline()
        if len(self.prompt) > 0:
                loc = line.find(self.prompt)
                if loc >= 0:
                    line = line[len(self.prompt):]
        return int(line[:-1])

    def env_next(self, state):
        """Return list of possible next environment moves, given current state.

        Format of given state is same as for iswinning method.
        """
        state_vector = range(len(state))
        for ind in range(len(self.env_vars)):
            state_vector[ind] = state[self.env_vars[ind]]
        for ind in range(len(self.sys_vars)):
            state_vector[ind+len(self.env_vars)] = state[self.sys_vars[ind]]
        self.p.stdin.write("envnext "+" ".join([str(i) for i in state_vector])+"\n")
        env_moves = []
        line = self.p.stdout.readline()
        while "---\n" not in line:
            if len(self.prompt) > 0:
                loc = line.find(self.prompt)
                if loc >= 0:
                    line = line[len(self.prompt):]
            env_moves.append(dict([(k, int(s)) for (k,s) in zip(self.env_vars, line.split())]))
            line = self.p.stdout.readline()
        return env_moves


    def sys_nextfeas(self, state, env_move, goal_mode):
        """Return list of next system moves consistent with some strategy.

        Format of given state and env_move is same as for iswinning
        method.
        """
        if goal_mode < 0 or goal_mode > self.numgoals()-1:
            raise ValueError("Invalid goal mode requested: "+str(goal_mode))
        state_vector = range(len(state))
        for ind in range(len(self.env_vars)):
            state_vector[ind] = state[self.env_vars[ind]]
        for ind in range(len(self.sys_vars)):
            state_vector[ind+len(self.env_vars)] = state[self.sys_vars[ind]]
        emove_vector = range(len(env_move))
        for ind in range(len(self.env_vars)):
            emove_vector[ind] = env_move[self.env_vars[ind]]
        self.p.stdin.write("sysnext "+" ".join([str(i) for i in state_vector])+" "+" ".join([str(i) for i in emove_vector])+" "+str(goal_mode)+"\n")
        sys_moves = []
        line = self.p.stdout.readline()
        while "---\n" not in line:
            if len(self.prompt) > 0:
                loc = line.find(self.prompt)
                if loc >= 0:
                    line = line[len(self.prompt):]
            sys_moves.append(dict([(k, int(s)) for (k,s) in zip(self.sys_vars, line.split())]))
            line = self.p.stdout.readline()
        return sys_moves


    def sys_nexta(self, state, env_move):
        """Return list of possible next system moves, whether or not winning.

        Format of given state and env_move is same as for iswinning
        method.
        """
        state_vector = range(len(state))
        for ind in range(len(self.env_vars)):
            state_vector[ind] = state[self.env_vars[ind]]
        for ind in range(len(self.sys_vars)):
            state_vector[ind+len(self.env_vars)] = state[self.sys_vars[ind]]
        emove_vector = range(len(env_move))
        for ind in range(len(self.env_vars)):
            emove_vector[ind] = env_move[self.env_vars[ind]]
        self.p.stdin.write("sysnexta "+" ".join([str(i) for i in state_vector])+" "+" ".join([str(i) for i in emove_vector])+"\n")
        sys_moves = []
        line = self.p.stdout.readline()
        while "---\n" not in line:
            if len(self.prompt) > 0:
                loc = line.find(self.prompt)
                if loc >= 0:
                    line = line[len(self.prompt):]
            sys_moves.append(dict([(k, int(s)) for (k,s) in zip(self.sys_vars, line.split())]))
            line = self.p.stdout.readline()
        return sys_moves


    def getvars(self):
        """Return string of environment and system variable names in order.

        Indices are indicated in parens.
        """
        self.p.stdin.write("var\n")
        line = self.p.stdout.readline()
        if len(self.prompt) > 0:
                loc = line.find(self.prompt)
                if loc >= 0:
                    line = line[len(self.prompt):]
        return line[:-1]

    def numgoals(self):
        self.p.stdin.write("numgoals\n")
        line = self.p.stdout.readline()
        if len(self.prompt) > 0:
                loc = line.find(self.prompt)
                if loc >= 0:
                    line = line[len(self.prompt):]
        return int(line[:-1])

    def reset(self, spec_filename=None):
        """Quit and start anew, reading spec from file with given name.

        If no filename given, then use previous one.
        """
        if self.p is not None:
            self.p.stdin.write("quit\n")
            returncode = self.p.wait()
            self.p = None
            if returncode != 0:
                self.spec_filename = None
                return False
        if spec_filename is not None:
            self.spec_filename = spec_filename
        if self.spec_filename is not None:
            self.p = subprocess.Popen([GR1C_BIN_PREFIX+"gr1c",
                                       "-i", self.spec_filename],
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
        else:
            self.p = None
        return True

    def close(self):
        """End session, and kill gr1c child process."""
        self.p.stdin.write("quit\n")
        returncode = self.p.wait()
        self.p = None
        if returncode != 0:
            return False
        else:
            return True

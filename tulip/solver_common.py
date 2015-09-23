#!/usr/bin/env python
#
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
# Common components for solvers
import time, os
class SolverException(Exception):
    pass

def memoryMonitor(pid):
    maxmem = 0
    t = 0.01
    procstr = "/proc/%d/statm" % pid
    statm = None
    try:
        statm = open(procstr, "r")
        while 1:
            statm.seek(0)
            pstats = statm.read().split()
            # pstats[0] = VmSize = total program size
            vmsize = int(pstats[0])
            if vmsize == 0:
                # Likely the process has exited, has a defunct entry in /proc
                break
            maxmem = max(maxmem, vmsize)
            #usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            #maxmem = max(maxmem, usage.ru_maxrss)
            time.sleep(t)
            # exponential backoff
            t *= 1.2
    except IOError:
        return 0
    finally:
        if statm:
            statm.close()
    return maxmem*os.sysconf("SC_PAGE_SIZE")/1024 # KiB

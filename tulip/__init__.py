# Copyright (c) 2011, 2013 by California Institute of Technology
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
"""nTLP

...a permanent fork of TuLiP that removes use of MPT, yices, and JTLV,
and will still follow relevant upstream changes.
TuLiP (http://tulip-control.sf.net) is the Temporal Logic Planning Toolbox
that provides functions for verifying and constructing control protocols.
"""

# Initialize logging facility
import logging as _logging
from time import gmtime as _gmtime
logger = _logging.getLogger(__name__)
logger.setLevel(_logging.DEBUG)
_console_logh = _logging.StreamHandler()
_console_logh.setLevel(_logging.WARNING)
_base_log_format = "%(name)s:%(levelname)s: %(message)s"
_formatterh = _logging.Formatter("%(asctime)s "+_base_log_format)
_formatterh.converter = _gmtime
_console_logh.setFormatter(_formatterh)
logger.addHandler(_console_logh)

def log_showtime(showtime=True):
    if showtime:
        _console_logh.setFormatter(_formatterh)  # Default format
    else:
        _console_logh.setFormatter(_logging.Formatter(_base_log_format))

def log_setlevel(lvl="WARNING"):
    _console_logh.setLevel(getattr(_logging, lvl))

def log_echotofile(filename=None):
    """

    If no filename is given, then create one with name of the form
    nTLP-YYYYMMDD.log
    """
    from time import strftime
    if filename is None:
        filename = "nTLP-"+strftime("%Y%m%d", _gmtime())+".log"
    file_logh = _logging.FileHandler(filename)
    file_logh.setLevel(_logging.DEBUG)
    formatterh = _logging.Formatter("%(asctime)s "+_base_log_format)
    formatterh.converter = _gmtime
    file_logh.setFormatter(formatterh)
    logger.addHandler(file_logh)


__all__ = ["prop2part", "grsim", "jtlvint", "automaton", "rhtlp", "spec", 'discretize', 'polytope']

__version__ = "0.8.0"

import prop2part
import grsim
import jtlvint
import automaton
from spec import GRSpec

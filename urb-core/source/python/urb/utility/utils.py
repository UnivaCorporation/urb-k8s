#!/usr/bin/env python

# Copyright 2017 Univa Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import functools
import cProfile as profile
import pstats
import re
import StringIO
from urb.exceptions.urb_exception import URBException

def get_score(lo, hi):
    """ Calculate and return a score used for storing range tuple elements (lo,hi,incr) 
    in an ordered set (usually used for storing that element to a message
    queue ordered set).
    """
    # The 0.0000000001 is arbitrary but allows for relatively large ranges
    # to be differentiated by this score. Might need to cook up something
    # more clever if this ever becomes critical.
    return lo + 0.0000000001 * hi

def sliceFromIdxStr(index):
    index_list = index.split(":")
    if len(index_list) != 3:
        ##################
        # Replace original exception with URBException
        # raise ShortJobException(6,
        raise URBException(
                                "3 elements expected for replication index. Replication index must " +
                                "have the form l:h:s with l, h and s being integers.")
    try:
        index_int_list = [int(e) for e in index_list]
    except:
        ##################
        # Replace original exception with URBException
        #raise ShortJobException(7,
        raise URBException(
                                'Integer elements expected for replication index. ' +
                                'Replication index must have the form l:h:s with l, h and s being integers.')
    return slice(*tuple(index_int_list))

def rangeFramSlice(sl):
    return range(sl.start, sl.stop + 1, sl.step)

def rangeFromIdxStr(index):
    return rangeFramSlice(sliceFromIdxStr(index))

def parse_index(index):
    if not index:
        return 1, 1, 1, 1
    sl = sliceFromIdxStr(index)
    return sl.start, sl.stop, sl.step, len(rangeFramSlice(sl))


INDENT_WIDTH = 0

def print_io(func):
    """Provides debug output for arguments and returned value of the function.
    Can be used as a decorator.
    For debug purpose only.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global INDENT_WIDTH
        indent = " " * INDENT_WIDTH * 4
        print indent, func.__name__
        print indent, "Args = ", args
        INDENT_WIDTH += 1
        try:
            val = func(*args, **kwargs)
            print indent, "Args after = ", args
            print indent, "Return value: ", val
            print ""
            return val
        except:
            raise
        finally:
            INDENT_WIDTH -= 1
    return wrapper

def profile_func(func):
    """If used as a decorator, prints the information about the execution
    of the decorated function.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        pr = profile.Profile()
        pr.enable()
        ret = func(*args, **kwargs)
        pr.disable()

        s = StringIO.StringIO()
        sortby = ['cumulative', 'time']
        ps = pstats.Stats(pr, stream=s).sort_stats(*sortby)
        ps.print_stats(200)
        print s.getvalue()
        return ret

    return wrapper


def __replace(init_str, env, var_repr):
    """Replaces all occurrences of variables in env in init_str string.
    Variables are represented like var_repr(var).
    """
    if not env:
        return init_str

    for var, value in env.iteritems():
        init_str = init_str.replace(var_repr(var), value)

    return init_str


def replace_env(init_str, env):
    """Replaces all occurrences of variables in env in init_str string.
    Variables are used like $var_name.
    """
    return __replace(init_str, env, lambda s: ("$" + s))


def replace_vars(init_str, env):
    """Replaces all occurrences of variables in env in init_str string.
    Variables are used like {var_name}.
    """
    return __replace(init_str, env, lambda s: ("{%s}" % s))


def join_args(*args):
    return " ".join(map(str, args))

def isfloat(value):
    try:
        float(value)
        return True
    except:
        return False


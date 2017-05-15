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


from utils import *
from sortedcontainers import SortedSet
from urb.exceptions.urb_exception import URBException
from copy import deepcopy
import re
        
def get_chunk(iterable, chunk_size):
    """ Generic generator which chunks up any iterable into chunks of size
    'chunk_size' and returns the chunks as iteration items. The last chunk
    will be shorter if the length of the iterable data is not evenly divisble
    by 'chunk_size'.
    """
    result = []
    for item in iterable:
        result.append(item)
        if len(result) == chunk_size:
            yield result
            result = []
    if len(result) > 0:
        yield result


class RangeTuple(tuple):
    def __init__(self, *args, **kwargs):
        super(RangeTuple, self).__init__()
        self.check_valid()
        self.start, self.stop, self.step = self

    def __new__(self, t):
        return super(RangeTuple, self).__new__(self, t)

    def __contains__(self, other):
        """ Returns True if other is fully contained in self. Otherwise
        returns False.
        """
        return self.start <= other.start and self.stop >= other.stop

    def check_valid(self):
        """ Checks whether 'tpl' is a valid range tuple, i.e. whether it has
        exactly three elements which are of type integer or have all the value
        None.
        """
        try:
            assert len(self) == 3
            assert [type(e) for e in self] == [int, int, int]
        except AssertionError:
            ##################
            # Replace original exception with URBException
            #raise ShortJobException(13, \
            raise URBException(
                "Tuple needs to consist of 3 integers. Got %s instead." % str(self))

    def join(self, other):
        """ Joins two adjacent RangeTuples into one. Returns the two tuples in
        sorted order if they are not adjacent (i.e. also if they overlap). In
        both cases a list is returned, either with one or two RangeTuple
        elements.
        """
        low, high = sorted((self, other))
        if low.stop + low.step == high.start:
            return [RangeTuple((low.start, high.stop, low.step))]
        else:
            return [low, high]

    def ck_same_step(self, other):
        """ Check whether self and other have same step size. Raise exception
        if not
        """
        if self.step <> other.step:
            ##################
            # Replace original exception with URBException
            #raise ShortJobException(31, \
            raise URBException(
                "Range tuples need to have the same step size. Got %d and %d." \
                % (self.step, other.step))

    def _ck_and_fix(self, other):
        """ Convenience function for ever repeated pattern of checking self
        and other and fixing their indices
        """
        self.ck_same_step(other)
        fself = self.fix_indices()
        fother = other.fix_indices()
        return fself, fother

    def isoverlapping(self, other):
        """ Return True if two RangeTuples are overlapping """
        fself, fother = self._ck_and_fix(other)
        low, high = sorted((fself, fother))
        return low.start <= high.start <= low.stop

    def isadjacent(self, other):
        """ Return True if two RangeTuples are adjacent """
        fself, fother = self._ck_and_fix(other)
        low, high = sorted((fself, fother))
        return low.stop + low.step == high.start

    def count(self):
        """ Returns count of index elements contained in a range tuple without
        expanding it into a range.
        Note that the stop value is meant to be inclusive, i.e. it is part of the
        range index set here.
        """
        return int((self.stop - self.start) / self.step) + 1

    def chop_chunks(self, chunk_size):
        """ Generator which chunks up a range specified via RangeTuple 'self'
        into RangeTuples which describe ranges of up to 'chunk_size' elements in
        them. Yields sequential tuples iteratively.

        IMPORTANT: the generator never expands the range so it can be used on huge
        ranges without causing memory issues

        Example:
            (5, 17, 3) with chunk_size = 2 will yield (5, 8, 3) | (11, 13, 3) | (16, 16, 3)
        """
        next_start, stop, step = self
        while next_start <= stop:
            start = next_start
            steps = int((stop - next_start) / step)
            if steps >= chunk_size:
                next_start += step * chunk_size
                yield RangeTuple((start, next_start - step, step))
            else:
                break
        if next_start <= stop:
            stop = next_start
            if steps:
                stop += step * steps
            yield RangeTuple((start, stop, step))

    def intersection(self, other):
        """ Returns the intersection of two range intervals as defined by
        start-end of self and start-end of other. If there is no overlap then
        None gets returned. Otherwise the intersection gets returned
        as RangeTuple.
        """
        fself, fother = self._ck_and_fix(other)
        if fself.stop < fother.start or fother.stop < fself.start:
            return None
        else:
            return RangeTuple((max(fself.start, fother.start), min(fself.stop, fother.stop), fself.step))

    def union(self, other):
        """ Determines union of two RangeTuples and returns list of
        RangeTuples either containing one element (union yields one contiguous
        range) or two elements (self and other do not overlap).
        """
        fself, fother = self._ck_and_fix(other)
        if fother in fself:
            return [fself]
        if fself in fother:
            return [fother]
        intersection = self.intersection(fother)
        if not intersection:
            return fself.join(fother)
        if fother.start < fself.start:
            return [RangeTuple((fother.start, fself.stop, fself.step))]
        else:
            return [RangeTuple((fself.start, fother.stop, fself.step))]
            
    def difference(self, other):
        fself, fother = self._ck_and_fix(other)
        intersection = self.intersection(fother)
        if not intersection:
            return fself.join(fother)
        ret = []
        low = fself.start if fself.start < fother.start else fother.start
        high = fself.stop if fself.stop > fother.stop else fother.stop
        if low < intersection.start:
            ret.append(RangeTuple((low, intersection.start-fself.step, fself.step)))
        if intersection.stop < high:
            ret.append(RangeTuple((intersection.stop+fself.step, high, fself.step)))
        if len(ret) == 2:
            ret = ret[0].join(ret[1])
        return ret

    def fix_indices(self):
        """ Adjust 'stop' values from ranges which will never get reached
        given the 'start' and 'step' definition, e.g. 5 in (2,5,2) ==> return
        (2,4,2) in this case.
        """
        start, stop, step = self
        steps = int((stop-start)/step)
        # self._reset(RangeTuple((start, start+steps*step, step)))
        return RangeTuple((start, start+steps*step, step))

    def test_sync(self, other):
        """ Raise an exception if value self and other are not in "sync step".
        E.g. (1,5,2) and (2,4,2) are not in sync.
        """
        self.ck_same_step(other)
        diff = other.start - self.start
        if diff % self.step:
            ##################
            # Replace original exception with URBException
            #raise ShortJobException(32, \
            raise URBException(
                "Tuple removal only supported for partial subsets.")

    def remove_overlap(self, other):
        """ Cuts out part of range tuple 'self' (of the form
        (start,stop,step)) which overlaps with the range specified by another
        tuple ('other'). The return value is a list of the resulting tuple(s):
            - either an empty list if there is no overlap
            - or with only 1 range tuple element which is the resulting range after
              the overlap has been cut out
            - or will be 2 if 'other' fully is contained within 'self'.

        Exceptions will be risen in the following cases:
            - if the step specifier of 'self' and 'other' is not the same
            - if the ranges are "out of sync", e.g. 1,3,5,7, ... and 4,6,8,... So
              they either need to share no element at all by being out of bounds
              (in which case an empty list gets returned) or they need to share at
              least on element
        """

        # Make sure range indices have no stop values never reached given the
        # start and step values (e.g. a stop of 5 for 2 for start and step)
        # Also step sizes need to be the same
        fself, fother = self._ck_and_fix(other)

        # Find intersection and return original range if there is none
        intersection = fself.intersection(fother)
        if not intersection:
            return [(fself.start, fself.stop, fself.step)]

        # Ensure ranges are in sync step (i.e. do not interleave)
        fself.test_sync(fother)

        # Determine cutdown range(s)
        if fself.start < intersection.start:
            ret = []
            ret.append((fself.start,intersection.start-fself.step,fself.step))
            if intersection.stop < self.stop:
                ret.append((intersection.stop+fself.step,fself.stop,fself.step))
            return ret
        elif intersection.stop < fself.stop:
            return [(intersection.stop+fself.step,fself.stop,fself.step)]
        else:
            return []


class IntervalSet(SortedSet):
    """ A set class designed to store non-overlapping interval ranges of the
    form (start, stop, step) as tuples. Overwrites the __contains__() and
    add() methods. add() throws exceptions if the element to be added is not
    suitable or if it overlaps with another range element already in the set.
    The 'step' value is currently ignored for the overlap tests, i.e.
    intervals are assumed to be continous and an overlap occurs when interval
    boundaries overlap.
    """
    def __init__(self, *args, **kwargs):
        super(IntervalSet, self).__init__(*args, **kwargs)

    def add(self, e):
        """ Add element to IntervalSet unless it overlaps with existing
        element in set (tested via __contains__() invoked by 'in'. Raises
        exception if overlap is detected.
        """
        if e in self:
            ##################
            # Replace original exception with URBException
            #raise ShortJobException(11, \
            raise URBException(
                "Trying to add range element " + str(e) + " but it " \
                + "overlaps with an existing element in IntervalSet.")

        super(IntervalSet, self).add(e)

    def __contains__(self, e):
        """ Check whether element 'e' already is contained in IntervalSet.
        Current check ignores 'step', so intervals are taken as being
        continuous and overlaps can be detected by only looking at the
        interval boundaries. (Would be possible to refactor with using 'step'
        and look at whether the investigated interval fits into the gaps of
        existing intervals or not.)
        Raises execeptions if type is not of the form tuple(int, int, int)
        for added element. Returns True if the element overlaps with existing
        set members. Otherwise returns False.
        """
        # Check for well formed tuple element
        RangeTuple(e).check_valid()

        # Test for overlaps
        prev, next = self.neighbors(e)
        if prev and not (e[1] < prev[0] or e[0] > prev[1]):
            return True
        if next and not (e[1] < next[0] or e[0] > next[1]):
            return True
        return False

    def neighbors(self, e):
        """ Identifies neighboring / potentially overlapping set members for
        an element 'e'
        """
        idx = self.bisect(e)
        prev = None if idx == 0 else self[idx-1]
        next = None if idx == len(self) else self[idx]
        return prev, next
        

class ChoppyRange():
    """ Providing low memory footprint and high performance access to "choppy
    ranges", i.e. integer ranges which can have gaps in them (example: 3:7:2,
    15:17:2 ==> a range of 3:17:2 with a gap of 9:13:2). NOTE, that our ranges
    have inclusive stop boundaries, so 1:3:1 means 1, 2, 3.

    The class itself is an iterator and will yield consecutive elements in the
    choppy range.
    """
    def __init__(self, initRange=None, force_same_step=True, backup=""):
        """ 'initRange' can take several forms of input, see the insert()
        method
        """
        # IntervalSet is used to store choppy range. IntervalSet allows to
        # test for overlapping ranges
        self.choppyRange = IntervalSet()
        self.ignoreOverlaps = False # raise exception if added range overlaps
        self.walker = None          # for the next() funtion
        self.backup = backup
        self.force_same_step = force_same_step
        self.step = None
        if self.backup:
            self.mq = MsgQ()
        if initRange:
            self.insert(initRange)

    def __iter__(self):
        """ Simple iterator definition """
        return self

    def __str__(self):
        """ String representation is start1:stop1:step1, start2:stop2:step2,
        ...
        """
        return ",".join([":".join([str(e) for e in list(itm)])
                                          for itm in self.items()])

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, idx):
        return self.choppyRange[idx]

    def __len__(self):
        return len(self.choppyRange)
        """
        i = 0
        for e in self.items():
            i += 1
        return i
        """

    def __expr__(self):
        """ Raw choppy range data type representation with string conversion
        """
        return str(self.choppyRange)

    def next(self):
        """ Iterator function uses _yieldIndex() generator """
        if not self.walker:
            # Initialize generator
            self.walker = self._yieldIndex(self.choppyRange)
        try:
            # Yield iterations
            return self.walker.next()
        except StopIteration:
            self.walker = None
            raise

    def _yieldIndex(self, cr):
        """ Generator delivering the index elements of a choppy range one by
        one and in sequence order
        """
        for rgItem in iter(cr.__iter__()):
            next, stop, step = rgItem
            while next <= stop:
                yield next
                next += step

    def chopup(self, chunk_size):
        """ Generator chunking up each individual element of a ChoppyRange
        IntervalSet into range descriptors with an index count of 'chunk_size'.
        Note that the last range descriptor for each element in the
        ChoppyRange can have less index elements if there are not enough in
        the corresponding IntervalSet element. I.e. we are not filling up with
        indeces from a follow on element because that's generally not
        possible.

        Uses RangeTuple.chop_chunks() generator.

        Example:
            cr = ChoppyRange()
            cr.insert("1:3:1,7:8:1")

            for e in cr.chopup(2)
                print e

            will yield

            (1,2,1)
            (3,3,1)
            (7,8,1)
        """
        for e in self.items():
            for ck in e.chop_chunks(chunk_size):
                yield ck

    def chopFillUp(self, chunk_size):
        """ Similar to self.chopup() but this Generator will try to bundle
        several range descriptors so as long as the count of total indices
        in a bundle stays <= chunk_size. Yielded values are lists with one
        or more range tuples a elements. They can be turned into a
        ChoppyRange by themselves by using self.insert().
        Note that the function does not "unpack" a range. It just bundles
        range tuples together so as long as the index count stays within
        chunk_size. It does, however, join adjacent ranges where possible.
        """
        def _expand_elem_lst(e, lst):
            """ Expands element list while glueing adjacent elements together
            where possible
            """
            if lst and e.isadjacent(lst[-1]):
                e = e.join(lst[-1])[0]
                lst.pop(-1)
            lst.append(e)
                
        fillL = []
        cklen = 0
        for e in self.chopup(chunk_size):
            elemlen = e.count()
            if cklen+elemlen < chunk_size:
                # assemble in fillL while index cnt smaller than chunk_size
                _expand_elem_lst(e, fillL)
                cklen += elemlen
                continue
            if cklen+elemlen == chunk_size:
                # exactly full ==> yield and reset
                _expand_elem_lst(e, fillL)
                yield fillL
                cklen = 0
                fillL = []
            else:
                # would exceed ==> yield previous and preset with current
                if fillL:
                    yield fillL
                cklen = elemlen
                fillL = [e]
        if fillL:
            # yield residue
            yield fillL
                
    def indexCount(self):
        """ Returns the number of indices contained in total in a ChoppyRange
        """
        if len(self):
            # return reduce(lambda x,y: x+y, [e.count() for e in self.items()])
            sum = 0
            for e in self.items():
                sum += e.count()
            return sum
        return 0
            
    def insert(self, initRange, step=0):
        """ Insert type dependent values. 'initRange' can be a slice,
        a string, a tuple (or list thereof), all specifying start,stop,step
        of contiguous range part (with inclusive stop boundary). It can also
        be an integer which forms a single element with start=stop. Furthermore
        it can be a range which will get translated into start,stop,step
        notation. Finally a string value can be supplied which consists or
        contiguous slices.
        The optional paramter 'step' is only used when a list is passed to us.
        Otherwise it is ignored.
        """
        if type(initRange) in [list, int]:
            getattr(self, "_add_" + type(initRange).__name__)(initRange, step)
        else:
            getattr(self, "_add_" + type(initRange).__name__)(initRange)

    def items(self):
        """ Return sorted list of range slice tuples which describe the choppy
        range
        """
        return list(self.choppyRange)

    def iteritems(self):
        """ Iterator for items() above """
        for rgItem in iter(self.choppyRange.__iter__()):
            yield rgItem

    def itervalues(self):
        """ Iterator of the range indices; same as provided by the ChoppyRange
        class iterator itself.
        """
        return self

    def lpop(self):
        try:
            item = self.choppyRange.pop(0)
            if self.backup:
                self.mq.zRemRangeByRank(self.backup, 0, 0)
            return item
        except:
            return None
        
    def clear(self):
        """ Clears choppy range data structure """
        self.choppyRange = IntervalSet()
        self.step = None

    def subtract(self, cr):
        """ Allows to remove parts of a ChoppyRange overlapping with another
        """
        def _updateTupleOverlap(old, overlap):
            """ Updates range tuple in ChoppyRange, i.e. determine overlap and
            update tuple spec in ChoppyRange
            Uses RangeTuple class and its remove_overlap() function.
            """
            if not old:
                return
            new = RangeTuple(old).remove_overlap(RangeTuple(overlap))
            if new and new[0] == old:
                # No update necessary
                return
            # Update needed ==> first remove existing
            self.choppyRange.remove(old)
            if self.backup:
                self.mq.zRem(self.backup, old)
            # then replace with adjusted settings (if any)
            for tpl in new:
                self.insert(tpl)

        for e in cr.items():
            # Identify potentially overlapping elements - can be two
            prev, next = self.choppyRange.neighbors(e)
            # For both see whether an update is needed
            _updateTupleOverlap(prev, e)
            _updateTupleOverlap(next, e)

    def copy(self):
        """ Create shallow copy of instance """
        ret = ChoppyRange(force_same_step=self.force_same_step, backup=self.backup)
        ret.step = self.step
        ret.choppyRange = IntervalSet(self.choppyRange)
        return ret

    def remove(self, toRemove):
        """ Removes elements from ChoppyRange. The specification of 'toRemove'
        is the same as that for the inserted elements in insert() above.
        Note that also the intersection of partially overlapping range
        elements will get removed.
        """
        cr = ChoppyRange(toRemove)
        self.subtract(cr)

    def union(self, *cr_list, **kwargs):
        """ Forms a union of 'self' and a list of ChoppyRange instance by
        merging their indices. Glues adjacent ranges into one. If in_pace is
        true then the merging occurs within the 'self' ChoppyRange instance.
        Otherwise it returns a new ChoppyRange instance containing the resulting
        union.
        """
        if kwargs.get('in_place'):
            union_cr = self
        else:
            # union_cr = deepcopy(self)  # will contain union in the end - start with copy of self
            union_cr = self.copy()  # will contain union in the end - start with copy of self

        # Loop of ChoppyRange instances in argumentlist and merge with
        # union_cr item by item
        for cr in cr_list:
            for e in cr.items():
                # List of neighbors
                nl = [neigh for neigh in union_cr.choppyRange.neighbors(e) if neigh]
                if not nl:
                    # No neighbors should happen only if self was empty
                    union_cr.insert(e)
                    continue

                # Replacement map with key is neighbor and value is replacement
                # Replacement is union of element with neighbor if element
                # overlaps or is adjacent with neighbor
                repl_map = dict((n,e.union(n)[0]) for n in nl if e.isoverlapping(n) or e.isadjacent(n))

                if not repl_map:
                    # Not overlapping/adjacent: standalone new element ==> just add
                    union_cr.insert(e)
                    continue

                # Replace elements while glueing adjacent ones
                toadd = None
                while True:
                    # Will loop once for one neighbor or twice for two
                    try:
                        rem, add = repl_map.popitem()
                    except:
                        break

                    union_cr.remove(rem)    # we can remove the neighbor immediately

                    # In case of two overlapping/adjacent neighbors the
                    # resuling replacement will be one big range spanning
                    # both. So form union for later adding in that case,
                    # otherwise just store to replacement
                    toadd = toadd.union(add)[0] if toadd else add

                # And do the insert of the replacement now
                union_cr.insert(toadd)

        return union_cr

    def intersection(self, other):
        intersect_cr = ChoppyRange(force_same_step=self.force_same_step)
        for e in other.items():
            # List of neighbors
            nl = [neigh for neigh in self.choppyRange.neighbors(e) if neigh]
            if not nl:
                # No neighbors should happen only if self was empty
                intersect_cr.insert(e)
                continue

            for neighbor in nl:
                overlap = neighbor.intersection(e)
                if overlap:
                    intersect_cr.insert(overlap)

        return intersect_cr

    def values(self):
        """ Returns list of range indeces in the choppy range """
        return [e for e in self]

    def isempty(self):
        for e in self:
            return False
        return True

    def _load(self, descr_lst):
        """ Will load ChoppyRange data structure with items from
        'descr_lst'. The items in 'descr_list' can either be tuples or lists
        (hence the tuple conversion below). Lists are needed for deserialized
        JSON objects because tuples get serialized into JSON lists and when
        deserializing will result in Python lists. Independent of the type,
        the items have to have 3 elements for start, stop and step.
        """
        for e in descr_lst:
            self.insert(tuple(e))

    def _group(self, lst, step):
        """
        Groups fragmented range (with "holes" in it) with step-size 'step'
        into range descriptor tuples which will get added to a ChoppyRange
        object.

        Explicit for-loop implementation of the below grouping recipe. The
        for-loop is several 10% faster ...

        from operator import itemgetter
        from itertools import groupby
        for k, g in groupby(enumerate(lst),
                        lambda (i,grp_indicator):step*i-grp_indicator):
             grp = map(itemgetter(1), g)
             self.insert((grp[0],grp[-1], step))
        """

        low, high, old = None, None, None
        for i, v in enumerate(lst):
            # grp_indicator stays the same as long as index elements differ by
            # step
            grp_indicator = step * i - v
            if old <> grp_indicator:
                # A change has happened; new group has started
                if low:
                    # save old group
                    self.insert((low, high, step))
                low = None
                old = grp_indicator
            # Don't do "if not low" here - would mix up the case where low = 0
            if low is None:
                # save start value of group
                low = v
            # update high value
            high = v
        # save last group
        self.insert((low, high, step))

    def _add_RangeTuple(self, initRange):
        """ Add a RangeTuple instance """
        self._add_tuple(tuple(initRange))

    def _add_tuple(self, initRange):
        """ Add a tuple; 'initRange' is of the from (start,stop,step).
        Note that all other _add_* functions use _add_tuple in one way or
        another. Hence the we use the InvervalSet class method 'add' only
        here.
        """
        # Check for well formed tuple element - instantiating it as RangeTuple
        # will do that
        RangeTuple(initRange).check_valid()
        if self.force_same_step:
            if not self.step:
                self.step = initRange[2]
            elif self.step <> initRange[2]:
                ##################
                # Replace original exception with URBException
                #raise ShortJobException(40, \
                raise URBException(
                    "Step size needs to be the same for all elements of " \
                    + "ChoppyRange. Had %d thus far. Element %s has %d." % \
                    (self.step, str(initRange), initRange[2]))

        # add() method of IntervalSet will throw exception if newly added
        # range overlaps with existing ranges
        try:
            # self.choppyRange.add(initRange)
            self.choppyRange.add(RangeTuple(initRange))
            if self.backup:
                score = get_score(initRange[0], initRange[1])
                self.mq.zAdd(self.backup, score, initRange)
        except:
            if not self.ignoreOverlaps:
                raise

    def _add_list(self, initRange, step=0):
        """ Adds a range, i.e. a list of indices, or a list of range
        specifiers which can either be 3-element tuples or 3-element lists or
        a list of strings of the form 'start:stop:step'.
        If it is a list of integer indices then the optional 'step' argument
        is used to group the items. This is needed if the index list really is
        a choppy range, i.e. has holes in it. Without 'step' being specified
        (step=0) we will assume an equidistant range.
        """
        def _add_int_list(intl):
            if step:
                self._group(intl, step)
            else:
                if len(intl) == 1:
                    self._add_int(intl[0], step)
                else:
                    self._add_tuple((intl[0], intl[-1],
                                    intl[1] - intl[0]))
            
        if not initRange:
            return
        if type(initRange[0]) is int:
            _add_int_list(initRange)
        elif type(initRange[0]) is str:
            for e in initRange:
                self._add_str(e)
        elif type(initRange[0]) is unicode:
            _add_int_list([int(e) for e in initRange])
        elif type(initRange[0]) in [tuple, list, RangeTuple]:
            self._load(initRange)
        else:
            ##################
            # Replace original exception with URBException
            #raise ShortJobException(22, \
            raise URBException(
                "Type " + str(type(initRange[0])) + " is not supported " \
                + "as element for list which gets added to a ChoppyRange.")
            

    def _add_slice(self, initRange):
        """ Adds an element as defined by a slice whereby stop is inclusive
        """
        self._add_tuple((initRange.start, initRange.stop, initRange.step))

    def _add_str(self, initRange):
        """ Adds an element defined by string. Can either be the string
        representation of a RangeTuple, i.e. '(start, stop, step)' or the
        simple form "start:stop:step" or a comma separated list of the latter.
        """
        if not initRange:
            # do nothing in case of empty string
            return

        stripped = initRange.replace(" ", "")
        # First check case of string RangeTuple representation
        strtplpat = re.compile("\(\d+,\d+,\d+\)")
        rg_list = re.findall(strtplpat, stripped)
        if rg_list:
            for rg in rg_list:
                self._add_tuple(tuple(int(e) for e in rg[1:-1].split(',')))
            return
        # Now for lists of start:stop:step strings
        for rg in stripped.split(','):
            self._add_slice(sliceFromIdxStr(rg))

    def _add_unicode(self, initRange):
        """ Adds a uncode string element by converting it to string and then
        use the respective function for that
        """
        self._add_str(str(initRange))

    def _add_int(self, initRange, step=0):
        """ Adds an integer as start=stop=initRange and step taken as passed
        in or from self.step or as 1 as fall-back
        """
        step = step if step else self.step
        step = step if step else 1
        self._add_tuple((initRange, initRange, step))

if __name__ == '__main__':
    # For module testing

    # Create ChoppyRange instance and add range slice elements through various ways
    cr = ChoppyRange("2:4:1", force_same_step=False)
    cr.insert((7,15,2))
    cr.insert(19)
    cr.insert(slice(28,35,3))
    cr.insert([41,44,47,50])
    # Print what we've got
    print """Filling ChoppyRange with
        cr = ChoppyRange("2:4:1", force_same_step=False)
        cr.insert((7,15,2))
        cr.insert(19)
        cr.insert(slice(28,35,3))
        cr.insert([41,44,47,50])
    """
    print "choppyRange struct:", cr.choppyRange
    print "Elements:", cr.items()
    print ""

    print ""
    print "Testing insert of list of range strings"
    cr.clear()
    print 'Inserting ["1:5:2","9:11:2","14:20:2"]'
    cr.insert(["1:5:2","9:11:2","14:20:2"])
    print "Yields", cr

    # Create empty and load with output of form items() would create
    cr = ChoppyRange(force_same_step=False)
    cr.insert([(2,5,1),(12,18,2),(31,31,3),(42,43,2),(55,59,3)])
    # Print what we've got to test items(), __str__ and __expr__
    print "cr.insert([(2,5,1),(12,18,2),(31,31,3),(42,43,2),(55,59,3)]) yields"
    print "__str__() / str(): ", cr
    print "__expr__():", cr.__expr__()
    print "Elements:", cr.values()
    # Test chunking it up
    print "\nChunk in 3s"
    print "\n".join([str(ck) for ck in get_chunk(cr, 3)])
    print ""

    # Testing variations of list inserting into ChoppyRange
    cr.clear()
    cr.insert(range(10))
    print "Inserting range(10) yields", cr
    cr.clear()
    cr.insert([(2,5,1),(12,18,2),(31,31,3),(42,43,2),(55,59,3)])
    print "Inserting [(2,5,1),(12,18,2),(31,31,3),(42,43,2),(55,59,3)] yields", cr
    print ""

    # Save in string then do a bulk insert of that string
    s = str(cr)
    cr.clear()      # empty data structure in between
    cr.insert(s)
    print "Reloaing from", s, "yields:", cr.choppyRange
    print ""

    # Check invariance agains json conversions
    import json
    js = json.dumps(cr.items())         # dump it into string
    print "json.dumps(cr.items())", js
    cr.clear()
    cr.insert(json.loads(js))             # read it from it
    print "choppyRange struct after json.loads:", cr.choppyRange
    print "Elements:", cr.values()
    print ""

    # Check functions available for chunking up ChoppyRange without expansion
    print "Chop up ChoppyRange without expanding it"
    print "Use chunksize of 3"
    for e in cr.chopup(3):
        print e, "with element count", RangeTuple(e).count()
    print "Count elems of (2,2,3)", RangeTuple((2,2,3)).count()
    print "Count elems of (2,8,2)", RangeTuple((2,8,2)).count()
    print "Count elems of (2,7,2)", RangeTuple((2,7,2)).count()
    print "Count elems of (2,9,2)", RangeTuple((2,9,2)).count()
    print ""
    cr.clear()
    cr.insert([(2,5,2),(6,6,2),(12,18,2),(31,31,2),(42,43,2),(56,59,2)])
    print "Chop up ChoppyRange", cr, " without expansion but glue elements within chunksize"
    print "Use chunksize of 3"
    for e in cr.chopFillUp(3):
        print e, ChoppyRange(e)
    print ""
    print "Indices contained in ChoppyRange:", cr.indexCount()

    # Just clear the data and fill it with one descriptor of a larger range
    cr.clear()
    cr.insert((4,57,3))
    # Test chunking with that again
    print "Chunk in 4s of cr.insert((4,57,3))"
    print "\n".join([str(ck) for ck in get_chunk(cr, 4)])
    print ""

    # Test automatic grouping, i.e. taking scattered indices and form them
    # into range slice groups based on a given step width
    cr.clear()
    cr.insert([2,4,10,12,14,24,28,32,34,36,38], 2)
    print "Set with: cr.insert([2,4,10,12,14,24,28,32,34,36,38], 2)"
    print "choppyRange struct:", cr.choppyRange
    print ""

    # Test the iter*() functions
    print "Iterating through iteritems:"
    for e in cr.iteritems():
        print e
    print "Iterating through itervalues:"
    for e in cr.itervalues():
        print e

    # Test whether range overlaps get detected
    print ""
    cr.clear()
    cr.insert((2,4,1))
    print "Overlap tests with choppy range:", cr
    tstrgs = [(1,3,1), (3,5,1), (1,5,1), (3,3,1), (3,4,1), (2,3,1), (2,4,1)]
    for rg in tstrgs:
        try:
            cr.insert(rg)
            print rg, "got added wrongly ==>", str(cr)
        except:
            print rg, "overlaps with ==>", str(cr)
    # Finally check whether exception gets created correctly
    print "Trying to add range '(2,5,2)' to choppy range", cr
    try:
        cr.insert((2,5,2))
    except URBException as e:
        ##################
        # Replace original exception with URBException
        #except ShortJobException as e:
        print e

    # And whether overlap exceptions can be ignored
    print "\nNow with ingoreOverlaps set to True:"
    cr.ignoreOverlaps = True
    for rg in tstrgs:
        cr.insert(rg)
        print rg, "tried to add and ignored ==>", str(cr)

    # Test error detection for range inputs into IntervalSet class
    print "\nTesting error detecting in IntervalSet class"
    cr.ignoreOverlaps = False
    for rg in [(1,1), (1,2,'a'), "test"]:
        print "Trying to add", rg, "to choppy range"
        try:
            cr.insert(rg)
            print rg, "got added wrongly ==>", str(cr)
        except URBException as e:
            ##################
            # Replace original exception with URBException
            #except ShortJobException as e:
            print e
    print "Trying to add element 'test' to IntervalSet"
    try:
        s = IntervalSet()
        s.add("test")
    except URBException as e:
        ##################
        # Replace original exception with URBException
        #except ShortJobException as e:
        print e

    print ""
    print "Testing subtract() function"
    cr.clear()
    cr.insert([(2,7,2),(12,18,2),(31,31,2),(42,52,2),(55,59,2)])
    cr2 = ChoppyRange((4,5,2))
    print "Removing", cr2, "from", cr
    cr.subtract(cr2)
    print "Yields", cr
    cr2 = ChoppyRange((12,16,2))
    print "Removing", cr2, "from", cr
    cr.subtract(cr2)
    print "Yields", cr
    cr2 = ChoppyRange((57,57,2))
    print "Removing", cr2, "from", cr
    cr.subtract(cr2)
    print "Yields", cr
    cr2 = ChoppyRange((40,42,2))
    print "Removing", cr2, "from", cr
    cr.subtract(cr2)
    print "Yields", cr
    cr2 = ChoppyRange((40,46,2))
    print "Removing", cr2, "from", cr
    cr.subtract(cr2)
    print "Yields", cr
    cr2 = ChoppyRange((52,52,2))
    print "Removing", cr2, "from", cr
    cr.subtract(cr2)
    print "Yields", cr
    cr.clear()
    cr.insert([(2,7,2),(12,18,2),(31,31,2),(42,52,2),(55,59,2)])
    cr2 = ChoppyRange([(4,5,2),(40,42,2)])
    print "Removing", cr2, "from", cr
    cr.subtract(cr2)
    print "Yields", cr

    print ""
    print "Testing the remove() function"
    cr.clear()
    cr.insert([(2,7,2),(12,18,2),(31,31,2),(42,52,2),(55,59,2)])
    cr.remove((4,5,2))
    print "Removing (4,5,2) from", cr
    print "Yields", cr

    print ""
    print "Testing __contains__() in IntervalSet"
    cr.clear()
    cr.insert([(2,7,2),(12,18,2),(31,31,2),(42,52,2),(55,59,2)])
    print "ChoppyRange is", cr
    try:
        cr.insert((5,9,2))
    except URBException:
        ##################
        # Replace original exception with URBException
        #except ShortJobException as e:
        print "Attempted to insert 5:9:2 = overlap ==> got exception"
    cr.insert((9,11,2))
    print "Attempted to insert 9:11:2 = no overlap ==>", cr

    print ""
    cr.clear()
    cr.insert([(2,7,2),(12,18,2),(31,31,2),(42,52,2),(55,59,2)])
    print "Output of values()", cr.values(), " for ChoppyRang", cr

    print ""
    cr = ChoppyRange("1:1:1")
    print "Is >>", cr, "<< empty?", cr.isempty()
    print "Subtracting 1 from ChoppyRange", cr, " yields:", cr.subtract(ChoppyRange(1))
    print "Is >>", cr, "<< empty?", cr.isempty()

    print ""
    cr = ChoppyRange("1:1:1")
    try:
        cr.insert("2:2:2")
        print "Error: should have received step mismatch because of trying to insert 2:2:2 to ChoppyRange of 1:1:1"
    except:
        print "Trying to insert 2:2:2 to ChoppyRange of", cr, " and correctly got exception because of step mismatch"
    print "Step size in cr", cr, " is", cr.step

    print ""
    print "RangeTuple((1,4,1)).union(RangeTuple((7,9,1))):", RangeTuple((1,4,1)).union(RangeTuple((7,9,1)))
    print "RangeTuple((7,9,1)).union(RangeTuple((1,4,1))):", RangeTuple((7,9,1)).union(RangeTuple((1,4,1)))
    print "RangeTuple((1,4,1)).union(RangeTuple((3,9,1))):", RangeTuple((1,4,1)).union(RangeTuple((3,9,1)))
    print "RangeTuple((3,9,1)).union(RangeTuple((1,4,1))):", RangeTuple((3,9,1)).union(RangeTuple((1,4,1)))
    print "RangeTuple((1,9,1)).union(RangeTuple((2,4,1))):", RangeTuple((1,9,1)).union(RangeTuple((2,4,1)))
    print "RangeTuple((2,4,1)).union(RangeTuple((1,9,1))):", RangeTuple((2,4,1)).union(RangeTuple((1,9,1)))
    print "RangeTuple((2,4,1)).union(RangeTuple((1,9,1))):", RangeTuple((2,4,1)).union(RangeTuple((1,9,1)))
    print "RangeTuple((1,4,2)).union(RangeTuple((3,9,2))):", RangeTuple((1,4,2)).union(RangeTuple((3,9,2)))
    print "RangeTuple((1,4,2)).union(RangeTuple((5,9,2))):", RangeTuple((1,4,2)).union(RangeTuple((5,9,2)))
    try:
        print "RangeTuple((1,4,2)).union(RangeTuple((3,9,1))):", RangeTuple((1,4,2)).union(RangeTuple((3,9,1)))
        print "Tuple union was done incorrectly despite inequal step"
    except:
        print "RangeTuple((1,4,2)).union(RangeTuple((3,9,1))) correctly resulted in exception because inequal steps."
    print ""
    print "RangeTuple((1,4,1)).difference(RangeTuple((7,9,1))):", RangeTuple((1,4,1)).difference(RangeTuple((7,9,1)))
    print "RangeTuple((1,4,1)).difference(RangeTuple((3,9,1))):", RangeTuple((1,4,1)).difference(RangeTuple((3,9,1)))
    print "RangeTuple((1,4,1)).difference(RangeTuple((4,9,1))):", RangeTuple((1,4,1)).difference(RangeTuple((4,9,1)))
    print "RangeTuple((1,4,1)).difference(RangeTuple((5,9,1))):", RangeTuple((1,4,1)).difference(RangeTuple((5,9,1)))
    print "RangeTuple((1,4,1)).difference(RangeTuple((1,9,1))):", RangeTuple((1,4,1)).difference(RangeTuple((1,9,1)))
    print "RangeTuple((1,4,1)).difference(RangeTuple((2,3,1))):", RangeTuple((1,4,1)).difference(RangeTuple((2,3,1)))
    print "RangeTuple((1,4,1)).difference(RangeTuple((1,3,1))):", RangeTuple((1,4,1)).difference(RangeTuple((1,3,1)))
    print ""
    print "RangeTuple((1,4,1)).join(RangeTuple(5,7,1)):", RangeTuple((1,4,1)).join(RangeTuple((5,7,1)))
    print "RangeTuple((1,4,1)).join(RangeTuple(4,7,1)):", RangeTuple((1,4,1)).join(RangeTuple((4,7,1)))
    print "RangeTuple((1,4,1)).join(RangeTuple(6,7,1)):", RangeTuple((1,4,1)).join(RangeTuple((6,7,1)))

    print ""
    cr = ChoppyRange("1:4:1,7:9:1")
    cr2 = ChoppyRange("3:5:1,11:13:1")
    cr3 = ChoppyRange("6:6:1,17:18:1")
    print "Union of %s  &  %s  &  %s ==> %s" % (cr, cr2, cr3, cr.union(cr2, cr3)) 
    cr = ChoppyRange("1:4:1,9:10:1")
    cr2 = ChoppyRange("3:5:1,11:13:1")
    cr3 = ChoppyRange("6:8:1,17:18:1")
    print "Union of %s  &  %s  &  %s ==> %s" % (cr, cr2, cr3, cr.union(cr2, cr3)) 
    cr = ChoppyRange("1:4:2,9:9:2")
    cr2 = ChoppyRange("3:5:2,11:13:2")
    cr3 = ChoppyRange("6:8:2,17:18:2")
    print "Union of %s  &  %s  &  %s ==> %s" % (cr, cr2, cr3, cr.union(cr2, cr3)) 
    print ""
    print "Testing in_place union:"
    cr = ChoppyRange("1:4:2,9:9:2")
    cr2 = ChoppyRange("3:5:2,11:13:2")
    cr3 = ChoppyRange("6:8:2,17:18:2")
    print "In-place union of %s  &  %s  &  %s" % (cr, cr2, cr3)
    cr.union(cr2, cr3, in_place=True)
    print "cr instance itself:", cr

    print ""
    cr = ChoppyRange("1:4:1,7:9:1,11:15:1,22:25:1")
    cr2 = ChoppyRange("3:8:1,10:10:1,13:14:1,24:29:1")
    print "Intersection of %s and %s ==> %s" % (cr, cr2, cr.intersection(cr2))
    cr = ChoppyRange("1:4:1,7:9:1,11:15:1,22:25:1")
    cr2 = ChoppyRange("0:1:1,4:7:1,11:22:1,25:29:1")
    print "Intersection of %s and %s ==> %s" % (cr, cr2, cr.intersection(cr2))
    cr = ChoppyRange("1:8:3,10:21:3,28:28:3")
    cr2 = ChoppyRange("4:9:3,13:21:3,25:25:3,28:35:3")
    print "Intersection of %s and %s ==> %s" % (cr, cr2, cr.intersection(cr2))

    print ""
    print 'ChoppyRange("(2,4, 1) , (5, 7, 1) ,( 9,11,1),(21,22,1)") ==>', ChoppyRange("(2,4, 1) , (5, 7, 1) ,( 9,11,1),(21,22,1)")

    print ""
    cr = ChoppyRange("1:4:1")
    cr2 = ChoppyRange()
    cr3 = ChoppyRange()
    un = cr2.union(cr3)
    cr.subtract(un)
    print "subtr", cr

    import sys
    if len(sys.argv) == 1:
        sys.exit(0)
    print ""
    print "Benchmarking various options to implement storing and removing to/from Redis."
    print "Usage:", sys.argv[0], " <ChoppyRangeDescrStr> <ChunkSize> ['print']"
    print ""
    crstr = sys.argv[1]
    cksz = int(sys.argv[2])
    doprint = False
    if len(sys.argv) == 4:
        doprint = True
    print ""
    mq = MsgQ()
    mq.clearMsgQs()
    import time

    print "Benchmarking how to do unions of failed or done tasks"
    cr = ChoppyRange(crstr)
    start = time.time()
    for e in cr.chopup(cksz):
        mq.zAdd("TTT", e.start, e)
    print "Chopping of ChoppyRange", cr, " in chunks of size", cksz, " took", time.time()-start
    start = time.time()
    cr2 = ChoppyRange()
    crlst = []
    while True:
        e = mq.zLPopAndMove('TTT')
        if not e:
            break
        crlst.append(ChoppyRange(e))
    cr2 = ChoppyRange().union(*crlst)
    print "Popping and union of ChoppyRange", cr, " in chunks of size", cksz, " took", time.time()-start
    print ""
    start = time.time()
    for e in cr.chopup(cksz):
        mq.zAdd("TTT", e.start, str(ChoppyRange(e)))
    print "Chopping of ChoppyRange", cr, " in chunks of size", cksz, " took", time.time()-start
    start = time.time()
    i = 0
    while True:
        e = mq.zLPopAndMove('TTT')
        if not e:
            break
        mq.sAdd(str(i), *ChoppyRange(e).values())
        i += 1
    sts = [str(e) for e in range(i)]
    un = mq.sUnion(*sts)
    print "Union of sets from", cr, " split in chunks of size", cksz, " took", time.time()-start

    print ""
    start = time.time()
    cr = ChoppyRange(crstr, backup='XXX', force_same_step=False)
    for e in cr.chopFillUp(cksz):
        mq.sAdd('TTT', e)
    print "Fill chopped took:", time.time() - start
    l = []
    start = time.time()
    while True:
        e = mq.sPop('TTT')
        if e:
            if doprint:
                l.append(e)
        else:
            break
    if doprint:
        print l
    print "Popping with sPop took:", time.time() - start

    mq.clearMsgQs()
    print ""
    import time
    start = time.time()
    cr = ChoppyRange(crstr, backup='XXX', force_same_step=False)
    for e in cr.chopFillUp(cksz):
        mq.sAdd('TTT', e)
    print "Fill chopped took:", time.time() - start
    l = []
    start = time.time()
    while True:
        e = mq.sPopMove('TTT','T')
        if e:
            if doprint:
                l.append(e)
        else:
            break
    if doprint:
        print l
    print "Popping with sPopMove took:", time.time() - start

    mq.clearMsgQs()
    print ""
    import time
    start = time.time()
    cr = ChoppyRange(crstr, backup='XXX', force_same_step=False)
    for e in cr.chopFillUp(cksz):
        mq.zAdd('XYZ', get_score(e[0][0], e[-1][1]), e)
    print "Fill chopped with zAdd took:", time.time() - start
    # print cr2.mq.zGet(cr2.backup)
    l = []
    start = time.time()
    while True:
        e = mq.zLPopAndMove('XYZ', 'Z')
        # e = mq.zLPopMove('XYZ','Z')
        if e:
            if doprint:
                l.append(e)
        else:
            break
    if doprint:
        print l
    print "Popping with zLPopMove took:", time.time() - start

    mq.clearMsgQs()
    print ""
    import time
    start = time.time()
    cr = ChoppyRange(crstr, backup='XXX', force_same_step=False)
    for e in cr.chopFillUp(cksz):
        mq.zAdd('TTT', get_score(e[0][0], e[-1][1]), e)
    print "Fill chopped with zAdd took:", time.time() - start
    # print cr2.mq.zGet(cr2.backup)
    l = []
    start = time.time()
    while True:
        e = mq.zLPopAndMove('TTT')
        if e:
            if doprint:
                l.append(e)
        else:
            break
    if doprint:
        print l
    print "Popping with zLPopAndRem took:", time.time() - start

    print ""
    mq.clearMsgQs()
    start = time.time()
    cr = ChoppyRange(crstr, backup='ZZZ', force_same_step=False)
    for e in cr.chopFillUp(cksz):
        mq.pushToQ('YYY', e)
    print "Fill chopped with pushToQ took:", time.time() - start
    start = time.time()
    l = []
    while True:
        msg = mq.popFromQ('YYY')
        if not msg:
            break
        else:
            if doprint:
                l.append(msg)
    if doprint:
        print l
    print "Popping with popFromQ took:", time.time() - start

    print ""
    mq.clearMsgQs()
    start = time.time()
    cr = ChoppyRange(crstr, force_same_step=False)
    mq.sAdd('XXX', *[e for e in cr.itervalues()])
    for e in get_chunk(cr, cksz):
        mq.pushToQ('AAA', e)
    print "Fill chopped with pushToQ and sAdd of itervalues took:", time.time() - start
    start = time.time()
    l = []
    while True:
        msg = mq.popFromQ('AAA')
        if not msg:
            break
        else:
            if doprint:
                l.append(msg)
    if doprint:
        print l
    print "Popping with popFromQ took:", time.time() - start

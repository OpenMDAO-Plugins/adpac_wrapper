import fileinput
import sys

from openmdao.main.api import Container

from adpac_wrapper.input import Input

# Default input values used for (non-)dimensionalizing, etc.
INPUT = Input()


# Map from BC type name to class.
_REGISTRY = {}

def register(name, cls):
    """ Register `cls` as handler for `name`. """
    _REGISTRY[name] = cls


class BCPair(object):
    """ Paired BCs which communicate. Used for scheduling. """

    def __init__(self, bc1, bc2, lblock1, lblock2):
        self.bc1 = bc1
        self.bc2 = bc2
        self.lblock1 = lblock1
        self.lblock2 = lblock2


class Boundata(Container):
    """ ADPAC boundary condition file handling. """

    def __init__(self, *args, **kwargs):
        super(Boundata, self).__init__(*args, **kwargs)
        self._bcs = []

    def read(self, casename, input_ref=None):
        """
        Read boundary condition information from ``<casename>.boundata``.
        `input_ref` provides an :class:`Input` object for reference conditions.
        Note that unlike ADPAC, unrecognized keywords are treated as an error.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        self._bcs = []
        inp = fileinput.FileInput(casename+'.boundata', mode='rU')
        try:
            line = inp.readline()
            while line:
                tokens = line.upper().split()
                if not tokens:
                    line = inp.readline()
                    continue  # Blank.

                typ = tokens[0]
                if typ[0] == '#':
                    line = inp.readline()
                    continue  # Comment.
                elif typ == 'ENDDATA':
                    break     # End of input.

                name = 'BC_%d' % (len(self._bcs)+1)

                # Dispatch based on BC type.
                try:
                    new_bc = self.add(name, _REGISTRY[typ](typ))
                except KeyError:
                    self.raise_exception("line %d: unrecognized BC type '%s'" \
                                         % (inp.lineno(), typ), ValueError)

                # Read remaining data and add this BC.
                try:
                    new_bc.read(tokens, inp, input_ref)
                except Exception:
                    self.remove(name)
                    raise
                else:
                    self._bcs.append(new_bc)

                line = inp.readline()
        finally:
            inp.close()

    def check_config(self):
        """ Check sanity of current configuration. """
        for _bc in self._bcs:
            _bc.check_config()

    def write(self, casename, input_ref=None):
        """
        Write boundary condition information to ``<casename>.boundata``.
        `input_ref` provides a :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = bc.INPUT

        with open(casename+'.boundata', 'w') as out:
            out.write("""\
# B        L   L L L L L L L   L   L   M   M   N   N   M   M   N   N
# C        B   B F F D D S S   1   2   1   1   1   1   2   2   2   2
# T        L   L A A I I P P   L   L   L   L   L   L   L   L   L   L
# Y        O   O C C R R E E   I   I   I   I   I   I   I   I   I   I
# P        C   C E E 1 2 C C   M   M   M   M   M   M   M   M   M   M
# E        K   K 1 2     1 2           1   2   1   2   1   2   1   2
#          1   2
# ------ --- --- - - - - - - --- --- --- --- --- --- --- --- --- ---
""")
            for i, _bc in enumerate(self._bcs):
                _bc.write(out, i+1, input_ref)

    def schedule(self):
        """
        Perform a (simple-minded) enhanced scheduling of the boundary
        conditions. On a realistic test case the improvement was measurable
        (approx 7%), though not significant. Currently only 'PATCH' boundary
        conditions are scheduled. Including other BCs may improve the enhanced
        scheduling effect.

        .. warning::
           if patches intentionally overlap, this rescheduling may break
           the configuration!

        """
        local = []        # Patch within a block.
        patches = []      # Patch between blocks.
        non_patches = []  # Non-patch BCs.

        # Split into patch & non-patch BCs.
        # Only schedule *communicating* patches.
        for _bc in self._bcs:
            if _bc.type_name == 'PATCH':
                if _bc.lblock1 != _bc.lblock2:
                    # Insertion sort by decreasing size, increasing lblock1.
                    size = _bc.size()
                    for i, patch in enumerate(patches):
                        if size > patch.size() or \
                           size == patch.size() and _bc.lblock1 < patch.lblock1:
                            patches.insert(i, _bc)
                            break
                    else:
                        patches.append(_bc)
                else:
                    local.append(_bc)
            else:
                non_patches.append(_bc)

        # Now schedule for communications.

        # Combine exchanges into pairs of patches.
        pairs = []
        while patches:
            bc1 = patches[0]

            # Look for other half of exchange.
            for i, bc2 in enumerate(patches):
                if (bc2.lblock1 == bc1.lblock2) and \
                   (bc2.lblock2 == bc1.lblock1):
                    pairs.append(BCPair(bc1, bc2, bc1.lblock1, bc1.lblock2))
                    patches.pop(i)
                    patches.pop(0)
                    break
            else:
                msg = 'No match for PATCH BC lblock1 %d, lblock2 %d' \
                      % (bc1.lblock1, bc1.lblock2)
                self.raise_exception(msg, RuntimeError)

        # Determine highest block number.
        max_block = 0
        for pair in pairs:
            max_block = max(max_block, pair.lblock1, pair.lblock2)

        sched = []    # Scheduled exchanges.
        pending = []  # Waiting on busy.
        while pairs:
            self._logger.debug('schedule: new pass')

            # Clear busy flags (block numbers use 1-origin).
            busy = [False] * (max_block+1)

            # Process any pending blocks.
#TODO: Try to find way to 'unblock' best pair.
#      Currently a small pending scheduled here can block a larger pair
#      not yet processed.
            for pair in pending:
                self._logger.debug('    not-pending: %d %d %d',
                                   pair.lblock1, pair.lblock2, pair.bc1.size())
                sched.append(pair)
                busy[pair.lblock1] = True
                busy[pair.lblock2] = True
            pending = []

            # Process remaining pairs.
            self._logger.debug('    pairs:')
            for pair in pairs:
                self._logger.debug('       %d %d %d',
                                   pair.lblock1, pair.lblock2, pair.bc1.size())

            processed = []
            for pair in pairs:
                if busy[pair.lblock1]:
                    if busy[pair.lblock2]:
                        self._logger.debug('    busy: %d %d %d', pair.lblock1,
                                           pair.lblock2, pair.bc1.size())
                        continue
                    else:
                        self._logger.debug('    pending: %d %d %d', pair.lblock1,
                                           pair.lblock2, pair.bc1.size())
                        busy[pair.lblock2] = True
                        pending.append(pair)
                        processed.append(pair)
                else:
                    if busy[pair.lblock2]:
                        self._logger.debug('    pending: %d %d %d', pair.lblock1,
                                          pair.lblock2, pair.bc1.size())
                        pending.append(pair)
                    else:
                        self._logger.debug('    scheduled: %d %d %d', pair.lblock1,
                                           pair.lblock2, pair.bc1.size())
                        busy[pair.lblock2] = True
                        sched.append(pair)
                    busy[pair.lblock1] = True
                    processed.append(pair)

            for pair in processed:
                pairs.remove(pair)

        # Copy any pending blocks to end of schedule.
        for pair in pending:
            self._logger.debug('    not-pending: %d %d %d',
                               pair.lblock1, pair.lblock2, pair.bc1.size())
            sched.append(pair)

        # Merge scheduled patches & non-patches.
        self._bcs = []
        self._bcs.extend(local)
        for pair in sched:
            self._bcs.append(pair.bc1)
            self._bcs.append(pair.bc2)
        self._bcs.extend(non_patches)


def main():  # pragma no cover
    """
    Quick test: read ``<casename>.boundata`` file, and then write to
    ``<casename>_new.boundata`` file. Optionally schedules 'PATCH'
    boundary conditions.

    Usage: ``python boundata.py [--schedule] casename``
    """
    if len(sys.argv) > 1:
        schedule = sys.argv[1] == '--schedule'
        casename = sys.argv[-1]
        boundata = Boundata()
        boundata.read(casename)
        if schedule:
            boundata.schedule()
        boundata.write(casename+'_new')
    else:
        print 'usage: python boundata.py [--schedule] casename'


if __name__ == '__main__':  # pragma no cover
    main()


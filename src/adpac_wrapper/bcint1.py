from openmdao.lib.datatypes.api import Float, Int, Str

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class BCInt1(BC):
    """ ADPAC 'BCINT1' boundary condition. """

    intdir1 = Str(desc='Interpolation direction (I, J, or, K).')
    intdir2 = Str(desc='Interpolation direction (I, J, or, K).')
    ishftdr = Int(low=1, high=3, desc='Periodic shift direction (1, 2, or 3).')
    dshift = Float(desc='Shift increment.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(BCInt1, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().upper().split()
        if len(tokens) != 2:
            self.raise_exception('line %d: expecting 2 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        self.intdir1 = tokens[0]
        self.intdir2 = tokens[1]

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 2:
            self.raise_exception('line %d: expecting 2 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            self.ishftdr = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: ishftdr (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        try:
            self.dshift  = float(tokens[1])
        except ValueError:
            self.raise_exception('line %d: dshift (%s) must be a number.' \
                                 % (inp.lineno(), tokens[1]), ValueError)

    def check_config(self):
        """ Check sanity of current configuration. """
        super(BCInt1, self).check_config()

        if self.intdir1 not in ('I', 'J', 'K'):
            self.raise_exception('intdir1 (%s) must be I, J, or K.' \
                                 % self.intdir1, ValueError)

        if self.intdir2 not in ('I', 'J', 'K'):
            self.raise_exception('intdir2 (%s) must be I, J, or K.' \
                                 % self.intdir2, ValueError)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('\n')
        super(BCInt1, self).write(out, count, input_ref)

        out.write(' INTDIR1 INTDIR2\n')
        out.write(' %s %s\n' % (self.intdir1, self.intdir2))

        out.write(' ISHFTDR DSHIFT\n')
        out.write(' %d %r\n' % (self.ishftdr, self.dshift))


register('BCINT1', BCInt1)


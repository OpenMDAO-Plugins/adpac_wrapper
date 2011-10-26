from openmdao.main.api import Container
from openmdao.lib.datatypes.api import Int, Str

from adpac_wrapper.bcprr import BCPRR
from adpac_wrapper.boundata import register


class BCPRM(BCPRR):
    """
    ADPAC 'BCPRM' boundary condition.

    Receiving block definitions are held in :class:`BCPRM_recv` child objects
    named ``recv_<NN>``.
    """

    def __init__(self, *args, **kwargs):
        super(BCPRM, self).__init__(*args, **kwargs)
        self._recv = []

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(BCPRM, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            nrrdat = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: nrrdat (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        if nrrdat < 1:
            self.raise_exception('line %d: nrrdat (%d) must be >= 1.' \
                                 % (inp.lineno(), nrrdat), ValueError)
        inp.readline()
        for i in range(nrrdat):
            name = 'recv_%d' % (i+1)
            blkdef = self.add(name, BCPRM_recv())
            blkdef.read(inp)
            self._recv.append(blkdef)

    def check_config(self):
        """ Check sanity of current configuration. """
        super(BCPRM, self).check_config()

        if not self._recv:
            self.raise_exception('No receiving blocks specified!', ValueError)

        first_blkdef = self._recv[0]
        for i, blkdef in enumerate(self._recv):
            blkdef.check_config()
            if blkdef.lface1b != first_blkdef.lface1b:
                self.raise_exception('Multiple lface1b requirements at %d.' % i,
                                     ValueError)
            if blkdef.ldir1b != first_blkdef.ldir1b:
                self.raise_exception('Multiple ldir1b requirements at %d.' % i,
                                     ValueError)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(BCPRM, self).write(out, count, input_ref)

        out.write(' NRRDAT\n')
        out.write(' %d\n' % len(self._recv))
        out.write(' LBLOCK1B LFACE1B LDIR1B L1LIMB M1LIM1B M1LIM2B N1LIM1B N1LIM2B\n')
        for blkdef in self._recv:
            blkdef.write(out)

register('BCPRM', BCPRM)


class BCPRM_recv(Container):
    """ :class:`BCPRM` receiving block definition. """

    lblock1b = Int(low=1, desc='Receiving block.')
    lface1b = Str(desc='Grid plane (I, J, or K).')
    ldir1b = Str(desc='Direction into flowfield (P or M).')
    l1limb = Int(low=1, desc='Grid index of surface.')
    m1lim1b = Int(low=1, desc='Initial 1st coord index.')
    m1lim2b = Int(low=1, desc='Initial 2nd coord index.')
    n1lim1b = Int(low=1, desc='Final 1st coord index.')
    n1lim2b = Int(low=1, desc='Final 2nd coord index.')

    def read(self, inp):
        """ Read from stream `inp`. """
        tokens = inp.readline().upper().split()
        if len(tokens) != 8:
            self.raise_exception('line %d: expecting 8 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('lblock1b', 'lface1b', 'ldir1b', 'l1limb',
                                  'm1lim1b', 'm1lim2b', 'n1lim1b', 'n1lim2b')):
            if attr == 'lface1b' or attr == 'ldir1b':
                value = tokens[i]
            else:
                try:
                    value = int(tokens[i])
                except ValueError:
                    self.raise_exception('line %d: %s (%s) must be an integer.' \
                                         % (inp.lineno(), attr, tokens[i]),
                                         ValueError)
            setattr(self, attr, value)

    def check_config(self):
        """ Check sanity of current configuration. """
#TODO: check indices against mesh dimensions, etc.
        if self.lface1b not in ('I', 'J', 'K'):
            self.raise_exception('lface1b (%s) must be I, J, or K.' \
                                 % self.lface1b, ValueError)

        if self.ldir1b not in ('P', 'M'):
            self.raise_exception('ldir1b (%s) must be P or M.' \
                                 % self.ldir1b, ValueError)

        if self.n1lim2b <= self.n1lim1b:
            self.raise_exception('n1lim2b (%d) must be > n1lim1b (%d).' \
                                 % (self.n1lim2b, self.n1lim1b), ValueError)

    def write(self, out):
        """ Write to stream `out`. """
        out.write(' %d %s %s %d %d %d %d %d\n' \
                  % (self.lblock1b, self.lface1b, self.ldir1b, self.l1limb,
                     self.m1lim1b, self.m1lim2b, self.n1lim1b, self.n1lim2b))


from openmdao.main.api import Container
from openmdao.lib.datatypes.api import Float, Int, Str

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class BCPRR(BC):
    """
    ADPAC 'BCPRR' boundary condition.

    Sending block definitions are held in :class:`BCPRR_send` child objects
    named ``send_<NN>``.
    """

    thper = Float(units='rad', desc='Overall circumferential span.')

    def __init__(self, *args, **kwargs):
        super(BCPRR, self).__init__(*args, **kwargs)
        self._send = []

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(BCPRR, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            self.thper = float(tokens[0])
        except ValueError:
            self.raise_exception('line %d: thper (%s) must be a number.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            nbcprr = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: nbcprr (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        if nbcprr < 1:
            self.raise_exception('line %d: nbcprr (%d) must be >= 1.' \
                                 % (inp.lineno(), nbcprr), ValueError)
        inp.readline()
        for i in range(nbcprr):
            name = 'send_%d' % (i+1)
            blkdef = self.add(name, BCPRR_send())
            blkdef.read(inp)
            self._send.append(blkdef)

    def check_config(self):
        """ Check sanity of current configuration. """
        super(BCPRR, self).check_config()

        if not self._send:
            self.raise_exception('No sending blocks specified!', ValueError)

        for blkdef in self._send:
            blkdef.check_config()

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('\n')
        super(BCPRR, self).write(out, count, input_ref)

        out.write(' THPER\n')
        out.write(' %r\n' % self.thper)

        out.write(' NBCPRR\n')
        out.write(' %d\n' % len(self._send))
        out.write(' LBLOCK2B LFACE2B LDIR2B L2LIMB M2LIM1B M2LIM2B N2LIM1B N2LIM2B\n')
        for blkdef in self._send:
            blkdef.write(out)

register('BCPRR', BCPRR)


class BCPRR_send(Container):
    """ :class:`BCPRR` sending block definition. """

    lblock2b = Int(low=1, desc='Sending block.')
    lface2b = Str(desc='Grid plane (I, J, or K).')
    ldir2b = Str(desc='Direction into flowfield (P or M).')
    l2limb = Int(low=1, desc='Grid index of surface.')
    m2lim1b = Int(low=1, desc='Initial 1st coord index.')
    m2lim2b = Int(low=1, desc='Initial 2nd coord index.')
    n2lim1b = Int(low=1, desc='Final 1st coord index.')
    n2lim2b = Int(low=1, desc='Final 2nd coord index.')

    def read(self, inp):
        """ Read from stream `inp`. """
        tokens = inp.readline().upper().split()
        if len(tokens) != 8:
            self.raise_exception('line %d: expecting 8 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('lblock2b', 'lface2b', 'ldir2b', 'l2limb',
                                  'm2lim1b', 'm2lim2b', 'n2lim1b', 'n2lim2b')):
            if attr == 'lface2b' or attr == 'ldir2b':
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
        if self.lface2b not in ('I', 'J', 'K'):
            self.raise_exception('lface2b (%s) must be I, J, or K.' \
                                 % self.lface2b, ValueError)

        if self.ldir2b not in ('P', 'M'):
            self.raise_exception('ldir2b (%s) must be P or M.' \
                                 % self.ldir2b, ValueError)

    def write(self, out):
        """ Write to stream `out`. """
        out.write(' %d %s %s %d %d %d %d %d\n' \
                  % (self.lblock2b, self.lface2b, self.ldir2b, self.l2limb,
                     self.m2lim1b, self.m2lim2b, self.n2lim1b, self.n2lim2b))


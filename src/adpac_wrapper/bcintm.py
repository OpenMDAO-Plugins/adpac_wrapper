from openmdao.main.api import Container
from openmdao.lib.datatypes.api import Int, Str

from adpac_wrapper.bcint1 import BCInt1
from adpac_wrapper.boundata import register


class BCIntM(BCInt1):
    """
    ADPAC 'BCINTM' boundary condition.

    Sending block definitions are held in :class:`BCIntM_send` child objects
    named ``send_<NN>``, while receiving block definitions are held in
    :class:`BCIntM_recv` child objects named ``recv_<NN>``.
    """

    def __init__(self, *args, **kwargs):
        super(BCIntM, self).__init__(*args, **kwargs)
        self._send = []  # Sending block definitions.
        self._recv = []  # Receiving block definitions.

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(BCIntM, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            nblint2 = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: nblint2 (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        if nblint2 < 1:
            self.raise_exception('line %d: nblint2 (%d) must be >= 1.' \
                                 % (inp.lineno(), nblint2), ValueError)
        inp.readline()
        for i in range(nblint2):
            name = 'send_%d' % (i+1)
            blkdef = self.add(name, BCIntM_send())
            blkdef.read(inp)
            self._send.append(blkdef)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            nblint1 = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: nblint1 (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        if nblint1 < 1:
            self.raise_exception('line %d: nblint1 (%d) must be >= 1.' \
                                 % (inp.lineno(), nblint1), ValueError)
        inp.readline()
        for i in range(nblint1):
            name = 'recv_%d' % (i+1)
            blkdef = self.add(name, BCIntM_recv())
            blkdef.read(inp)
            self._recv.append(blkdef)

    def check_config(self):
        """ Check sanity of current configuration. """
        super(BCIntM, self).check_config()

        if not self._send:
            self.raise_exception('No sending blocks specified!', ValueError)

        if not self._recv:
            self.raise_exception('No receiving blocks specified!', ValueError)

        for blkdef in self._send:
            blkdef.check_config()

        first_blkdef = self._recv[0]
        for i, blkdef in enumerate(self._recv):
            blkdef.check_config()
            if blkdef.lface1 != first_blkdef.lface1:
                self.raise_exception('Multiple lface1 requirements at %d.' % i,
                                     ValueError)
            if blkdef.ldir1 != first_blkdef.ldir1:
                self.raise_exception('Multiple ldir1 requirements at %d.' % i,
                                     ValueError)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(BCIntM, self).write(out, count, input_ref)

        out.write(' NBLINT2\n')
        out.write(' %d\n' % len(self._send))
        out.write(' NBLDAT LFACE2 LDIR2 L2LIM M2LIM1 M2LIM2 N2LIM1 N2LIM2\n')
        for blkdef in self._send:
            blkdef.write(out)

        out.write(' NBLINT1\n')
        out.write(' %d\n' % len(self._recv))
        out.write(' LBLK1RR LFACE1 LDIR1 L1LIM M1LIM1 M1LIM2 N1LIM1 N1LIM2\n')
        for blkdef in self._recv:
            blkdef.write(out)

register('BCINTM', BCIntM)


class BCIntM_send(Container):
    """ :class:`BCIntM` sending block definition. """

    nbldat = Int(low=1, desc='Sending block.')
    lface2 = Str(desc='Grid plane (I, J, or K).')
    ldir2 = Str(desc='Direction into flowfield (P or M).')
    l2lim = Int(low=1, desc='Grid index of surface.')
    m2lim1 = Int(low=1, desc='Initial 1st coord index.')
    m2lim2 = Int(low=1, desc='Initial 2nd coord index.')
    n2lim1 = Int(low=1, desc='Final 1st coord index.')
    n2lim2 = Int(low=1, desc='Final 2nd coord index.')

    def read(self, inp):
        """ Read from stream `inp`. """
        tokens = inp.readline().upper().split()
        if len(tokens) != 8:
            self.raise_exception('line %d: expecting 8 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('nbldat', 'lface2', 'ldir2', 'l2lim',
                                  'm2lim1', 'm2lim2', 'n2lim1', 'n2lim2')):
            if attr == 'lface2' or attr == 'ldir2':
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
        if self.lface2 not in ('I', 'J', 'K'):
            self.raise_exception('lface2 (%s) must be I, J, or K.' \
                                 % self.lface2, ValueError)

        if self.ldir2 not in ('P', 'M'):
            self.raise_exception('ldir2 (%s) must be P or M.' \
                                 % self.ldir2, ValueError)

    def write(self, out):
        """ Write to stream `out`. """
        out.write(' %d %s %s %d %d %d %d %d\n' \
                  % (self.nbldat, self.lface2, self.ldir2, self.l2lim,
                     self.m2lim1, self.m2lim2, self.n2lim1, self.n2lim2))


class BCIntM_recv(Container):
    """ :class:`BCIntM` receiving block definition. """

    lblk1rr = Int(low=1, desc='Receiving block.')
    lface1 = Str(desc='Grid plane (I, J, or K).')
    ldir1 = Str(desc='Direction into flowfield (P or M).')
    l1lim = Int(low=1, desc='Grid index of surface.')
    m1lim1 = Int(low=1, desc='Initial 1st coord index.')
    m1lim2 = Int(low=1, desc='Initial 2nd coord index.')
    n1lim1 = Int(low=1, desc='Final 1st coord index.')
    n1lim2 = Int(low=1, desc='Final 2nd coord index.')

    def read(self, inp):
        """ Read from stream `inp`. """
        tokens = inp.readline().upper().split()
        if len(tokens) != 8:
            self.raise_exception('line %d: expecting 8 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('lblk1rr', 'lface1', 'ldir1', 'l1lim',
                                  'm1lim1', 'm1lim2', 'n1lim1', 'n1lim2')):
            if attr == 'lface1' or attr == 'ldir1':
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
        if self.lface1 not in ('I', 'J', 'K'):
            self.raise_exception('lface1 (%s) must be I, J, or K.' \
                                 % self.lface1, ValueError)

        if self.ldir1 not in ('P', 'M'):
            self.raise_exception('ldir1 (%s) must be P or M.' \
                                 % self.ldir1, ValueError)

        if self.m1lim2 <= self.m1lim1:
            self.raise_exception('m1lim2 (%d) must be > m1lim1 (%d).' \
                                 % (self.m1lim2, self.m1lim1), ValueError)

        if self.n1lim2 < self.n1lim1:
            self.raise_exception('n1lim2 (%d) must be >= n1lim1 (%d).' \
                                 % (self.n1lim2, self.n1lim1), ValueError)

    def write(self, out):
        """ Write to stream `out`. """
        out.write(' %d %s %s %d %d %d %d %d\n' \
                  % (self.lblk1rr, self.lface1, self.ldir1, self.l1lim,
                     self.m1lim1, self.m1lim2, self.n1lim1, self.n1lim2))


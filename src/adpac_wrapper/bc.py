from openmdao.main.api import Container
from openmdao.lib.datatypes.api import Int, Str

from adpac_wrapper.boundata import register


class BC(Container):
    """
    Base class for ADPAC boundary conditions.
    `type_name` is the boundary condition type, used to distinguish between
    multiple BC types that are handled by a single class.

    This base class is sufficient for the 'EXITP', EXT2DP', 'EXITN', 'INLETN',
    'NPSS', 'PATCH', 'PINT', 'PROBE', 'SSIN', 'SS2DIN', and 'TRAF' boundary
    conditions.
    """

    lblock1 = Int(low=1, desc="This side's block.")
    lblock2 = Int(low=1, desc="Other side's block.")
    lface1 = Str(desc='Grid plane (I, J, or K).')
    lface2 = Str(desc='Grid plane (I, J, or K).')
    ldir1 = Str(desc='Direction into flowfield (P or M).')
    ldir2 = Str(desc='Direction into flowfield (P or M).')
    lspec1 = Str(desc='Special information for this BC (H, I, J, K, L, M, or S)')
    lspec2 = Str(desc='Special information for this BC (H, I, J, K, L, M, or S)')
    l1lim = Int(low=1, desc='Grid index of surface.')
    l2lim = Int(low=1, desc='Grid index of surface.')
    m1lim1 = Int(low=1, desc='Initial 1st coord index.')
    m1lim2 = Int(low=1, desc='Initial 2nd coord index.')
    n1lim1 = Int(low=1, desc='Final 1st coord index.')
    n1lim2 = Int(low=1, desc='Final 2nd coord index.')
    m2lim1 = Int(low=1, desc='Initial 1st coord index.')
    m2lim2 = Int(low=1, desc='Initial 2nd coord index.')
    n2lim1 = Int(low=1, desc='Final 1st coord index.')
    n2lim2 = Int(low=1, desc='Final 2nd coord index.')

    def __init__(self, type_name, *args, **kwargs):
        super(BC, self).__init__(*args, **kwargs)
        self.type_name = type_name

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if len(tokens) < 19:
            self.raise_exception('line %d: expecting 19 fields, got %d.' \
                                 % (inp.linno(), len(tokens)), ValueError)

        for i, attr in enumerate(('', 'lblock1', 'lblock2', 'lface1', 'lface2',
                                  'ldir1', 'ldir2', 'lspec1', 'lspec2',
                                  'l1lim', 'l2lim', 'm1lim1', 'm1lim2',
                                  'n1lim1', 'n1lim2', 'm2lim1', 'm2lim2',
                                  'n2lim1', 'n2lim2')):
            if i == 0:
                continue  # BC type string.
            if i > 2 and i < 9:
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

        if self.lface2 not in ('I', 'J', 'K'):
            self.raise_exception('lface2 (%s) must be I, J, or K.' \
                                 % self.lface2, ValueError)

        if self.ldir1 not in ('P', 'M'):
            self.raise_exception('ldir1 (%s) must be P or M.' \
                                 % self.ldir1, ValueError)

        if self.ldir2 not in ('P', 'M'):
            self.raise_exception('ldir2 (%s) must be P or M.' \
                                 % self.ldir2, ValueError)

        if self.lspec1 not in ('H', 'I', 'J', 'K', 'L', 'M', 'S'):
            self.raise_exception('lspec1 (%s) must be H, I, J, K, L, M, or S.' \
                                 % self.lspec1, ValueError)

        if self.lspec2 not in ('H', 'I', 'J', 'K', 'L', 'M', 'S'):
            self.raise_exception('lspec2 (%s) must be H, I, J, K, L, M, or S.' \
                                 % self.lspec2, ValueError)

        if self.m1lim2 <= self.m1lim1:
            self.raise_exception('m1lim2 (%d) must be > m1lim1 (%d).' \
                                 % (self.m1lim2, self.m1lim1), ValueError)

        if self.n1lim2 < self.n1lim1:
            self.raise_exception('n1lim2 (%d) must be >= n1lim1 (%d).' \
                                 % (self.n1lim2, self.n1lim1), ValueError)

    def size(self):
        """ Compute size of boundary (used by :meth:`boundata.schedule`). """
        m = abs(self.m1lim1 - self.m1lim2) + 1
        n = abs(self.n1lim1 - self.n1lim2) + 1
        return m * n

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('%-8s' % self.type_name)

        out.write('%4d' % self.lblock1)
        out.write('%4d' % self.lblock2)

        out.write(' %s' % self.lface1)
        out.write(' %s' % self.lface2)
        out.write(' %s' % self.ldir1)
        out.write(' %s' % self.ldir2)
        out.write(' %s' % self.lspec1)
        out.write(' %s' % self.lspec2)

        out.write('%4d' % self.l1lim)
        out.write('%4d' % self.l2lim)
        out.write('%4d' % self.m1lim1)
        out.write('%4d' % self.m1lim2)
        out.write('%4d' % self.n1lim1)
        out.write('%4d' % self.n1lim2)
        out.write('%4d' % self.m2lim1)
        out.write('%4d' % self.m2lim2)
        out.write('%4d' % self.n2lim1)
        out.write('%4d' % self.n2lim2)

        out.write('  # BC %d\n' % count)


register('EXITP',  BC)
register('EXT2DP', BC)
register('EXITN',  BC)
register('INLETN', BC)
register('NPSS',   BC)
register('PATCH',  BC)
register('PINT',   BC)
register('PROBE',  BC)
register('SSIN',   BC)
register('SS2DIN', BC)
register('TRAF',   BC)


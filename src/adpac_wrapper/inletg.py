from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class InletG(BC):
    """ ADPAC 'INLETG' & 'INL2DG' boundary conditions. """

    ptot = Float(units='lbf/ft**2', low=0., exclude_low=True, iotype='in',
                 desc='Total pressure.')
    ttot = Float(units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Total temperature.')
    akin = Float(low=0., iotype='in', desc='Turbulent kinetic energy.')
    arin = Float(low=0., iotype='in', desc='Turbulent Reynolds number.')
    theta = Float(units='deg', iotype='in', desc='')
    phi = Float(units='deg', iotype='in', desc='')
    emdot = Float(units='lbm/s', low=0., iotype='in', desc='Mass flow rate.')
    prelax = Float(low=0., iotype='in', desc='Relaxation factor.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        super(InletG, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) < 2 or len(tokens) > 8:
            self.raise_exception('line %d: expecting 2 to 8 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        self.akin   = 0.
        self.arin   = 0.
        self.theta  = 0.
        self.phi    = 0.
        self.emdot  = 0.
        self.prelax = 0.

        for i, attr in enumerate(('ptot', 'ttot', 'akin', 'arin', 'theta',
                                  'phi', 'emdot', 'prelax')):
            if i >= len(tokens):
                break
            try:
                value = float(tokens[i])
            except ValueError:
                self.raise_exception('line %d: %s (%s) must be a number.' \
                                     % (inp.lineno(), attr, tokens[i]),
                                     ValueError)
            setattr(self, attr, value)
        
        self.ptot *= input_ref.pref
        self.ttot *= input_ref.tref

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        out.write('\n')
        super(InletG, self).write(out, count, input_ref)

        tokens = 2
        if self.akin > 0:
            tokens = 3
        if self.arin > 0:
            tokens = 4
        if self.emdot > 0:
            tokens = 6
        if self.prelax > 0:
            tokens = 7

        out.write(' PTOT TTOT')
        if tokens > 2:
            out.write(' AKIN')
        if tokens > 3:
            out.write(' ARIN')
        if tokens > 4:
            out.write(' THETA')
            out.write(' PHI')
            out.write(' EMDOT')
        if tokens > 6:
            out.write(' PRELAX')
        out.write('\n')

        out.write(' %r %r' \
                  % (self.ptot / input_ref.pref, self.ttot / input_ref.tref))
        if tokens > 2:
            out.write(' %r' % self.akin)
        if tokens > 3:
            out.write(' %r' % self.arin)
        if tokens > 4:
            out.write(' %r %r %r' % (self.theta, self.phi, self.emdot))
        if tokens > 6:
            out.write(' %r' % self.prelax)
        out.write('\n')


register('INLETG', InletG)
register('INL2DG', InletG)


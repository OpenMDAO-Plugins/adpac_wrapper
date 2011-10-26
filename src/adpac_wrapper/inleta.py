from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class InletA(BC):
    """ ADPAC 'INLETA' & 'INL2DA' boundary conditions. """

    ptot = Float(units='lbf/ft**2', low=0., exclude_low=True, iotype='in',
                 desc='Total pressure.')
    ttot = Float(units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Total temperature.')
    alpha = Float(units='deg', iotype='in', desc='Angle of attack.')
    akin = Float(low=0., iotype='in', desc='Turbulent kinetic energy.')
    arin = Float(low=0., iotype='in', desc='Turbulent Reynolds number.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        super(InletA, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) < 3 or len(tokens) > 5:
            self.raise_exception('line %d: expecting 3, 4, or 5 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        self.akin = 0.
        self.arin = 0.
        for i, attr in enumerate(('ptot', 'ttot', 'alpha', 'akin', 'arin')):
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
        super(InletA, self).write(out, count, input_ref)

        out.write(' PTOT TTOT ALPHA')
        if self.akin > 0:
            out.write(' AKIN')
            if self.arin > 0:
                out.write(' ARIN')
        out.write('\n')

        out.write(' %r %r %r' \
                  % (self.ptot / input_ref.pref, self.ttot / input_ref.tref,
                     self.alpha))
        if self.akin > 0:
            out.write(' %r' % self.akin)
            if self.arin > 0:
                out.write(' %r' % self.arin)
        out.write('\n')


register('INLETA', InletA)
register('INL2DA', InletA)


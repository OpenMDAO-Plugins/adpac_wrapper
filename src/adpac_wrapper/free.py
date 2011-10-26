from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class Free(BC):
    """ ADPAC 'FREE' & 'FRE2D' boundary conditions. """

    ptot = Float(units='lbf/ft**2', low=0., exclude_low=True, iotype='in',
                 desc='Total pressure.')
    ttot = Float(units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Total temperature.')
    eminf = Float(low=0., iotype='in', desc='Mach number.')
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

        super(Free, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) < 4 or len(tokens) > 6:
            self.raise_exception('line %d: expecting 4, 5, or 6 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        self.akin = 0.
        self.arin = 0.
        for i, attr in enumerate(('ptot', 'ttot', 'eminf', 'alpha',
                                  'akin', 'arin')):
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
        super(Free, self).write(out, count, input_ref)

        tokens = 4
        if self.akin > 0:
            tokens = 5
        if self.arin > 0:
            tokens = 6

        out.write(' PTOT TTOT EMINF ALPHA')
        if tokens > 4:
            out.write(' AKIN')
        if tokens > 5:
            out.write(' ARIN')
        out.write('\n')

        out.write(' %r %r %r %r' \
                  % (self.ptot / input_ref.pref, self.ttot / input_ref.tref,
                     self.eminf, self.alpha))
        if tokens > 4:
            out.write(' %r' % self.akin)
        if tokens > 5:
            out.write(' %r' % self.arin)
        out.write('\n')


register('FREE',  Free)
register('FRE2D', Free)


from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class Fixed(BC):
    """ ADPAC 'FIXED' boundary condition. """

    ro = Float(units='slug/ft**3', low=0., exclude_low=True, iotype='in',
               desc='Density.')
    u = Float(units='ft/s', iotype='in', desc='U velocity.')
    v = Float(units='ft/s', iotype='in', desc='V velocity.')
    w = Float(units='ft/s', iotype='in', desc='W velocity.')
    ttot = Float(units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Total temperature.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(Fixed, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 5:
            self.raise_exception('line %d: expecting 5 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('ro', 'u', 'v', 'w', 'ttot')):
            try:
                value = float(tokens[i])
            except ValueError:
                self.raise_exception('line %d: %s (%s) must be a number.' \
                                     % (inp.lineno(), attr, tokens[i]),
                                     ValueError)
            setattr(self, attr, value)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('\n')
        super(Fixed, self).write(out, count, input_ref)

        out.write(' RO U V W TTOT\n')
        out.write(' %r %r %r %r %r\n' \
                  % (self.ro, self.u, self.v, self.w, self.ttot))


register('FIXED', Fixed)


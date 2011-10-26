from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class SSVI(BC):
    """ ADPAC 'SSVI' & 'SS2DVI' boundary conditions. """

    rpmwall = Float(units='rpm', iotype='in', desc='Wall rotational speed.')
    twall = Float(units='degR', low=0., iotype='in', desc='Wall temperature.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(SSVI, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 2:
            self.raise_exception('line %d: expecting 2 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('rpmwall', 'twall')):
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
        super(SSVI, self).write(out, count, input_ref)

        out.write(' RPMWALL TWALL\n')
        out.write(' %r %r\n' % (self.rpmwall, self.twall))


register('SSVI',   SSVI)
register('SS2DVI', SSVI)


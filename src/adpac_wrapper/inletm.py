from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class InletM(BC):
    """ ADPAC 'INLETM' & 'INL2DM' boundary conditions. """

    emdot = Float(units='lbm/s', low=0., iotype='in',
                  desc='Mass flow rate.')
    ttot = Float(units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Total temperature.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        super(InletM, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 2:
            self.raise_exception('line %d: expecting 2 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('emdot', 'ttot')):
            try:
                value = float(tokens[i])
            except ValueError:
                self.raise_exception('line %d: %s (%s) must be a number.' \
                                     % (inp.lineno(), attr, tokens[i]),
                                     ValueError)
            setattr(self, attr, value)

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
        super(InletM, self).write(out, count, input_ref)

        out.write(' EMDOT TTOT\n')
        out.write(' %r %r\n' % (self.emdot, self.ttot / input_ref.tref))


register('INLETM', InletM)
register('INL2DM', InletM)


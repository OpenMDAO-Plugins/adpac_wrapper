from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class LamSS(BC):
    """ ADPAC 'LAMSS' & 'LAM2DS' boundary conditions. """

    ptot = Float(units='lbf/ft**2', low=0., exclude_low=True, iotype='in',
                 desc='Total pressure.')
    ttot = Float(units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Total temperature.')
    rpmwall = Float(units='rpm', iotype='in', desc='Rotational speed.')
    twall = Float(units='degR', low=0., iotype='in', desc='Wall temperature.')
    aratio = Float(low=0., iotype='in', desc='Porous area ratio.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        super(LamSS, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 5:
            self.raise_exception('line %d: expecting 4 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('ptot', 'ttot', 'rpmwall', 'twall',
                                  'aratio')):
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
        super(LamSS, self).write(out, count, input_ref)

        out.write(' PTOT TTOT RPMWALL TWALL ARATIO\n')
        out.write(' %r %r %r %r %r\n' \
                  % (self.ptot / input_ref.pref, self.ttot / input_ref.tref,
                     self.rpmwall, self.twall, self.aratio))


register('LAMSS',  LamSS)
register('LAM2DS', LamSS)


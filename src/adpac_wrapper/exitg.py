from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class ExitG(BC):
    """
    ADPAC 'EXITG', 'EXT2DG', 'EXITT', 'EXT2DT', & 'EXITX'
    boundary conditions.
    """

    pexit = Float(units='lbf/ft**2', low=0., exclude_low=True, iotype='in',
                  desc='Exit static pressure.')
    emdot = Float(units='lbm/s', low=0., iotype='in',
                  desc='Mass flow rate.')
    prelax = Float(low=0., high=1., iotype='in',
                   desc='Relaxation factor.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        super(ExitG, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1 and len(tokens) != 3:
            self.raise_exception('line %d: expecting 1 or 3 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            self.pexit = float(tokens[0]) * input_ref.pref
        except ValueError:
            self.raise_exception('line %d: pexit (%s) must be a number.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        if len(tokens) == 3:
            try:
                self.emdot = float(tokens[1])
            except ValueError:
                self.raise_exception('line %d: emdot (%s) must be a number.' \
                                     % (inp.lineno(), tokens[1]), ValueError)
            try:
                self.prelax = float(tokens[2])
            except ValueError:
                self.raise_exception('line %d: prelax (%s) must be a number.' \
                                     % (inp.lineno(), tokens[2]), ValueError)
        else:
            self.emdot = 0.
            self.prelax = 0.

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        out.write('\n')
        super(ExitG, self).write(out, count, input_ref)

        if self.emdot:
            out.write(' PEXIT EMDOT PRELAX\n')
            out.write(' %r %r %r\n' \
                      % (self.pexit / input_ref.pref, self.emdot, self.prelax))
        else:
            out.write(' PEXIT\n')
            out.write(' %r\n' % (self.pexit / input_ref.pref))


register('EXITG',  ExitG)
register('EXT2DG', ExitG)
register('EXITT',  ExitG)
register('EXT2DT', ExitG)
register('EXITX',  ExitG)


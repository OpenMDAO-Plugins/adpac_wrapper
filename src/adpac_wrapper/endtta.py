from openmdao.lib.datatypes.api import Int, Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class EndTTA(BC):
    """ ADPAC 'ENDTTA' boundary condition. """

    ntreat = Int(low=1, iotype='in',
                 desc='Number of treatments per rotor.')
    rpmwall = Float(units='rpm', iotype='in',
                    desc='Rotational speed of endwall regions.')
    twall = Float(units='R', low=0., iotype='in',
                  desc='Wall temperature.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        super(EndTTA, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 3:
            self.raise_exception('line %d: expecting 3 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            self.ntreat = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: ntreat (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        try:
            self.rpmwall = float(tokens[1])
        except ValueError:
            self.raise_exception('line %d: rpmwall (%s) must be a number.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        try:
            self.twall = float(tokens[2]) * input_ref.tref
        except ValueError:
            self.raise_exception('line %d: twall (%s) must be a number.' \
                                 % (inp.lineno(), tokens[0]), ValueError)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        out.write('\n')
        super(EndTTA, self).write(out, count, input_ref)

        out.write(' NTREAT RPMWALL TWALL\n')
        out.write(' %d %r %r\n' \
                  % (self.ntreat, self.rpmwall, self.twall / input_ref.tref))


register('ENDTTA', EndTTA)


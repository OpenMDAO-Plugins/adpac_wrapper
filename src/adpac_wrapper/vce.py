from openmdao.lib.datatypes.api import Int

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class VCE(BC):
    """ ADPAC 'VCE'/'MDICE' boundary condition. """

    global_id = Int(iotype='in', desc='Interface identifier.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(VCE, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('global_id',)):
            try:
                value = int(tokens[i])
            except ValueError:
                self.raise_exception('line %d: %s (%s) must be an integer.' \
                                     % (inp.lineno(), attr, tokens[i]),
                                     ValueError)
            setattr(self, attr, value)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('\n')
        super(VCE, self).write(out, count, input_ref)

        out.write(' GLOBAL ID\n')
        out.write(' %d\n' % self.global_id)


register('VCE', VCE)


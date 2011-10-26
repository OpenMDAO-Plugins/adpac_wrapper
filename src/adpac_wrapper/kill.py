from openmdao.lib.datatypes.api import Int

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class Kill(BC):
    """ ADPAC 'KILL' & 'KIL2D' boundary conditions. """

    lstart = Int(low=1, iotype='in', desc='Initial index.')
    lend = Int(low=1, iotype='in', desc='Final index.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(Kill, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 2:
            self.raise_exception('line %d: expecting 2 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('lstart', 'lend')):
            try:
                value = int(tokens[i])
            except ValueError:
                self.raise_exception('line %d: %s (%s) must be an integer.' \
                                     % (inp.lineno(), attr, tokens[i]),
                                     ValueError)
            setattr(self, attr, value)

    def check_config(self):
        """ Check sanity of current configuration. """
#TODO: check indices against mesh dimensions, etc.
        super(Kill, self).check_config()

        if self.lend <= self.lstart:
            self.raise_exception('lend (%d) must be > lstart (%d).' \
                                 % (self.lend, self.lstart), ValueError)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('\n')
        super(Kill, self).write(out, count, input_ref)

        out.write(' LSTART LEND\n')
        out.write(' %d %d\n' % (self.lstart, self.lend))


register('KILL',  Kill)
register('KIL2D', Kill)


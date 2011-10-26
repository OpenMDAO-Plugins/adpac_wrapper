from openmdao.lib.datatypes.api import Str

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class BDatIn(BC):
    """ ADPAC 'BDATIN' and 'BDATOU' boundary conditions. """

    filename = Str(iotype='in', desc='Filename for boundary data.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(BDatIn, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        self.filename = tokens[0]

    def check_config(self):
        """ Check sanity of current configuration. """
        super(BDatIn, self).check_config()

        if not self.filename:
            self.raise_exception('filename must be specified.', ValueError)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('\n')
        super(BDatIn, self).write(out, count, input_ref)

        out.write(' FILENAME\n')
        out.write(' %s\n' % self.filename)


register('BDATIN', BDatIn)
register('BDATOU', BDatIn)


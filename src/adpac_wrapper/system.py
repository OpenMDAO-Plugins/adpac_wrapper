from openmdao.lib.datatypes.api import Int, Str

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register


class System(BC):
    """ ADPAC 'SYSTEM' boundary condition. """

    interval = Int(low=1, iotype='in', desc='Interval between executions.')
    command = Str(iotype='in', desc='Command to execute.')

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        super(System, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            self.interval = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: interval (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        inp.readline()
        self.command = inp.readline().strip()

    def check_config(self):
        """ Check sanity of current configuration. """
        super(System, self).check_config()

        if not self.command:
            self.raise_exception('command must be specified.', ValueError)

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write('\n')
        super(System, self).write(out, count, input_ref)

        out.write(' INTERVAL\n')
        out.write(' %d\n' % self.interval)
        out.write(' COMMAND\n')
        out.write('%s\n' % self.command)


register('SYSTEM', System)


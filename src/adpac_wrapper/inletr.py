from openmdao.main.api import Container
from openmdao.lib.datatypes.api import Float

from adpac_wrapper.bc import BC
from adpac_wrapper.boundata import register, INPUT


class InletR(BC):
    """
    ADPAC 'INLETR' & 'INL2DR' boundary conditions.

    Inflow data definitions are held in :class:`InletR_data` child objects
    named ``data_<NN>``.
    """

    def __init__(self, *args, **kwargs):
        super(InletR, self).__init__(*args, **kwargs)
        self._data = []

    def read(self, tokens, inp, input_ref):
        """
        Read BC from current line `tokens` and then from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        super(InletR, self).read(tokens, inp, input_ref)

        inp.readline()
        tokens = inp.readline().split()
        if len(tokens) != 1:
            self.raise_exception('line %d: expecting 1 field, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)
        try:
            ndata = int(tokens[0])
        except ValueError:
            self.raise_exception('line %d: ndata (%s) must be an integer.' \
                                 % (inp.lineno(), tokens[0]), ValueError)
        if ndata < 1:
            self.raise_exception('line %d: ndata (%d) must be >= 1.' \
                                 % (inp.lineno(), ndata), ValueError)
        inp.readline()
        for i in range(ndata):
            name = 'data_%d' % (i+1)
            data = self.add(name, InletR_data())
            data.read(inp, input_ref)
            self._data.append(data)

    def check_config(self):
        """ Check sanity of current configuration. """
        super(InletR, self).check_config()

        if not self._data:
            self.raise_exception('No data definitions!', ValueError)

        if len(self._data) < 3:
            self.raise_exception('To few data definitions (need at least 3)',
                                 ValueError)
        prev = None
        for data in self._data:
            if prev is not None:
                if data.axial <= prev.axial:
                    self.raise_exception('axial coordinate non-monotonic',
                                         ValueError)
            prev = data

    def write(self, out, count, input_ref):
        """
        Write BC `count` to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        if input_ref is None:
            self._logger.warning('Using default reference values.')
            input_ref = INPUT

        out.write('\n')
        super(InletR, self).write(out, count, input_ref)

        out.write(' NDATA\n')
        out.write(' %d\n' % len(self._data))
        out.write(' AXIAL PTOT TTOT BETAX BETAT\n')
        for data in self._data:
            data.write(out, input_ref)

register('INLETR', InletR)
register('INL2DR', InletR)


class InletR_data(Container):
    """ Inflow data for :class:`InletR`. """

    axial = Float(units='ft', iotype='in', desc='Axial coordinate.')
    ptot = Float(units='lbf/ft**2', low=0., exclude_low=True, iotype='in',
                 desc='Total pressure.')
    ttot = Float(units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Total temperature.')
    betax = Float(units='deg', iotype='in', desc='Axial flow angle.')
    betat = Float(units='deg', iotype='in', desc='Circumferential flow angle.')

    def read(self, inp, input_ref):
        """
        Read BC from stream `inp`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        tokens = inp.readline().split()
        if len(tokens) != 5:
            self.raise_exception('line %d: expecting 5 fields, got %d.' \
                                 % (inp.lineno(), len(tokens)), ValueError)

        for i, attr in enumerate(('axial', 'ptot', 'ttot', 'betax', 'betat')):
            try:
                value = float(tokens[i])
            except ValueError:
                self.raise_exception('line %d: %s (%s) must be a number.' \
                                     % (inp.lineno(), attr, tokens[i]),
                                     ValueError)
            setattr(self, attr, value)

        self.ptot *= input_ref.pref
        self.ttot *= input_ref.tref

    def write(self, out, input_ref):
        """
        Write BC to stream `out`.
        `input_ref` provides an :class:`Input` object for reference conditions.
        """
        out.write(' %r %r %r %r %r\n' \
                  % (self.axial, self.ptot / input_ref.pref,
                     self.ttot / input_ref.tref, self.betax, self.betat))


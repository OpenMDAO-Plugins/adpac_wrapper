import fileinput
import os.path
import re
import sys

from openmdao.main.api import Container
from openmdao.lib.datatypes.api import Bool, Float, Int, List, Str

# Define units we need.
from adpac_wrapper.local_units import add_units
add_units()


# Line formats:
# <whitespace><#EOF> : end-of-file.
# <whitespace><#> : comment.
# <whitespace><name><whitespace><=><whitespace><value> : assignment.
_EOF_RE = re.compile(r'[ \t]*#EOF')
_COMMENT_RE = re.compile(r'([ \t]*#)|([ \t]*$)')
_LINE_RE = re.compile(r'[ \t]*([a-zA-Z0-9()]+)[ \t]+=[ \t]+([_a-zA-Z0-9.\-+]+)')

# Name formats:
# <alphanum><(><digits><)> : array.
# <alphanum> : scalar.
_ARRAY_RE = re.compile(r'([a-zA-Z][a-zA-Z0-9]*)\(([1-9][0-9]*)\)$')
_SCALAR_RE = re.compile(r'([a-zA-Z][a-zA-Z0-9]*)$')

# Special per-block variables.
_PER_BLOCK_VARS = (
    'advr',
    'bffile',
    'dfactc',
    'fcarb',
    'flive',
    'fturbcht',
    'lofile',
    'nbld',
    'nsl',
    'rpm',
    'rvtfile',
    'tplfile',
    'wbf'
)


class Input(Container):
    """ ADPAC input file handling. """

    casename = Str('', iotype='in',
                   desc='Base name of related files.')
    ccp = Float(1.6, low=1.0, high=1.8, iotype='in',
                desc='Baldwin-Lomax turbulence model coefficient.')
    cfl = Float(-5., iotype='in',
                desc='<0 steady flow, >0 unsteady flow.')
    cfmax = Float(2.5, iotype='in',
                  desc='Max time step multiplier without residual smoothing.')
    ckleb = Float(0.3, iotype='in',
                  desc='Baldwin-Lomax turbulence model coefficient.')
    cmutps = Float(14., iotype='in',
                   desc='Pressure side turbulence transition.')
    cmutss = Float(14., iotype='in',
                   desc='Suction side turbulence transition.')
    diam = Float(1., units='ft', low=0., exclude_low=True, iotype='in',
                 desc='Mesh dimensionalizing length scale.')
    disscg = Float(0., iotype='in',
                   desc='Undocumented (specified in EEE hptnew.input)')
    epstot = Float(0.2, low=0., iotype='in',
                   desc='Post multigrid smoothing coeff.')
    epsx = Float(1., iotype='in',
                 desc='Implicit residual smoothing X coeff.')
    epsy = Float(1., iotype='in',
                 desc='Implicit residual smoothing Y coeff.')
    epsz = Float(1., iotype='in',
                 desc='Implicit residual smoothing Z coeff.')
    f1eq = Bool(False, iotype='in',
                desc='Use one-equation turbulence model.')
    f2eq = Bool(False, iotype='in',
                desc='Use two-equation (k-R) turbulence model.')
    fbconf = Int(0, low=0, iotype='in',
                 desc='Iteration to freeze BCs.')
    fbcwarn = Bool(True, iotype='in',
                   desc='Check BC completeness.')
    fbfmeth = Int(0, iotype='in',
                  desc='Related to the k-R turbulence model.')
    fbfrlx = Float(1., iotype='in',
                   desc='Relaxation factor used when updating body forces.')
    fcambb = Int(99998, iotype='in',
                 desc='Related to the k-R turbulence model.')
    fcombi = Int(1, iotype='in',
                 desc='Related to the k-R turbulence model.')
    fcambe = Int(99999, iotype='in',
                 desc='Related to the k-R turbulence model.')
    fcart = Bool(False, iotype='in',
                 desc='Cartesion/Cylindrical coordinates.')
    fcoag1 = Int(1, low=1, iotype='in',
                 desc="'Full' multigrid initial level.")
    fcoag2 = Int(2, low=1, iotype='in',
                 desc="'Full' multigrid final level.")
    fcocom = Bool(False, iotype='in',
                  desc='Coarse mesh cell area and volume calc.')
    fconvrg = Float(-100., iotype='in',
                    desc='Terminating convergence level (log10).')

#FIXME: apparently these are block numbers, not boolean triggers.
    fdebug_1 = Bool(False, iotype='in',
                    desc='Print XYZ mesh for block.')
    fdebug_2 = Bool(False, iotype='in',
                    desc='Print ZRT mesh for block.')
    fdebug_3 = Bool(False, iotype='in',
                    desc='Print cell face areas for block.')
    fdebug_4 = Bool(False, iotype='in',
                    desc='Print cell volumes for block.')
    fdebug_5 = Bool(False, iotype='in',
                    desc='Print cell flow data for block.')
    fdebug_6 = Bool(False, iotype='in',
                    desc='Print cell time steps for block.')
    fdebug_7 = Bool(False, iotype='in',
                    desc='Print cell convective fluxes for block.')
    fdebug_8 = Bool(False, iotype='in',
                    desc='Print cell dissipative fluxes for block.')
    fdebug_9 = Bool(False, iotype='in',
                    desc='Print cell diffusive fluxes for block.')
    fdebug_10 = Bool(False, iotype='in',
                     desc='Print cell imp. res. smoothing for block.')
    fdebug_11 = Bool(False, iotype='in',
                     desc='Print advance debug for block.')
    fdebug_12 = Bool(False, iotype='in',
                     desc='Print update debug for block.')
    fdebug_13 = Bool(False, iotype='in',
                     desc='Print inject debug for block.')
    fdebug_14 = Bool(False, iotype='in',
                     desc='Print Rforce debug for block.')
    fdebug_15 = Bool(False, iotype='in',
                     desc='Print interp debug for block.')

    fdeltat = Float(0., units='s', low=0., iotype='in',
                    desc='Time-dependent solution time step.')
    fdesign = Bool(False, iotype='in',
                   desc='Use body force design system calculation.')
    fdesrlx = Float(1., iotype='in',
                    desc='Related to the k-R turbulence model.')
    ffast = Bool(False, iotype='in',
                 desc='Use simplified multigrid algorithm.')
    ffilt = Int(1, low=0, high=5, iotype='in',
                desc='Select added dissipation routine:\n'
                     '    0 - None\n'
                     '    1 - hpro3d dissipation\n'
                     '    2 - NASA tm dissipation\n'
                     '    3 - Eigenvalue-scaled dissipation\n'
                     '    4 - Delaney constant coefficient dissipation\n'
                     '    5 - Swanson eigenvalue-scaled dissipation')
    ffulmg = Bool(False, iotype='in',
                  desc="Use 'full' multigrid solution.")
    fgrafint = Int(0, low=0, iotype='in',
                   desc='Internal graphics update interval.')
    fgrafix = Bool(False, iotype='in',
                   desc='Use internal graphics display.')
    fimgint = Int(0, low=0, iotype='in',
                  desc='Image capture interval.')
    fimgsav = Bool(False, iotype='in',
                   desc='Capture images.')
    fimpfac = Int(2, low=-2, high=2, iotype='in',
                  desc='Implicit algorithm time accuracy.')
    fimplic = Bool(False, iotype='in',
                   desc='Use implicit algorithm.')
    finvvi = Bool(False, iotype='in',
                  desc='Viscous/inviscid flow solution.')
    fitchk = Int(100, low=1, iotype='in',
                 desc='Checkpoint interval.')
    fitfmg = Int(0, low=0, iotype='in',
                 desc="'Full' multigrid coarse iterations.")
    fkinf = Float(0.0001, iotype='in',
                  desc='Initial value for turbulence field.')
    flossb = Int(99998, iotype='in',
                 desc='Related to the k-R turbulence model.')
    flosse = Int(99999, iotype='in',
                 desc='Related to the k-R turbulence model.')
    flossi = Int(1, iotype='in',
                 desc='Related to the k-R turbulence model.')
    fmassav = Int(1, iotype='in',
                  desc='Mass averaging algorithm.')
    fmgtstep = Int(1, iotype='in',
                   desc="'Full' multigrid coarse time steps.")
    fmixlen = Float(-1, iotype='in',
                    desc='If >0, enables mixing-length turbulence model.')
    fmulti = Int(1, iotype='in',
                 desc='Multigrid grid levels.')
    fncmax = Int(100, low=0, iotype='in',
                 desc='Maximum iterations.')
    fnsl = Int(11, low=0, iotype='in',
               desc='Number of streamlines for k-R turbulence model.')
    fntstep = Int(1, low=1, iotype='in',
                  desc='Implicit time steps.')
    fpitch = Float(0., iotype='in',
                   desc='Undocumented.')
    frdmul = Bool(False, iotype='in',
                  desc='Read coarse mesh multigrid BCs.')
    fresid = Int(1, low=0, high=4, iotype='in',
                 desc='Implicit residual smoothing scheme:\n'
                      '    0 - None\n'
                      '    1 - Constant coefficient\n'
                      '    2 - Jorgensen-Chima time-accurate\n'
                      '    3 - Hall variable coefficient\n'
                      '    4 - Swanson variable coefficient')
    frest = Int(0, low=-1, high=1, iotype='in',
                desc='Restart scheme:\n'
                     '    0 - No restart file used\n'
                     '    1 - Initialize from restart file\n'
                     '   -1 - Initialize from coarse restart file')
    frinf = Float(0.001, iotype='in',
                  desc='Initial value for k-R turbulence field.')
    frowmx = Float(0, iotype='in',
                   desc='Undocumented (from EEE hptnew.input)')
    frvtupb = Int(99998, iotype='in',
                  desc='Related to the k-R turbulence model.')
    frvtupi = Int(1, iotype='in',
                  desc='Related to the k-R turbulence model.')
    frvtupe = Int(99999, iotype='in',
                  desc='Related to the k-R turbulence model.')
    fsave = Bool(True, iotype='in',
                 desc='Save solution to restart file.')
    fsolve = Int(1, low=0, high=2, iotype='in',
                 desc='Time-marching solution method:\n'
                      '    0 - 4-stage fast algorithm\n'
                      '    1 - 4-stage Runge-Kutta algorithm\n'
                      '    2 - 5-stage Runge-Kutta algorithm')
    fsubit = Int(1, low=1, iotype='in',
                 desc='Coarse grid subiterations.')
    ftimei = Int(1, low=1, high=10, iotype='in',
                 desc='Time step update interval.')
    ftimerm = Int(0, units='s', low=0, iotype='in',
                  desc='CPU time remaining trigger.')
    ftimfac = Float(1., low=1., high=10., iotype='in',
                    desc='Implicit time step limiting.')
    ftotsm = Bool(False, iotype='in',
                  desc='Use post multigrid smoothing.')
    fturbb = Int(10, low=1, iotype='in',
                 desc='Beginning iteration for turb model.')
    fturbf = Int(0, low=0, iotype='in',
                 desc='Freeze iteration for turb model.')
    fturbi = Int(1, low=1, iotype='in',
                 desc='Turb model update interval.')
    funint = Int(0, low=0, iotype='in',
                 desc='Plot3D output interval.')
    fupwind = Bool(False, iotype='in',
                   desc='Use upwind differencing scheme for 2D mesh block solver.')
    fvtsfac = Float(2.5, iotype='in',
                    desc='Viscous time step factor.')
    fwallf = Bool(True, iotype='in',
                  desc='Use wall functions.')
    gamma = Float(1.4, iotype='in',
                  desc='Specific heat ratio.')
    p3dprt = Bool(True, iotype='in',
                  desc='Write Plot3D files.')
    pref = Float(2116.22, units='lbf/ft**2', low=0., exclude_low=True,
                 iotype='in', desc='Reference total pressure.')
    prno = Float(0.7, iotype='in',
                 desc='Prndtl number.')
    prtno = Float(0.9, iotype='in',
                  desc='Turbulent Prndtl number.')
    rgas = Float(1716.26, units='ft*lbf/(slug*R)', iotype='in',
                 desc='Gas constant.')
    rmach = Float(0.5, low=0., iotype='in',
                  desc='Reference mach number.')
    tref = Float(518.67, units='degR', low=0., exclude_low=True, iotype='in',
                 desc='Reference total temperature.')
    vis2 = Float(1./2., low=0., high=2., iotype='in',
                 desc='2nd order dissipation factor.')
    vis4 = Float(1./64., low=0., high=1./16., iotype='in',
                 desc='4th order dissipation factor.')
    viscg2 = Float(1./8., low=0., high=1., iotype='in',
                   desc='Coarse grid 2nd order dissipation.')
    viscg4 = Float(-1, iotype='in',
                   desc='undocumented (from hptnew).')
    xmom = Float(0, iotype='in',
                 desc='X-coordinate of moment component.')
    xtranps = Float(0.1, iotype='in',
                    desc='Pressure side turbulence transition.')
    xtranss = Float(0.1, iotype='in',
                    desc='Suction side turbulence transition.')
    ymom = Float(0, iotype='in',
                 desc='Y-coordinate of moment component.')
    zetarat = Float(0.6, low=0.2, high=0.9, iotype='in',
                    desc='Exponent for dissipation/residual smoothing ratio.')
    zmom = Float(0, iotype='in',
                 desc='Z-coordinate of moment component.')

    # Per-block variables.
    advr = List(iotype='in',
                desc='Block rotational speed in terms of an advance ratio.')
    bffile = List(iotype='in',
                  desc='File for block blade blockage and body force terms.')
    dfactc = List(iotype='in',
                  desc='Diffusion factor.')
    fcarb = List(iotype='in',
                 desc='Cartesian/cylindrical coordinates (-1 => unset).')
    flive = List(iotype='in',
                 desc='Undocumented.')
    fturbcht = List(iotype='in',
                    desc='Use C/O-grid heat transfer turbulence model.')
    lofile = List(iotype='in',
                  desc='Loss coefficient file.')
    nbld = List(iotype='in',
                desc='Number of blades in block.')
    nsl = List(iotype='in',
               desc='Number of streamlines for k-R turbulence model.')
    rpm = List(units='rpm', iotype='in',
               desc='Rotational speed of mesh block.')
    rvtfile = List(iotype='in',
                   desc='Imposed rVtheta distribution.')
    tplfile = List(iotype='in',
                   desc='Total pressure loss profile.')
    wbf = List(iotype='in',
               desc='Write body force file.')

    # Misc.
    header_lines = List(iotype='in',
                        desc='Comment lines before first variable assignment.')

    write_defaults = Bool(False, iotype='in',
                          desc='If False, only non-default values are written.')

    def __init__(self, *args, **kwargs):
        super(Input, self).__init__(*args, **kwargs)
        self._max_blocks = 0  # Maximum number of blocks we know about.

        # Scalar defaults:
#TODO: there should be a cleaner way to do this.
        self._defaults = {}
        for name, value in self.__dict__.items():
            if name[0] != '_':
                self._defaults[name] = value

        # Per-block defaults.
        self._defaults['advr'] = 0.
        self._defaults['bffile'] = 'default_file_name'
        self._defaults['dfactc'] = 0
        self._defaults['fcarb'] = -1
        self._defaults['flive'] = 1.
        self._defaults['fturbcht'] = 0
        self._defaults['lofile'] = 'default_file_name'
        self._defaults['nbld'] = 1
        self._defaults['nsl'] = 11
        self._defaults['rpm'] = 0.
        self._defaults['rvtfile'] = 'default_file_name'
        self._defaults['tplfile'] = 'default_file_name'
        self._defaults['wbf'] = 0

    def create_per_block_vars(self, new_max):
        """ Create all per-block variables up to `new_max`. """
        for i in range(self._max_blocks, new_max):
            for name in _PER_BLOCK_VARS:
                getattr(self, name).append(self._defaults[name])
        self._max_blocks = new_max

    def reset_to_defaults(self):
        """ Reset to default values. """
        for name in self._defaults.keys():
            if name in _PER_BLOCK_VARS:
                setattr(self, name, [])
            else:
                setattr(self, name, self._defaults[name])
        self._max_blocks = 0
        self.header_lines = []

    def read(self, casename):
        """
        Read input from ``<casename>.input``.
        Note that unlike ADPAC, unrecognized keywords are treated as an error.
        """
        self.reset_to_defaults()

        filename = casename+'.input'
        if not os.path.exists(filename):
            msg = "Input file '%s' not found in '%s'." \
                  % (filename, os.getcwd())
            self.raise_exception(msg, IOError)

        errors = 0
        in_header = True
        inp = fileinput.FileInput(filename, mode='rU')
        try:
            for line in inp:
                if re.match(_EOF_RE, line):
                    break
                if re.match(_COMMENT_RE, line):
                    if in_header:
                        self.header_lines.append(line)
                else:
                    in_header = False
                    match = re.match(_LINE_RE, line)
                    if match is None:
                        self._logger.error("line %d: bad format.", inp.lineno())
                        self._logger.error(line.rstrip())
                        errors += 1
                    elif match.group(1).upper == 'ENDINPUT':
                        break
                    else:
                        if not self._process_line(match.group(1),
                                                  match.group(2), inp.lineno()):
                            errors += 1
        finally:
            inp.close()

        if errors:
            self.raise_exception("%d errors in '%s'" % (errors, filename),
                                 RuntimeError)

    def _process_line(self, name, value, lineno):
        """ Process one line's data. """
        block_index = -1
        match = re.match(_ARRAY_RE, name)
        if match is None:
            if not re.match(_SCALAR_RE, name):
                self._logger.error("line %d: '%s' bad format.", lineno, name)
                return False
        else:
            # Handle per-block variable, or FDEBUG array.
            if match.group(1).lower() in _PER_BLOCK_VARS:
                name = match.group(1)
                block_index = int(match.group(2))
            else:
                name = match.group(1)+'_'+match.group(2)

        name = name.lower()
        if not hasattr(self, name):
            # ADPAC would treat this as a comment line.
            self._logger.error("line %d: '%s' not found.", lineno, name)
            return False

        # If necessary, extend per-block variables.
        if block_index > self._max_blocks:
            self.create_per_block_vars(block_index)

        # Assign value, which is represented as a float or a string.
        try:
            float_val = float(value)
        except ValueError:
            pass  # Keep string value.
        else:
            value = float_val

        if block_index < 0:
            current = getattr(self, name)
            if isinstance(current, bool):
                value = bool(value)
            elif isinstance(current, int):
                value = int(value)
            setattr(self, name, value)
        else:
            current = getattr(self, name)[block_index-1]
            if isinstance(current, bool):
                value = bool(value)
            elif isinstance(current, int):
                value = int(value)
            getattr(self, name)[block_index-1] = value
        return True

    def check_config(self):
        """ Check sanity of current configuration. """
        if not self.casename:
            self.raise_exception('Casename must be specified.', ValueError)

        if self.f1eq and self.f2eq:
            self.raise_exception('Cannot run both 1-eq and 2-eq models!',
                                 ValueError)

        if self.fimplic and self.fdeltat <= 0:
            self.raise_exception('fdeltat must be >= 0 for implicit analysis.',
                                 ValueError)

        if self.fsolve < 2 and self.cfmax > 2.75:
            self.raise_exception('fsolve=%d requires cfmax <= 2.75' \
                                 % self.fsolve, ValueError)

    def write(self, casename=None):
        """ Write input to ``<casename>.input``. """
        casename = casename or self.casename
        filename = casename+'.input'

        # Get sorted list of variables.
        varnames = sorted([name for name, var in self.items(iotype='in')])

        with open(filename, 'w') as out:
            for line in self.header_lines:
                out.write(line)

            skip = ['header_lines', 'write_defaults']
            skip.extend(_PER_BLOCK_VARS)
            for name in varnames:
                if name in skip:
                    continue

                value = casename if name == 'casename' else self.get(name)
                if not self.write_defaults:
                    # Minimize lines by skipping defaulted values.
                    if value == self._defaults[name]:
                        continue

                # If boolean or int, map to float.
                if isinstance(value, (bool, int)):
                    value = float(value)

                # Fix FDEBUG array names.
                underscore = name.find('_')
                if underscore > 0:
                    name = '%s(%s)' % (name[:underscore], name[underscore+1:])
               
                # Limit doc to single line.
                doc = self.trait(name).desc
                doc = doc.split('\n')[0]
                out.write('%-10s = %-14s # %s\n' % (name.upper(), value, doc))
            out.write('\n')

            if self._max_blocks:
                # Write per-block variables in groups.
                for name in _PER_BLOCK_VARS:
                    written = False
                    for i in range(self._max_blocks):
                        value = self.get(name)[i]
                        if value != self._defaults[name] or self.write_defaults:
                            fullname = '%s(%d)' % (name.upper(), i+1)
                            if isinstance(value, (bool, int)):
                                value = float(value)
                            out.write('%-10s = %-14s\n' % (fullname, value))
                            written = True
                    if written:
                        out.write('\n')
                out.write('\n')


def main():  # pragma no cover
    """
    Quick test: read ``<casename>.input`` file, and then write to
    ``<casename>_new.input`` file.

    Usage: ``python input.py casename``
    """
    if len(sys.argv) > 1:
        casename = sys.argv[1]
        inp = Input()
        inp.read(casename)
        inp.write(casename+'_new')
    else:
        print 'usage: python input.py casename'


if __name__ == '__main__':  # pragma no cover
    main()


import os.path

from openmdao.main.api import Container
from openmdao.lib.datatypes.api import List


class Converge(Container):
    """ Processes the ADPAC ``<casename>.converge`` output file. """

    max_error = List(float, iotype='out',
                     desc='log10(maximum error value).')
    rms_error = List(float, iotype='out',
                     desc='log10(RMS error value).')
    mass_inflow = List(float, units='lbm/s', iotype='out',
                       desc='Inlet mass flow.')
    mass_outflow = List(float, units='lbm/s', iotype='out',
                        desc='Exit mass flow.')
    pressure_ratio = List(float, iotype='out',
                          desc='Exit/inlet pressure ratio.')
    efficiency = List(float, iotype='out',
                      desc='Adiabatic efficiency.')
    ss_pts = List(int, iotype='out',
                  desc='Number of supersonic points.')
    sep_pts = List(int, iotype='out',
                   desc='Number of seperated points.')

    ptinlt = List(float, units='lbf/ft**2', iotype='out',
                  desc='Inlet total pressure (from unit 42).')
    ttinlt = List(float, units='degR', iotype='out',
                  desc='Inlet total temperature (from unit 42).')
    emavin = List(float, units='lbm/s', iotype='out',
                  desc='Inlet mass flow (from unit 42).')
    ptexit = List(float, units='lbf/ft**2', iotype='out',
                  desc='Exit total pressure (from unit 42).')
    ttexit = List(float, units='degR', iotype='out',
                  desc='Exit total temperature (from unit 42).')
    emavout = List(float, units='lbm/s', iotype='out',
                   desc='Outlet mass flow (from unit 42).')
    eff = List(float, iotype='out',
               desc='Adiabatic efficiency (from unit 42).')

    def clear(self):
        """ Clear data. """
        self.max_error = []
        self.rms_error = []
        self.mass_inflow = []
        self.mass_outflow = []
        self.pressure_ratio = []
        self.efficiency = []
        self.ss_pts = []
        self.sep_pts = []

        self.ptinlt = []
        self.ttinlt = []
        self.emavin = []
        self.ptexit = []
        self.ttexit = []
        self.emavout = []
        self.eff = []

    def read(self, casename):
        """ Read ``<casename>.converge`` data. """
        self.clear()

        with open(casename+'.converge', 'r') as inp:
            line = inp.readline()  # Header lines.
            line = inp.readline()
            line = inp.readline()
            line = inp.readline()
            while line:
                fields = line.split()
                self.max_error.append(float(fields[1]))
                self.rms_error.append(float(fields[2]))
                self.mass_inflow.append(float(fields[3]))
                self.mass_outflow.append(float(fields[4]))
                self.pressure_ratio.append(float(fields[5]))
                self.efficiency.append(float(fields[6]))
                self.ss_pts.append(int(fields[7]))
                self.sep_pts.append(int(fields[8]))
                line = inp.readline()

        # The zooming file (fort.42) is non-standard.
        if not os.path.exists('fort.42'):
            return

        with open('fort.42', 'r') as inp:
            line = inp.readline()  # Header line.
            line = inp.readline()
            while line:
                fields = line.split()
                self.ptinlt.append(float(fields[1]))
                self.ttinlt.append(float(fields[2]))
                self.emavin.append(float(fields[3]))
                self.ptexit.append(float(fields[4]))
                self.ttexit.append(float(fields[5]))
                self.emavout.append(float(fields[6]))
                self.eff.append(float(fields[7]))
                line = inp.readline()

    def write(self, converge_name=None, zoom_name=None):
        """ Write data out as CSV files. """
        converge_name = converge_name or 'converge.csv'
        zoom_name = zoom_name or 'zoom.csv'

        with open(converge_name, 'w') as out:
            out.write('i, max_error, rms_error, mass_inflow, mass_outflow,'
                      ' pressure_ratio, efficiency, ss_pts, sep_pts\n')
            for i in range(len(self.max_error)):
                out.write('%g' % i)
                out.write(', %g' % self.max_error[i])
                out.write(', %g' % self.rms_error[i])
                out.write(', %g' % self.mass_inflow[i])
                out.write(', %g' % self.mass_outflow[i])
                out.write(', %g' % self.pressure_ratio[i])
                out.write(', %g' % self.efficiency[i])
                out.write(', %g' % self.ss_pts[i])
                out.write(', %g\n' % self.sep_pts[i])

        # The zooming file (fort.42) is non-standard.
        if len(self.nstep) <= 0:
            return

        with open(zoom_name, 'w') as out:
            out.write('i, ptinlt, ttinlt, emavin,'
                      ' ptexit, ttexit, emavout, eff\n')
            for i in range(len(self.ptinlt)):
                out.write('%g' % i)
                out.write(', %g' % self.ptinlt[i])
                out.write(', %g' % self.ttinlt[i])
                out.write(', %g' % self.emavin[i])
                out.write(', %g' % self.ptexit[i])
                out.write(', %g' % self.ttexit[i])
                out.write(', %g' % self.emavout[i])
                out.write(', %g\n' % self.eff[i])


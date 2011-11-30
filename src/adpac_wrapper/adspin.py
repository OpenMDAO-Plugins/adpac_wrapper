import os.path

from openmdao.lib.components.external_code import ExternalCode


class Request(object):
    """ Holds ADSPIN request parameters and results. """

    def __init__(self, block, imin, imax, jmin, jmax, kmin, kmax):
        self.block = block
        self.imin = imin
        self.imax = imax
        self.jmin = jmin
        self.jmax = jmax
        self.kmin = kmin
        self.kmax = kmax

        self.a  = -1.
        self.pt = -1.
        self.ps = -1.
        self.tt = -1.
        self.ts = -1.
        self.w  = -1.


class ADSPIN(ExternalCode):
    """ Minimal wrapper for the ADSPIN tool. """

    def __init__(self, casename, *args, **kwargs):
        super(ADSPIN, self).__init__(*args, **kwargs)
        self.casename = casename
        self.requests = []
        self.run_adspin = True

    def add_request(self, request):
        """ Add a request to the list of requests. """
        self.requests.append(request)

    def execute(self):
        """ Run ADSPIN for each request and parse results. """
        self.write_input()

        # Remove output files.
        for name in ('adspin.out', 'adspin.log'):
            if os.path.exists(name):
                os.remove(name)

        if self.run_adspin:
            self.command = ['adspin']
            self.stdin = 'adspin.inp'
            self.stdout = 'adspin.log'
            self.stderr = ExternalCode.STDOUT
            super(ADSPIN, self).execute()
        else:
            if not self.results_dir:
                self.raise_exception('run_adspin is False,'
                                     ' and no results_dir specified',
                                     RuntimeError)
            self.copy_results(self.results_dir, 'adspin.out')

        self.read_output()

    def write_input(self, filename='adspin.inp'):
        """ Writes ADSPIN input 'script'. """
        with self.dir_context:
            with open(filename, 'w') as out:
                out.write('%s\n' % self.casename)
                if os.path.exists(self.casename+'.restart.new'):
                    out.write('2\n')  # Use .restart.new
                out.write('adspin.out\n')
                for i, req in enumerate(self.requests):
                    out.write('%d\n' % req.block)

                    if req.imin == req.imax:
                        out.write('i\n')
                        out.write('n\n')  # Multiple surface averaging.
                        out.write('%d\n' % req.imin)
                        out.write('%d %d\n' % (req.jmin, req.jmax))
                        out.write('%d %d\n' % (req.kmin, req.kmax))
                    elif req.jmin == req.jmax:
                        out.write('j\n')
                        out.write('n\n')
                        out.write('%d\n' % req.jmin)
                        out.write('%d %d\n' % (req.imin, req.imax))
                        out.write('%d %d\n' % (req.kmin, req.kmax))
                    elif req.kmin == req.kmax:
                        out.write('k\n')
                        out.write('n\n')
                        out.write('%d\n' % req.kmin)
                        out.write('%d %d\n' % (req.imin, req.imax))
                        out.write('%d %d\n' % (req.jmin, req.jmax))
                    else:
                        self.raise_exception('Request %d not an I, J, or K'
                                             ' surface.' % i, ValueError)

                    out.write('2\n')  # Mass averaging.
                    out.write('n\n')  # Do not extend surface.
                    if i < len(self.requests)-1:
                        out.write('y\n')
                    else:
                        out.write('n\n')

    def read_output(self, filename='adspin.out'):
        """
        Reads ADSPIN output and populates :class:`Request` instances with
        results.
        """
        with self.dir_context:
            with open(filename, 'r') as inp:
                for i, req in enumerate(self.requests):
                    req.ptot, req.ttot, req.massflow = -1., -1., -1.

                    line = inp.readline()
                    while line:
                        if 'Total surface area' in line:
                            req.a = float(line.split()[-1])
                        elif 'Average total pressure' in line:
                            req.pt = float(line.split()[-1])
                        elif 'Average static pressure' in line:
                            req.ps = float(line.split()[-1])
                        elif 'Average total temperature' in line:
                            req.tt = float(line.split()[-1])
                        elif 'Average static temperature' in line:
                            req.ts = float(line.split()[-1])
                        elif 'Total flowrate through surface' in line:
                            req.w = float(line.split()[-1])
                        elif '________' in line:
                            break
                        line = inp.readline()

                    self._logger.debug('req %d: a %g, pt %g, ps %g, tt %g, ts %g, w %g',
                                       i, req.a, req.pt, req.ps, req.tt, req.ts, req.w)


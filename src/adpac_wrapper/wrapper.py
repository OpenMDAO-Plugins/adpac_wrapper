import os.path
import time

from openmdao.main.api import FileMetadata, set_as_top
from openmdao.main.resource import ResourceAllocationManager as RAM
from openmdao.lib.components.external_code import ExternalCode
from openmdao.lib.datatypes.api import Bool, Int, Float, Str
from openmdao.lib.datatypes.domain import surface_probe

from adpac_wrapper.boundata import Boundata
from adpac_wrapper.converge import Converge
from adpac_wrapper.input    import Input
from adpac_wrapper.property import Property
from adpac_wrapper.vis3d    import Vis3D, Plot3D, BladeRow
from adpac_wrapper          import restart

# Import boundary conditions so they're all registered.
from adpac_wrapper import bc, bcint1, bcintm, bcprm, bcprr, bdatin, \
                          endtta, exitg, fixed, free, inleta, inletg, \
                          inletm, inletr, inlett, kill, lamss, mbcavg, \
                          ssvi, system, vce


class ProbeRequest(object):
    """
    Describes a surface probe request.

    - `surfaces` is a list of ``(block, imin, imax, jmin, jmax, kmin, kmax)`` \
    mesh surface specifications to be used for the calculation. \
    Indices start at 1.
    - `variables` is a list of ``(attribute_name, metric_name, units)`` \
    tuples. Legal metric names are 'area', 'mass_flow', 'corrected_mass_flow', \
    'pressure', 'pressure_stagnation', 'temperature', and \
    'temperature_stagnation'.
    - `weighting_scheme` specifies how individual values are weighted. \
    Legal values are 'area' for area averaging and 'mass' for mass averaging.
    """

    def __init__(self, surfaces, variables, scheme):
        self.surfaces = surfaces
        self.variables = variables
        self.scheme = scheme


class ADPAC(ExternalCode):
    """
    File-based wrapper for ADPAC.
    Additional information regarding ADPAC may be found in the
    `ADPAC v1.0 User's Manual`.
    """

    update_restart = Bool(False, io_type='in',
                          desc='If True, <casename>.restart.old is updated'
                               ' with <casename>.restart.new')
    run_adpac = Bool(True, iotype='in',
                     desc='If True, ADPAC is run, otherwise precomputed result'
                          ' files are copied from `results_dir`.')
    parallel = Bool(False, io_type='in',
                    desc='If True, the parallel version of ADPAC is run.')
    serial_adpac = Str('adpac_linux', iotype='in',
                       desc='Path to serial ADPAC executable to run.')
    mpi_adpac = Str('adpac_linux_mpi', io_type='in',
                    desc='Path to MPI ADPAC executable to run.')
    mpi_procs = Int(0, io_type='in',
                    desc='Number of MPI processes to run (0 => #blocks).')
    stats = Bool(True, io_type='in',
                 desc='Collect parallel execution statistics.')
    mpi_path = Str('mpirun', io_type='in',
                   desc='Path to MPI executable to run.')
    results_dir = Str(iotype='in',
                      desc='Directory of precomputed results'
                           ' (for workflow debug).')

    # Command-line arguments.
    iasync = Bool(False, iotype='in',
                  desc='Use asynchronous patch exchanges.')
    ibalance = Bool(True, iotype='in',
                    desc='Use block size load balancer.')
    icheck = Bool(True, iotype='in',
                  desc='Call stopchk() at every bcapp().')
    idissf = Bool(True, iotype='in',
                  desc='Use inter-block dissipation.')
    irevs = Bool(False, iotype='in',
                 desc='Print forces for rotating blocks.')

    def __init__(self, casename=None, *args, **kwargs):
        super(ADPAC, self).__init__(*args, **kwargs)
        self.poll_delay = 1.  # Default is very short.
        self.surface_probes = []

        self.add('input', Input())
        self.add('boundata', Boundata())
        self.add('converge', Converge())

        if casename:
            self.input.casename = casename
            self.read_output(casename)

    def tree_rooted(self):
        """ If specified, read ``<casename>.input``. """
        super(ADPAC, self).tree_rooted()
        if self.input.casename:
            self.read_input(self.input.casename)

    def add_probe(self, request):
        """ Add a :class:`ProbeRequest` to be evaluated. """
        if not isinstance(request, ProbeRequest):
            self.raise_exception('Must be a ProbeRequest', TypeError)
        for attr, metric, units in request.variables:
            if not hasattr(self, attr):
                setattr(self, attr, Float(units=units, iotype='out',
                                          desc='Surface probe for ' + metric))
        self.surface_probes.append(request)

    def create_property(self, name, targets):
        """
        Create :class:`Property` that maps to one or more target variables.
        Scalar targets are specified by their (possibly nested) name.
        Array targets are specified by ``(name, index)``.
        """
        if isinstance(targets, basestring):
            targets = [targets]

        units = None
        iotype = None
        desc = None
        prop_targets = []
        for i, target in enumerate(targets):
            if isinstance(target, basestring):
                path = target
            elif isinstance(target, tuple):
                path = target[0]
            else:
                self.raise_exception('Invalid target[%d]: %r' % (i, target),
                                     ValueError)
            attrs = path.split('.')
            obj = self
            for attr in attrs[:-1]:
                obj = getattr(obj, attr)
            var = obj.trait(attrs[-1])
            if var is None:
                self.raise_exception('No such target[%d]: %r' % (i, target),
                                     ValueError)
            if i:
                if var.units != units:
                    self.raise_exception('Incompatible units at %d: %s vs. %s' \
                                         % (i, var.units, units), ValueError)
                if var.iotype != iotype:
                    self.raise_exception('Incompatible iotype at %d: %s vs. %s' \
                                         % (i, var.iotype, iotype), ValueError)
            else:
                units = var.units
                iotype = var.iotype
                desc = var.desc

            if isinstance(target, tuple):
                prop_targets.append((obj, attrs[-1], (target[1],)))
            else:
                prop_targets.append((obj, attrs[-1], None))

# TODO: make targets output-only?

        # Create property variable.
        self.add_trait(name, Property(targets=prop_targets, units=units,
                                      iotype=iotype, desc=desc))

    def copy_inputs(self, inputs_dir, casename=None, patterns=None):
        """
        Copy inputs from `inputs_dir` that match `patterns`.
        Also copies any files prefixed by ``<casename>``.
        This can be useful for resetting problem state.
        """
        casename = casename or self.input.casename
        patterns = patterns or []
        patterns.extend((casename+'.*',))
        super(ADPAC, self).copy_inputs(inputs_dir, patterns)

    def copy_results(self, results_dir, patterns=None):
        """
        Copy files from `results_dir` that match `patterns`.
        Also copies any files prefixed by ``<casename>``.
        This can be useful for workflow debugging.
        """
        patterns = patterns or []
        patterns.extend((self.input.casename+'.*', 'fort.42', 'fort.60'))
        super(ADPAC, self).copy_results(results_dir, patterns)

    def check_config(self):
        """ Check sanity of current configuration. """
        super(ADPAC, self).check_config()
        self.input.check_config()
        self.boundata.check_config()

    def execute(self):
        """
        Writes to ``<casename>.input`` and ``<casename>.boundata`` files.
        If `update_restart` is True and ``<casename>.restart.new`` exists,
        updates ``<casename>.restart.old`` with ``<casename>.restart.new``.
        Then removes existing output files.
        If `run_adpac` is True, executes ADPAC.
        Otherwise, copies precomputed results files from `results_dir`.
        """
        casename = self.input.casename

        if self.update_restart and \
           os.path.exists(casename+'.restart.new'):
            os.rename(casename+'.restart.new', casename+'.restart.old')
            self.input.frest = 1

        self.write_input(casename)

        # Remove output files.
        for ext in ('.converge', '.forces', '.log', '.output',
                    '.p3dabs', '.p3drel', '.restart.new'):
            if os.path.exists(casename+ext):
                os.remove(casename+ext)
        for name in ('fort.42', 'fort.60'):
            if os.path.exists(name):
                os.remove(name)
        self.converge.clear()

        if self.run_adpac:
            if self.parallel:
                self.run_parallel()
            else:
                self.run_serial()

            # Check for warnings.
            warnings = 0
            filenames = [casename+'.output']
            if self.parallel:
                filenames.append(casename+'.log')
            for fname in filenames:
                with open(fname) as inp:
                    for line in inp:
                        if 'WARNING in Checkout!' in line:
                            warnings += 1
            if warnings:
                self._logger.warning('%d warnings written by ADPAC to %s',
                                     warnings, filenames)
            # Check for errors.
            run_ok = False
            errors = 0
            with open(casename+'.output') as inp:
                for line in inp:
                    if 'ABORT in ERROR' in line or \
                       'ALERT!' in line:
                        errors += 1
                    elif 'execution normally terminated' in line:
                        run_ok = True
            if errors:
                self.raise_exception('%d errors reported by ADPAC' % errors,
                                     RuntimeError)
            if not run_ok:
                self.raise_exception('truncated ADPAC output', RuntimeError)

        else:
            if not self.results_dir:
                self.raise_exception('run_adpac is False,'
                                     ' and no results_dir specified',
                                     RuntimeError)

            if self.results_dir != 'skip-copy-results':
                self.copy_results(self.results_dir)

        self.read_output()
        self.evaluate_probe_requests()

    def run_serial(self):
        """
        Run serial version of ADPAC. Runs on remote host if there's more
        than just the local allocator.
        """
        try:
            allocator = RAM.get_allocator(1)
        except IndexError:
            self.resources = {}
        else:
            self.resources = {'n_cpus': 1}

        self.command = self.serial_adpac
        if not self.idissf:
            self.command += ' -d'
        if self.irevs:
            self.command += ' -r'

        self.stdin  = self.input.casename+'.input'
        self.stdout = self.input.casename+'.output'
        self.stderr = ExternalCode.STDOUT
        super(ADPAC, self).execute()

    def run_parallel(self):
        """
        Run parallel version of ADPAC. Gets hostnames from resource
        allocators and uses MPI for distribution.  Retries if code never
        started due to lack of InfiniPath contexts.
        """
        busy_hosts = []
        for retry in range(3):
            if retry:
                self._logger.info('retrying...')
            try:
                self._run_parallel(busy_hosts)
            except RuntimeError:
                with open(self.input.casename+'.log') as out:
                    for line in out.readlines():
                        msg = 'No free InfiniPath contexts available'
                        if msg in line:
                            self._logger.error(msg)
                            break
                    else:
                        raise
            else:
                return
        self.raise_exception('Too many retries.', RuntimeError)

    def _run_parallel(self, busy_hosts):
        """
        Run parallel version of ADPAC. Gets hostnames from resource
        allocators and uses MPI for distribution. `busy_hosts` is a list of
        hosts to exclude from consideration, and is updated with the hosts
        we attempt to use here.  This provides a mechanism to skip those hosts
        a previous attempt failed with.
        """
        if self.mpi_procs:
            n_cpus = self.mpi_procs
        else:
            n_cpus = len(self.input.nbld)
#TODO: get correct number of blocks (nbld isn't necessarily correct)

        hostnames = RAM.get_hostnames(dict(n_cpus=n_cpus, exclude=busy_hosts))
        if not hostnames:
            self.raise_exception('No hosts!', RuntimeError)
        busy_hosts.extend(hostnames)

        machinefile = 'machines'
        with open(machinefile, 'w') as out:
            for name in hostnames:
                out.write('%s\n' % name)

        self.command  = self.mpi_path
        self.command += ' -np %d' % n_cpus
        self.command += ' -machinefile %s' % machinefile

        if os.path.sep in self.mpi_adpac:
            self.command += ' %s' % self.mpi_adpac
        else:
            # Some mpirun commands want a real path.
            for prefix in os.environ['PATH'].split(os.path.pathsep):
                path = os.path.join(prefix, self.mpi_adpac)
                if os.path.exists(path):
                    self.command += ' %s' % path
                    break
            else:
                self.raise_exception("Can't find %r on PATH" % self.mpi_adpac,
                                     RuntimeError)
        if self.stats:
            self.command += ' -s all'
        self.command += ' -Z'

        if self.iasync:
            self.command += ' -a'
        if self.ibalance:
            self.command += ' -b'
        if not self.icheck:
            self.command += ' -c'
        if not self.idissf:
            self.command += ' -d'
        if self.irevs:
            self.command += ' -r'

        self.command += ' -i %s' % self.input.casename+'.input'
        self.command += ' -o %s' % self.input.casename+'.output'

        self.stdout = self.input.casename+'.log'
        self.stderr = ExternalCode.STDOUT
        self.resources = {}  # MPI will do distribution.
        super(ADPAC, self).execute()

        # On some systems (like GX with a shared filesystem between
        # front-end and compute nodes) it can take a bit before the
        # output files 'materialize'.
        for retry in range(30):
            if os.path.exists(self.input.casename+'.log') and \
               os.path.exists(self.input.casename+'.output'):
                break
            else:
                time.sleep(1)
        else:
            self.raise_exception('timeout waiting for output files',
                                 RuntimeError)

    def read_input(self, casename=None):
        """
        Read from ``<casename>.input`` and ``<casename>.boundata`` files.
        """
        casename = casename or self.input.casename
        self.external_files = []

        with self.dir_context:
            self.input.read(casename)
            self.boundata.read(casename, self.input)

            self.external_files.extend((
                FileMetadata(path='%s.input' % casename, input=True,
                             desc='General setup information.'),
                FileMetadata(path='%s.boundata' % casename, input=True,
                             desc='Boundary condition information.'),
                FileMetadata(path='%s.mesh' % casename, input=True,
                             binary=True, desc='Mesh information.'),
                FileMetadata(path='%s.restart.old' % casename, input=True,
                             binary=True, desc='Current flowfield.'),

                FileMetadata(path='%s.converge' % casename, output=True,
                             desc='Convergence data.'),
                FileMetadata(path='%s.forces' % casename, output=True,
                             desc='Resultant forces.'),
                FileMetadata(path='%s.output' % casename, output=True,
                             desc='Command output.'),
                FileMetadata(path='%s.log' % casename, output=True,
                             desc='Parallel execution log.'),

                FileMetadata(path='%s.p3dabs' % casename, output=True,
                             binary=True, desc='Plot3D absolute flowfield.'),
                FileMetadata(path='%s.p3drel' % casename, output=True,
                             binary=True, desc='Plot3D relative flowfield.'),
                FileMetadata(path='%s.restart.new' % casename, output=True,
                             binary=True, desc='Current flowfield.'),

                FileMetadata(path='fort.60', output=True,
                             desc=''),
            ))

    def write_input(self, casename=None):
        """
        Write to ``<casename>.input`` and ``<casename>.boundata`` files.
        """
        casename = casename or self.input.casename
        with self.dir_context:
            self.input.write(casename)
            self.boundata.write(casename, self.input)

    def read_output(self, casename=None):
        """ Read convergence output. """
        casename = casename or self.input.casename
        with self.dir_context:
            self.converge.clear()
            if os.path.exists(casename+'.converge'):
                self.converge.read(casename)

    def evaluate_probe_requests(self):
        """ Evaluates all surface probe requests. """
        domain = restart.read(self.input.casename, self._logger)
        for req in self.surface_probes:
            surfaces = []
            for block, imin, imax, jmin, jmax, kmin, kmax in req.surfaces:
                zone = 'zone_%d' % block
                imin = imin-1 if imin > 0 else imin  # Allow end-relative
                imax = imax-1 if imax > 0 else imax
                jmin = jmin-1 if jmin > 0 else jmin
                jmax = jmax-1 if jmax > 0 else jmax
                kmin = kmin-1 if kmin > 0 else kmin
                kmax = kmax-1 if kmax > 0 else kmax
                surfaces.append((zone, imin, imax, jmin, jmax, kmin, kmax))
            variables = []
            for attr, metric, units in req.variables:
                variables.append((metric, units))

            metrics = surface_probe(domain, surfaces, variables, req.scheme)
            for i, (attr, metric, units) in enumerate(req.variables):
                setattr(self, attr, metrics[i])

    def create_bladerow_vis3d(self, npassages=0, rows=None):
        """
        Creates 3D visualization model for bladerows.
        `npassages` sets the number of passages per row (via symmetry),
        if less than one, then the full wheel is displayed.
        `rows` is an optional specification of which rows to display
        (block numbers, starting at 1). Assumes an H-grid with SSVI boundaries.
        Returns the created :class:`Vis3D` object.
        Does not always produce a good result.
        """
        casename = self.input.casename
        nblades = self.input.nbld
        root = Vis3D(Plot3D(casename+'.mesh', casename+'.p3drel',
                            multiblock=True, dim=3, blanking=False,
                            binary=True, big_endian=True, unformatted=False))
        row = 0
        for i in range(len(nblades)):
            block = i + 1
            if nblades[i] <= 1:
                continue
            if rows and block not in rows:
                continue

            imax, jmax, kmax = -1, -1, -1

            # Find jmax (shroud) surface and get I range.
            for _bc in self.boundata._bcs:
                if _bc.type_name == 'SSVI' and _bc.lblock1 == block and \
                   _bc.lface1 == 'J' and _bc.ldir1 == 'M':
                    imin = _bc.m1lim1
                    imax = _bc.m1lim2
                    break
            else:
                msg = "Can't find shroud surface in block %d" % block
                self._logger.debug(msg)

            # Find jmin (hub) surface and get I range.
            for _bc in self.boundata._bcs:
                if _bc.type_name == 'SSVI' and _bc.lblock1 == block and \
                   _bc.lface1 == 'J' and _bc.ldir1 == 'P':
                    imin = _bc.m1lim1  # Not always 1 (i.e. spinner)
                    imax = _bc.m1lim2
                    break
            else:
                msg = "Can't find hub surface in block %d" % block
                self._logger.debug(msg)

            if imax < 1:
                continue  # No I range.

            # Find kmax (blade) surface to get leading and trailing edges.
            for _bc in self.boundata._bcs:
                if _bc.type_name == 'SSVI' and _bc.lblock1 == block and \
                   _bc.lface1 == 'K' and _bc.ldir1 == 'M':
                    ile  = _bc.m1lim1
                    ite  = _bc.m1lim2
                    jmin = _bc.n1lim1
                    jmax = _bc.n1lim2
                    kmax = _bc.l2lim
                    break
            else:
                msg = "Can't find blade surface in block %d" % block
                self._logger.debug(msg)
                continue

            # Now create full wheel for this blade row.
            row += 1
            obj = root.add('BladeRow_%d' % row,
                           BladeRow(block, imin, ile, ite, imax,
                                    jmin, jmax, kmax))
            obj.colorby_palette = 'Pres'
            if npassages != 1:
                obj.symmetry = 'rotational'
                obj.symmetry_axis = 'x'
                obj.symmetry_angle = 360. / nblades[i]
                if npassages < 1:
                    obj.symmetry_instances = nblades[i]
                else:
                    obj.symmetry_instances = npassages

        return root


def main():  # pragma no cover
    """
    Runs ADPAC for the given casename (which may be in a different directory).
    Since this will overwrite existing ``.input`` and ``.boundata`` files,
    they will be renamed to ``.input.<N>`` and ``.boundata.<N>``.

    Usage: ``python wrapper.py casename``
    """
    if len(sys.argv) > 1:
        path = sys.argv[1]
        directory = os.path.dirname(path)
        casename = os.path.basename(path)
        if directory:
            os.chdir(directory)
        adpac = ADPAC(casename=casename)
        set_as_top(adpac)

        # Move original inputs out of the way.
        i = 0
        while os.path.exists(casename+'.input.%d' % i):
            i += 1
        for ext in ('.input', '.boundata'):
            os.rename(casename+ext, casename+ext+'.%d' % i)

        adpac.run()
    else:
        print 'usage: python wrapper.py casename'


if __name__ == '__main__':  # pragma no cover
    main()


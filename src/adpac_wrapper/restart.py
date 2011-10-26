from openmdao.units.units import PhysicalQuantity
from openmdao.util.stream import Stream

from openmdao.lib.datatypes.domain import Vector, read_plot3d_grid

from adpac_wrapper.input import Input


def read(casename, logger, suffix='.restart.new'):
    """ Return domain read from ADPAC .input, .mesh, and .restart files. """
    # Read input.
    input = Input()
    input.read(casename)

    # Read mesh.
    domain = read_plot3d_grid(casename+'.mesh', big_endian=True,
                              unformatted=False, logger=logger)

    # Set global reference state.
    domain.reference_state = {
        'ideal_gas_constant': PhysicalQuantity(input.rgas, 'ft*lbf/(slug*degR)'),
        'length_reference': PhysicalQuantity(input.diam, 'ft'),
        'pressure_reference': PhysicalQuantity(input.pref, 'lbf/ft**2'),
        'specific_heat_ratio': PhysicalQuantity(input.gamma, 'unitless'),
        'temperature_reference': PhysicalQuantity(input.tref, 'degR'),
    }

    # Set zone handedness and symmetry.  Also make cylindrical if necessary.
    for i, zone in enumerate(domain.zones):
        zone.right_handed = False
        try:
            nbld = input.nbld[i]
        except IndexError:
            nbld = 1  # Default.
        if nbld > 1:
            zone.symmetry = 'rotational'
            zone.symmetry_axis = 'x'
            zone.symmetry_instances = input.nbld[i]
        try:
            fcarb = input.fcarb[i]
        except IndexError:
            fcarb = input.fcart  # Default
        else:
            if fcarb == -1:
                fcarb = input.fcart
        if not fcarb:
            zone.make_cylindrical(axis='x')

    # Read restart.
    restart = casename+suffix
    with open(restart, 'rb') as inp:
        logger.info('reading restart file %r', restart)
        stream = Stream(inp, binary=True, big_endian=True,
                        single_precision=True, integer_8=False,
                        unformatted=False, recordmark_8=False)

        # Read number of zones.
        nblocks = stream.read_int()
        if nblocks != len(domain.zones):
            raise RuntimeError('nblocks (%d) in %r != #Mesh zones (%d)'
                               % (nblocks, restart, len(domain.zones)))

        # Read zone dimensions.
        for zone in domain.zones:
            name = domain.zone_name(zone)
            imax, jmax, kmax = stream.read_ints(3)
            logger.debug('    %s: %dx%dx%d', name, imax, jmax, kmax)
            zone_i, zone_j, zone_k = zone.shape
            if imax != zone_i+1 or jmax != zone_j+1 or kmax != zone_k+1:
                raise RuntimeError('%s: Restart %dx%dx%d != Mesh %dx%dx%d' \
                                   % (name, imax, jmax, kmax,
                                      zone_i, zone_j, zone_k))
        # Read zone variables.
        for i, zone in enumerate(domain.zones):
            name = domain.zone_name(zone)
            zone_i, zone_j, zone_k = zone.shape
            shape = (zone_i+1, zone_j+1, zone_k+1)
            logger.debug('reading data for %s', name)

            zone.flow_solution.grid_location = 'CellCenter'
            zone.flow_solution.ghosts = [1, 1, 1, 1, 1, 1]

            name = 'density'
            arr = stream.read_floats(shape, order='Fortran')
            logger.debug('    %s min %g, max %g', name, arr.min(), arr.max())
            zone.flow_solution.add_array(name, arr)

            vec = Vector()
            if zone.coordinate_system == 'Cartesian':
                vec.x = stream.read_floats(shape, order='Fortran')
                logger.debug('    momentum.x min %g, max %g',
                             vec.x.min(), vec.x.max())
                vec.y = stream.read_floats(shape, order='Fortran')
                logger.debug('    momentum.y min %g, max %g',
                             vec.y.min(), vec.y.max())
                vec.z = stream.read_floats(shape, order='Fortran')
                logger.debug('    momentum.z min %g, max %g',
                             vec.z.min(), vec.z.max())
            else:
                vec.z = stream.read_floats(shape, order='Fortran')
                logger.debug('    momentum.z min %g, max %g',
                             vec.z.min(), vec.z.max())
                vec.r = stream.read_floats(shape, order='Fortran')
                logger.debug('    momentum.r min %g, max %g',
                             vec.r.min(), vec.r.max())
                vec.t = stream.read_floats(shape, order='Fortran')
                logger.debug('    momentum.t min %g, max %g',
                             vec.t.min(), vec.t.max())
            zone.flow_solution.add_vector('momentum', vec)

            name = 'energy_stagnation_density'
            arr = stream.read_floats(shape, order='Fortran')
            logger.debug('    %s min %g, max %g', name, arr.min(), arr.max())
            zone.flow_solution.add_array(name, arr)

            name = 'pressure'
            arr = stream.read_floats(shape, order='Fortran')
            logger.debug('    %s min %g, max %g', name, arr.min(), arr.max())
            zone.flow_solution.add_array(name, arr)

        # Read zone scalars.
        ncyc = stream.read_ints(len(domain.zones))
        dtheta = stream.read_floats(len(domain.zones))
        omegal = stream.read_floats(len(domain.zones))
        logger.debug('    ncyc %s', str(ncyc))
        logger.debug('    dtheta %s', str(dtheta))
        logger.debug('    omegal %s', str(omegal))
        for i, zone in enumerate(domain.zones):
            zone.flow_solution.ncyc = ncyc[i]
            zone.flow_solution.dtheta = dtheta[i]
            zone.flow_solution.omegal = omegal[i]

        # Implicit calculation data not supported.

    return domain


def write(domain, casename, logger, suffix='restart.new'):
    """
    Write domain as ADPAC .mesh and .restart files.

    NOTE: if any zones are cylindrical, their grid_coordinates are changed
          to cartesian and then back to cylindrical.  This will affect the
          coordinate values slightly.
    """

# FIXME: don't mess up mesh!
    # Write (cartesian) mesh.
    cylindricals = []
    for zone in domain.zones:
        if zone.coordinate_system == 'Cylindrical':
            logger.debug('Converting %s to cartesian coordinates',
                         domain.zone_name(zone))
            cylindricals.append(zone)
            zone.grid_coordinates.make_cartesian(axis='x')
    try:
        write_plot3d_grid(domain, casename+'.mesh', big_endian=True,
                          unformatted=False, logger=logger)
    finally:
        for zone in cylindricals:
            logger.debug('Converting %s back to cylindrical coordinates',
                         domain.zone_name(zone))
            zone.grid_coordinates.make_cylindrical(axis='x')

    # Write restart.
    restart = casename+suffix
    with open(restart, 'wb') as out:
        logger.info('writing restart file %r', restart)
        stream = Stream(out, binary=True, big_endian=True,
                        single_precision=True, integer_8=False,
                        unformatted=False, recordmark_8=False)

        # Write number of zones.
        stream.write_int(len(domain.zones))

        # Write zone dimensions.
        for zone in domain.zones:
            name = domain.zone_name(zone)
            imax, jmax, kmax = zone.shape
            logger.debug('    %s: %dx%dx%d', name, imax+1, jmax+1, kmax+1)
            stream.write_ints((imax+1, jmax+1, kmax+1))

        # Write zone variables.
        for zone in domain.zones:
            name = domain.zone_name(zone)
            logger.debug('writing data for %s', name)

            arr = zone.flow_solution.density
            logger.debug('    density min %g, max %g', arr.min(), arr.max())
            stream.write_floats(arr, order='Fortran')

            if zone.coordinate_system == 'Cartesian':
                arr = zone.flow_solution.momentum.x
                logger.debug('    momentum.x min %g, max %g',
                             arr.min(), arr.max())
                stream.write_floats(zone.flow_solution.momentum.x,
                                    order='Fortran')

                arr = zone.flow_solution.momentum.y
                logger.debug('    momentum.y min %g, max %g',
                             arr.min(), arr.max())
                stream.write_floats(zone.flow_solution.momentum.y,
                                    order='Fortran')

                arr = zone.flow_solution.momentum.z
                logger.debug('    momentum.z min %g, max %g',
                             arr.min(), arr.max())
                stream.write_floats(zone.flow_solution.momentum.z,
                                    order='Fortran')
            else:
                arr = zone.flow_solution.momentum.z
                logger.debug('    momentum.z min %g, max %g',
                             arr.min(), arr.max())
                stream.write_floats(zone.flow_solution.momentum.z,
                                    order='Fortran')

                arr = zone.flow_solution.momentum.r
                logger.debug('    momentum.r min %g, max %g',
                             arr.min(), arr.max())
                stream.write_floats(zone.flow_solution.momentum.r,
                                    order='Fortran')

                arr = zone.flow_solution.momentum.t
                logger.debug('    momentum.t min %g, max %g',
                             arr.min(), arr.max())
                stream.write_floats(zone.flow_solution.momentum.t,
                                    order='Fortran')

            arr = zone.flow_solution.energy_stagnation_density
            logger.debug('    energy_stagnation_density min %g, max %g',
                         arr.min(), arr.max())
            stream.write_floats(zone.flow_solution.energy_stagnation_density,
                                order='Fortran')

            arr = zone.flow_solution.pressure
            logger.debug('    pressure min %g, max %g', arr.min(), arr.max())
            stream.write_floats(zone.flow_solution.pressure, order='Fortran')

        # Write zone scalars.
        ncyc = []
        dtheta = []
        omegal = []
        for zone in domain.zones:
            ncyc.append(zone.flow_solution.ncyc)
            dtheta.append(zone.flow_solution.dtheta)
            omegal.append(zone.flow_solution.omegal)
        logger.debug('    ncyc %s', str(ncyc))
        logger.debug('    dtheta %s', str(dtheta))
        logger.debug('    omegal %s', str(omegal))
        stream.write_ints(ncyc)
        stream.write_floats(dtheta)
        stream.write_floats(omegal)

        # Implicit calculation data not supported.
        stream.write_int(0)


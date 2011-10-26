"""
Support for representing a 3D visualization of data via an external tool.
Currently only knows about Plot3D input files and MeshSurfaces, and the
only supported visualization tool is Ensight.
"""

import copy
import os.path
import platform

from openmdao.main.api import Container, Slot
from openmdao.lib.datatypes.api import Bool, Float, Int, List, Str
from openmdao.lib.datatypes.domain import read_plot3d_shape


class Vis3DObject(Container):
    """ Non-root object of 3D visualization model. """

    colorby_palette = Str()
    symmetry = Str()
    symmetry_axis = Str()
    symmetry_angle = Float(low=0, exclude_low=True, high=180)
    symmetry_instances = Int(1, low=1)
    visible = Bool(True)

    def __init__(self):
        super(Vis3DObject, self).__init__()
        self._vis_name = None

    @property
    def vis_name(self):
        """ Returns name in visualization hierarchy. """
        if not self._vis_name:
            name = self.get_pathname()
            parent = self.parent
            while parent and not isinstance(parent, Vis3D):
                parent = parent.parent
            if parent is None:
                return self.name
            else:
                pname = parent.get_pathname()
                if pname:
                    self._vis_name = name[len(pname)+1:]
                else:
                    self._vis_name = name
        return self._vis_name

    def clone(self, offset):
        """ Return a copy of ourselves, adjusting for block `offset`. """
        obj = copy.copy(self)  # Must be shallow!
        obj.parent = None
        obj._vis_name = None
        return obj

    def write_ensight(self, stream):
        """ Writes Ensight commands to `stream`. """
        if not self.visible:
            stream.write("""
# Make invisible.
part: select_byname_begin
 "%(name)s"
part: select_byname_end
part: modify_begin
part: visible OFF
part: modify_end
""" % {'name':self.vis_name})

        if self.symmetry == 'rotational':
            stream.write("""
# Rotational symmetry.
part: select_byname_begin
 "%(name)s"
part: select_byname_end
part: modify_begin
part: symmetry_type rotational
part: symmetry_axis %(axis)s
part: symmetry_angle %(angle)g
part: symmetry_rinstances %(instances)d
part: modify_end
""" % {'name':self.vis_name, 'axis':self.symmetry_axis,
       'angle':self.symmetry_angle, 'instances':self.symmetry_instances})

        if self.colorby_palette:
            stream.write("""
# Color palette.
part: select_byname_begin
 "%(name)s"
part: select_byname_end
part: modify_begin
part: colorby_palette %(palette)s
part: modify_end
""" % {'name':self.vis_name, 'palette':self.colorby_palette})


class Vis3DGroup(Vis3DObject):
    """ An object containing sub-objects. """

    def __init__(self):
        super(Vis3DGroup, self).__init__()
        self.objects = []

    def add(self, *args, **kwargs):
        """
        Remember :class:`Vis3DObject` instances added (and in what order).
        """
        obj = super(Vis3DGroup, self).add(*args, **kwargs)
        if isinstance(obj, Vis3DObject):
            self.objects.append(obj)
        return obj

    def clone(self, offset):
        """ Return a copy of ourselves, adjusting for block `offset`. """
        obj = Vis3DObject.clone(self, offset)
        obj.objects = []
        for child in self.objects:
            obj.add(child._name, child.clone(offset))
        return obj

    def write_ensight(self, stream):
        stream.write('\n# Group %s\n' % self.vis_name)
        for obj in self.objects:
            obj.write_ensight(stream)

        stream.write('\npart: select_byname_begin\n')
        for obj in self.objects:
            stream.write(' "%s"\n' % obj.vis_name)
        stream.write('part: select_byname_end\n')
        stream.write('part: group %s\n' % self.vis_name)

        # Groups have to have a specially formatted name.
        self._vis_name = 'GROUP: %s' % self.vis_name
        Vis3DObject.write_ensight(self, stream)


class Plot3D(Vis3DObject):
    """ Plot3D mesh and results to be visualized. """

    mesh_file = Str()
    results_file = Str()
    multiblock = Bool(True)
    dimension = Int(3, low=2, high=3)
    blanking = Bool(False)
    binary = Bool(True)
    big_endian = Bool(False)
    unformatted = Bool(True)

    def __init__(self, mesh_file, results_file, multiblock=True, dim=3,
                 blanking=False, binary=True, big_endian=False,
                 unformatted=True):
        super(Plot3D, self).__init__()
        self.mesh_file = mesh_file
        self.results_file = results_file
        self.multiblock = multiblock
        self.dimension = dim
        self.blanking = blanking
        self.binary = binary
        self.big_endian = big_endian
        self.unformatted = unformatted

    def write_ensight(self, stream):
        """ Writes Ensight commands to `stream`. """
        path = os.path.dirname(self.mesh_file) or '.'
        geometry = os.path.basename(self.mesh_file)
        result = os.path.basename(self.results_file)

        shape = read_plot3d_shape(self.mesh_file,
                                  multiblock=self.multiblock,
                                  dim=self.dimension,
                                  big_endian=self.big_endian,
                                  unformatted=self.unformatted)

        endian = 'big_endian' if self.big_endian else 'little_endian'
        iblank = 'ON' if self.blanking else 'OFF'
        multi_zone = 'ON' if self.multiblock else 'OFF'
        if self.binary:
            read_as = 'fortran_binary' if self.unformatted else 'c_binary'
        else:
            read_as = 'ascii'
        dim = '%dd' % self.dimension

        imax, jmax, kmax = 0, 0, 0
        for dims in shape:
            imax = max(imax, dims[0])
            jmax = max(jmax, dims[1])
            if self.dimension > 2:
                kmax = max(kmax, dims[2])

        stream.write("""
# Plot3D %(name)s
data: binary_files_are %(endian)s
data: format plot3d
data: path %(path)s
data: geometry %(geometry)s
data: result %(result)s
data: shift_time 1. 0. 0.
data: plot3diblank %(iblank)s
data: plot3dmulti_zone %(multi_zone)s
data: plot3dread_as %(read_as)s
data: plot3ddimension %(dim)s
data: read
data_partbuild: begin
part: select_default
part: modify_begin
part: elt_representation 3D_feature_2D_full
part: modify_end
data_partbuild: data_type structured
data_partbuild: group OFF
data_partbuild: select_all
data_partbuild: domain all
data_partbuild: noderange_i 1 %(imax)d
data_partbuild: noderange_j 1 %(jmax)d
data_partbuild: noderange_k 1 %(kmax)d
data_partbuild: nodestep 1 1 1
data_partbuild: nodedelta 0 0 0
data_partbuild: description
data_partbuild: create
data_partbuild: end
part: select_default
part: modify_begin
part: elt_representation 3D_border_2D_full
part: modify_end
""" % {'name':self.vis_name, 'path':path, 'geometry':geometry, 'result':result,
       'iblank':iblank, 'multi_zone':multi_zone, 'read_as':read_as, 'dim':dim,
       'endian':endian, 'imax':imax, 'jmax':jmax, 'kmax':kmax})

        if not self.visible:
            stream.write("""
part: select_all
part: modify_begin
part: visible OFF
part: modify_end
""")


class MeshSurface(Vis3DObject):
    """ I, J, or K surface of mesh. """

    block = Int(low=1)
    plane = Str()
    value = Int(low=1)
    min2 = Int(low=1)
    max2 = Int(low=1)
    min3 = Int(low=1)
    max3 = Int(low=1)

    def __init__(self, block, plane, value, min2, max2, min3, max3):
        super(MeshSurface, self).__init__()
        self.block = block
        self.plane = plane
        self.value = value
        self.min2 = min2
        self.max2 = max2
        self.min3 = min3
        self.max3 = max3

    def clone(self, offset):
        """ Return a copy of ourselves, adjusting for block `offset`. """
        obj = Vis3DObject.clone(self, offset)
        obj.block += offset
        return obj

    def write_ensight(self, stream):
        """ Writes Ensight commands to `stream`. """
        stream.write("""
# MeshSurface %(name)s
clip: select_default
part: modify_begin
clip: tool ijk
part: modify_end
clip: select_default
part: modify_begin
clip: mesh_plane %(plane)s
clip: tool ijk
part: modify_end
part: select_begin
 %(block)d
part: select_end
clip: begin
clip: value %(value)d
clip: domain intersect
clip: tool ijk
clip: dimension2 %(min2)d %(max2)d
clip: dimension3 %(min3)d %(max3)d
clip: end
clip: create
part: select_lastcreatedpart
part: modify_begin
part: description %(name)s
part: modify_end
""" % {'block':self.block, 'plane':self.plane, 'value':self.value,
       'min2':self.min2, 'max2':self.max2, 'min3':self.min3, 'max3':self.max3,
       'name':self.vis_name})

        super(MeshSurface, self).write_ensight(stream)


class BladeRow(Vis3DGroup):
    """
    Represents a blade row as a group of two blade surfaces and a
    disk surface.
    """

    def __init__(self, block, imin, ile, ite, imax, jmin, jmax, kmax):
        super(BladeRow, self).__init__()
        self.add('disk', MeshSurface(block, 'J', jmin, imin, imax, 1, kmax))
        self.add('side_1', MeshSurface(block, 'K', 1, ile, ite, jmin, jmax))
        self.add('side_2', MeshSurface(block, 'K', kmax, ile, ite, jmin, jmax))


class Vis3DCollection(Container):
    """ A named collection of objects. """

    objects = List(Container)  # Prefer (Vis3DCollection, Vis3DObject)

    def add(self, *args, **kwargs):
        """
        Remember :class:`Vis3DCollection` and :class:`Vis3DObject` instances
        added (and in what order).
        """
        obj = super(Vis3DCollection, self).add(*args, **kwargs)
        if isinstance(obj, (Vis3DCollection, Vis3DObject)):
            self.objects.append(obj)
        return obj

    def add_vis3d(self, name, other, offset):
        """
        Copy :class:`Vis3DCollection` `other` to this one as `name`.
        `offset` is used to determine updated zone numbers.
        """
        collection = self.add(name, Vis3DCollection())
        for obj in other.objects:
            collection.add(obj.name, obj.clone(offset))

    def write_ensight(self, stream):
        """ Writes Ensight commands to `stream`. """
        for obj in self.objects:
            obj.write_ensight(stream)


class Vis3D(Vis3DCollection):
    """ Root object to 3D visualization model. """

    data_obj = Slot(Plot3D)

    x_angle = Float(0., units='deg', iotype='in', desc='Rotation about X.')
    y_angle = Float(0., units='deg', iotype='in', desc='Rotation about Y.')
    z_angle = Float(0., units='deg', iotype='in', desc='Rotation about Z.')

    def __init__(self, data_obj):
        super(Vis3D, self).__init__()
        self.data_obj = data_obj

    def write_ensight(self, filename):
        """ Write Ensight commands to `filename`. """
        with open(filename, 'w') as stream:
            stream.write('VERSION 8.21\n')
            self.data_obj.write_ensight(stream)
            stream.write("""
# Shading & variables.
view: hidden_surface ON
varextcfd: show_extended ON
variables: activate Pres
""")
            super(Vis3D, self).write_ensight(stream)

            if self.x_angle or self.y_angle or self.z_angle:
                stream.write("""
# Rotate.
view_transf: rotate %g %g %g
""" % (self.x_angle, self.y_angle, self.z_angle))

            stream.write("""
# Fit to viewport.
view_transf: fit 0
""")


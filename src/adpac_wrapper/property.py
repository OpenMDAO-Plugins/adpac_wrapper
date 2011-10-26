import weakref

from enthought.traits.api import TraitType
from enthought.traits.trait_handlers import NoDefaultSpecified

from openmdao.main.api import convert_units
from openmdao.main.attrwrapper import AttrWrapper


class Property(TraitType):
    """
    A Trait that maps to one or more target traits.
    `targets` is a list tuples of the form:
    ``(parent_obj, target_name, array_index)``.
    """

    def __init__(self, targets, **metadata):
        self._targets = []
        for obj, attr, indices in targets:
            self._targets.append((weakref.ref(obj), attr, indices))
        super(Property, self).__init__(NoDefaultSpecified, **metadata)

    def __getstate__(self):
        """ Resolve weak references. """
        state = self.__dict__.copy()
        resolved = []
        for wref, attr, indices in self._targets:
            resolved.append(wref(), attr, indices)
        state['_targets'] = resolved
        return state

    def __setstate__(self, state):
        """ Convert targets to weak references. """
        self.__dict__.update(state)
        self._targets = []
        for obj, attr, indices in resolved:
            self._targets.append((weakref.ref(obj), attr, indices))

    def get(self, obj, name):
        """ Return first target's value. """
        wref, attr, indices = self._targets[0]
        val = getattr(wref(), attr)
        if indices:
            for index in indices:
                val = val[index]
        return val

    def set(self, obj, name, value):
        """ Set all target values. """
        for wref, attr, indices in self._targets:
            if indices:
                obj = getattr(wref(), attr)
                for index in indices[:-1]:
                    obj = object[index]
                if isinstance(value, AttrWrapper):
                    src_units = value.metadata['units']
                    dst_units = obj.trait(name).units
                    if dst_units and src_units and src_units != dst_units:
                        obj[indices[-1]] = \
                            convert_units(value.value, src_units, dst_units)
                    else:
                        obj[indices[-1]] = value.value
                else:
                    obj[indices[-1]] = value
            else:
                setattr(wref(), attr, value)


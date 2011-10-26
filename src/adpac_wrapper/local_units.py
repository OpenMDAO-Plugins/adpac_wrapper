import openmdao.units as units

def add_units():
    """ Add units we need if not already defined. """

    required = (
        ('lbf',  '4.4482216152605*N', 'Pounds force'),
        ('lbm',  '1.*lb',             'Pounds mass'),
        ('rpm',  '6.*deg/s',          'Revolutions per minute.'),
        ('slug', '14.5939*kg',        'Slug'),
    )
    for name, unit, comment in required:
        try:
            units.PhysicalQuantity(0., name)
        except ValueError:
            units.add_unit(name, unit, comment)


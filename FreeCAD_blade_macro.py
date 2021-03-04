from FreeCAD import Base
import Part, PartGui, Sketcher

import os
import numpy as np
import pandas as pd

DIR = '/home/nicola/Documents/code/turbine_designer_new'

HOLLOW = False
THICKNESS = 0.005
SKIP_INNER_PROFILES = 2  # Number of profiles to skip on the inside

def lerp(a, b, f):
    return a*(1-f) + b*f

# Return a sketch with a bezier curve from a set of points
def create_bezier_sketch(points, z):
    sketch = App.activeDocument().addObject(
            'Sketcher::SketchObject', 'Section')
    sketch.Placement = App.Placement(
            App.Vector(0, 0, z), App.Rotation(0, 0, 0, 1))
    sketch.MapMode = "Deactivated"
    coords = [App.Vector(x, y, z) for x, y in points]
    sketch.addGeometry(Part.BSplineCurve(coords))

    sketch.addGeometry(Part.LineSegment(coords[0], coords[-1]))

    # sketch.addConstraint(Sketcher.Constraint('Coincident', 1, 1, 0, 2))
    # sketch.addConstraint(Sketcher.Constraint('Coincident', 1, 2, 0, 1))

    return sketch

def get_foil_shape(name):
    center_offset = 0.3
    df = pd.read_csv(os.path.join(DIR, 'foil_data', name, 'shape.csv'))
    points = [(row['x'] - center_offset, -row['y']) for _, row in df.iterrows()]
    return points

def interp_foil_shapes(shape_1, shape_2, f):
    return [(lerp(x1, x2, f), lerp(y1, y2, f))
            for (x1, y1), (x2, y2) in zip(shape_1, shape_2)]

def scale_and_rotate_foil_shape(shape, s, r):
    shape = [(x * s, y * s) for (x, y) in shape]  # Scale
    # a = math.radians( -ts[n] + 90 )
    shape = [(x * np.cos(r) - y * np.sin(r),
             x * np.sin(r) + y * np.cos(r)) for (x, y) in shape]
    return shape

# def shrunken_foil_shape(shape, t):
    # new_shape = []
    # for i in range(len(shape)):
        # p = shape[i]
        # l = np.sqrt(p[0]**2 + p[1]**2)
        # n = (p[0]/l, p[1]/l)
        # new_shape.append((p[0] - n[0]*t, p[1] - n[1]*t))
    # return new_shape
def shrunken_foil_shape(shape, t):
    prevs = [shape[-1]] + shape[:-1]
    nexts = shape[1:] + [shape[0]]

    new_shape = []
    for i in range(0, len(shape), 1):
        d1 = (shape[i][0] - prevs[i][0], shape[i][1] - prevs[i][1])
        l1 = np.sqrt(d1[0]**2 + d1[1]**2)
        n1 = (d1[1]/l1, -d1[0]/l1)
        d2 = (nexts[i][0] - shape[i][0], nexts[i][1] - shape[i][1])
        l2 = np.sqrt(d2[0]**2 + d2[1]**2)
        n2 = (d2[1]/l2, -d2[0]/l2)
        n = ((n1[0]+n2[0])/2, (n1[1]+n2[1])/2)
        if l1 > 0.002 and l2 > 0.002:
            new_shape.append((shape[i][0] + n[0]*t, shape[i][1] + n[1]*t))

    # while True:
        # if new_shape[0][1] > new_shape[-1][1]:
            # new_shape = new_shape[:-1]
        # else:
            # break

    return new_shape
# def shrunken_foil_shape(shape, t):
    # prevs = [shape[-1]] + shape[:-1]
    # nexts = shape[1:] + [shape[0]]

    # new_shape = []
    # for i in range(len(shape)):
        # d = (nexts[i][0] - prevs[i][0], nexts[i][1] - prevs[i][1])
        # l = np.sqrt(d[0]**2 + d[1]**2)
        # n = (d[1]/l, -d[0]/l)
        # new_shape.append((shape[i][0] - n[0]*t, shape[i][1] - n[1]*t))
    # return new_shape

### Load blade parameters

df = pd.read_csv(os.path.join(DIR, 'blade_design.csv'))
rs = df['radius']
cs = df['chord_length']
ts = df['angle_of_twist_rad']
foils = df['airfoils']
fs = df['interp_factor']

### Load airfoil shapes

FOIL_NAMES = []
for foil in foils:
    names = foil.split(',')
    for name in names:
        if name not in FOIL_NAMES:
            FOIL_NAMES.append(name)

foil_shapes = {name: get_foil_shape(name) for name in FOIL_NAMES}

### Generate blade
doc = App.newDocument()

loft = doc.addObject("Part::Loft", "Blade")

sections = []
shrunk_sections = []
for n in range(len(rs)):
    foil_names = foils[n].split(',')
    if len(foil_names) == 1:
        # No interpolation needed
        foil_shape = foil_shapes[foil_names[0]]
    else:
        # Interpolated foil shape
        foil_shape = interp_foil_shapes(
                foil_shapes[foil_names[0]],
                foil_shapes[foil_names[1]],
                np.mod(fs[n], 1))
    section_shape = scale_and_rotate_foil_shape(foil_shape, cs[n], ts[n])

    section = create_bezier_sketch(section_shape, rs[n])
    sections.append(section)

    # Also create a shrunk section:
    if HOLLOW and n < len(rs) - SKIP_INNER_PROFILES:
        # We rotate separately because shrinking depends on real y-axis
        shrunk_shape = scale_and_rotate_foil_shape(foil_shape, cs[n], 0)
        # Perform shrinkage in many steps for better stability
        for i in range(100):
            shrunk_shape = shrunken_foil_shape(shrunk_shape, THICKNESS/100)
        shrunk_shape = scale_and_rotate_foil_shape(shrunk_shape, 1, ts[n])
        shrunk_section = create_bezier_sketch(shrunk_shape, rs[n])
        shrunk_sections.append(shrunk_section)

if HOLLOW:
    sections = shrunk_sections[::-1] + sections

loft.Sections = sections
loft.Solid = True
loft.Ruled = True

doc.recompute()

from build123d import *
import numpy as np
from typing import Optional


def _lerp(a: np.array, b: np.array, f: float):
    return a*(1-f) + b*f


def _vec2_rotate(vec_array: np.array, angle: float):
    """
    Rotate each of an array of 2D vectors by a fixed angle
    """
    x, y = vec_array[:, 0].copy(), vec_array[:, 1].copy()
    vec_array[:, 0] = (
            x * np.cos(angle) -
            y * np.sin(angle)
    )
    vec_array[:, 1] = (
            x * np.sin(angle) +
            y * np.cos(angle)
    )
    return vec_array


def _shrink_polygon(shape: np.array, shrink: float):
    """
    Shrinks a polygon (defined as an array list of 2D points)
    Seems more robust than build123d's offset function
    """
    # Set origin to center; will undo at the end
    centroid = np.sum(shape, axis=0) / len(shape)
    shape = shape - centroid

    # Vector from previous to next point
    tangent = (
        np.concatenate([shape[1:], shape[:1]]) -
        np.concatenate([shape[-1:], shape[:-1]])
    )
    # Normalize it
    tangent = tangent / np.linalg.norm(tangent, axis=1)[:, np.newaxis]
    # Rotate it by 90deg to get inwards normal
    normal = _vec2_rotate(tangent, -np.pi/2)

    # Offset point towards normal to shrink section
    shape += normal * shrink

    """
    To prevent non-manifold face after shrinkage, remove any points
    that would prevent a monotonically increasing angle.
    
    Stage 1:
    To keep it symmetrical, start by removing first and last points
    until the angle between them is in correct direction.
    
    Stage 2:
    Remove any remaining bad points.
    """

    # Stage 1
    while True:
        first = shape[0]
        last = shape[-1]
        angle = (
            np.arctan2(first[1], first[0]) -
            np.arctan2(last[1], last[0])
        )
        if angle > 0:
            # Start and end points overlap; remove them
            shape = shape[1:-1]
            continue
        break

    # Stage 2
    i = 1
    while i < len(shape):
        last_vec = shape[i - 1]
        vec = shape[i]
        angle = (
            np.arctan2(vec[1], vec[0]) -
            np.arctan2(last_vec[1], last_vec[0])
        )
        if angle > 0:
            # Point is not monotonic; delete it
            shape = np.delete(shape, i, axis=0)
            continue
        i += 1

    # Restore origin
    shape = shape + centroid
    return shape


def _solid_blade_profile(
        blade: 'Blade',
        shrink: float = 0.0,
        min_chord: Optional[float] = None
) -> Part:
    with BuildPart() as build_part:
        # Create main shape by lofting the slice profiles
        for i, row in blade.slices.iterrows():
            if min_chord is not None and row.chord < min_chord:
                # Section would be too small; stop here
                break
            # Get interpolated airfoil shape
            shape = _lerp(
                blade.airfoil_shapes[row.airfoil_1],
                blade.airfoil_shapes[row.airfoil_2],
                row.airfoil_factor
            )
            # Scale it
            shape *= row.chord
            # Rotate it
            shape = _vec2_rotate(shape, row.twist)
            # Shrink it
            if shrink > 0:
                shape = _shrink_polygon(shape, shrink)
                if len(shape) < 3:
                    # Shrinking has fully collapsed shape; stop here
                    break

            with BuildSketch(Plane.XY.offset(
                # Last section is also 'shrunk' along z
                row.radius - shrink if(i == blade.num_slices - 1)
                else row.radius
            )):
                with BuildLine():
                    Spline(
                        *[(x, y) for x, y in shape]
                    )
                    Line(tuple(shape[0]), tuple(shape[-1]))
                make_face()

        loft()
        first_section = build_part.faces().group_by(Axis.Z)[0][0]

        # Add the stem
        with BuildSketch(Plane.XY.offset(blade.stem.start - shrink)):
            Circle(blade.stem.diameter / 2 - shrink)
        extrude(amount=blade.stem.length + shrink)
        stem_face = build_part.faces(Select.LAST).group_by(Axis.Z)[-1][0]
        loft([stem_face, first_section], ruled=True)

    return build_part.part


def build_blade_shape(
        blade: 'Blade',
        hollow_thickness: Optional[float],
        hollow_min_chord: Optional[float]
) -> Part:
    outer = _solid_blade_profile(blade)
    if hollow_thickness is not None:
        inner = _solid_blade_profile(
            blade,
            hollow_thickness,
            hollow_min_chord
        )
        return outer - inner
    else:
        return outer

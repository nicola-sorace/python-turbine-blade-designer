from build123d import *
import numpy as np


def _lerp(a: np.array, b: np.array, f: float):
    return a*(1-f) + b*f


def build_blade_shape(blade: 'Blade') -> Part:
    with BuildPart() as build_part:
        for i, row in blade.slices.iterrows():
            # Get interpolated airfoil shape
            shape = _lerp(
                blade.airfoil_shapes[row.airfoil_1],
                blade.airfoil_shapes[row.airfoil_2],
                row.airfoil_factor
            )
            # Scale it
            shape *= row.chord
            # Rotate it
            #TODO what's wrong here?
            x, y = shape[:, 0].copy(), shape[:, 1].copy()
            shape[:, 0] = (
                x * np.cos(row.twist) -
                y * np.sin(row.twist)
            )
            shape[:, 1] = (
                x * np.sin(row.twist) +
                y * np.cos(row.twist)
            )

            with BuildSketch(Plane.XY.offset(row.radius)):
                with BuildLine():
                    Polyline(
                        *[(x, y) for x, y in shape],
                        close=True
                    )
                make_face()
        loft(ruled=True)

    return build_part.part

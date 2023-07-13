import numpy as np
import pandas as pd


def _midpoints(df: pd.DataFrame, column: str):
    xs = df[column].to_numpy()
    return (xs[1:] + xs[:-1]) / 2


def estimate_blade_forces(
        blade: 'Blade',
        environment: 'Environment'
) -> pd.DataFrame:
    # Width of each slice
    rs = blade.slices.radius.to_numpy()
    drs = rs[1:] - rs[:-1]

    # Get values at midpoints
    rs = _midpoints(blade.slices, 'radius')
    solidities = _midpoints(blade.slices, 'solidity')
    lifts = _midpoints(blade.slices, 'lift_coefficient')
    drags = _midpoints(blade.slices, 'drag_coefficient')
    twists = _midpoints(blade.slices, 'twist')
    chords = _midpoints(blade.slices, 'chord')
    inds_a = _midpoints(blade.slices, 'axial_induction')
    inds_r = _midpoints(blade.slices, 'radial_induction')

    axial_forces = (
        solidities * np.pi * environment.fluid_density *
        (environment.free_stream_velocity**2 * (1-inds_a)**2) /
        (np.cos(twists)**2) *
        (lifts * np.sin(twists) + drags * np.cos(twists)) *
        rs * drs
    )

    radial_forces = (
        solidities * np.pi * environment.fluid_density *
        (environment.free_stream_velocity**2 * (1-inds_a)**2) /
        (np.cos(twists)**2) *
        (lifts * np.cos(twists) - drags * np.sin(twists)) *
        rs * drs
    )

    drag_force = np.sum(axial_forces)
    turning_torque = np.sum(radial_forces * rs)
    bending_torque = np.sum(axial_forces * rs)

    print(f"Total drag force: {drag_force}")
    print(f"Total turning torque: {turning_torque}")
    print(f"Total bending torque: {bending_torque}")

    return pd.DataFrame({
        'radius': rs,
        'axial_force': axial_forces,
        'radial_force': radial_forces,
    })

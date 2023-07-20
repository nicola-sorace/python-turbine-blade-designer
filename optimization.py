"""
Turbine blade optimization using the Blade Element Momentum equations
Based on:
https://glingram.webspace.durham.ac.uk/wp-content/uploads/sites/104/2021/04/wind_turbine_design.pdf
"""

import numpy as np
import pandas as pd
import warnings

ITERATION_LIMIT = 1000
ERROR_TOLERANCE = 1e-15


def _lerp(a, b, f):
    """
    Linear interpolation between `a` and `b`
    """
    return a * (1-f) + b * f


def _interpolate_to_slices(
        section_vals: np.array,
        ids: np.array
) -> np.array:
    """
    Lookup values in `section_vals` by indices in `ids`.
    However, indices are expressed as floats.
    The two closest indices are linearly interpolated.
    """
    return [
        _lerp(
            section_vals[int(np.floor(i))],
            section_vals[int(np.ceil(i))],
            np.mod(i, 1)
        )
        for i in ids
    ]


def _chord_lengths(
        twists: np.array,
        rs: np.array,
        local_tip_speed_ratio: np.array,
        blade_count: int
):
    return (
        (8 * np.pi * rs * np.cos(twists)) /
        (3 * blade_count * local_tip_speed_ratio)
    )


def _local_solidities(
        chords: np.array,
        rs: np.array,
        blade_count: float
):
    return (blade_count * chords) / (2 * np.pi * rs)


def optimize_blade(
        blade: 'Blade',
        environment: 'Environment',
        target_power: float,
        expected_efficiency: float,
        tip_speed_ratio: float,
        blade_count: int
) -> pd.DataFrame:
    # Calculate the approximate blade length to meet targets
    final_r = np.sqrt(
        (2*target_power) / (
            expected_efficiency *
            environment.fluid_density *
            np.pi * environment.free_stream_velocity**3
        )
    )
    print(f" - Blade radius: {final_r:.2f}m")
    # Calculate resulting properties
    angular_velocity = (tip_speed_ratio * environment.free_stream_velocity / final_r)
    rpm = 60 * angular_velocity / (2 * np.pi)
    torque = target_power / angular_velocity
    print(f" - Blade should spin at {rpm:.0f}RPM, with a generator torque of {torque:.2f}Nm")

    # Split blade into slices of equal length
    rs = np.linspace(blade.sections[0].start_r, final_r, blade.num_slices)
    # Ensure start/end locations are exact
    forced_lengths = []
    for section in blade.sections:
        if section.start_r is not None:
            forced_lengths.append(section.start_r)
        if section.end_r is not None:
            forced_lengths.append(section.end_r)
    for r in forced_lengths:
        i = np.argmin(np.abs(rs - r))
        rs[i] = r

    # Generate a list of interpolated section indices for each slice
    # (for example, a slice midway between section 1 and 2 is 1.5)
    ids = []
    i = 0
    for sec, section in enumerate(blade.sections):
        if sec != 0:
            last_section = blade.sections[sec - 1]
            last_r = (
                last_section.start_r
                if last_section.end_r is None
                else last_section.end_r
            )

        while i < blade.num_slices and rs[i] < section.start_r:
            # Section hasn't started yet
            if sec == 0:
                # Blade has not started yet; just repeat first id
                ids.append(sec)
            else:
                # Interpolate from last
                ids.append(sec-1 + (rs[i] - last_r) / (section.start_r - last_r))
            i += 1

        fixed_section = False
        if section.end_r is not None:
            fixed_section = True
            end_r = section.end_r
        elif sec < len(blade.sections) - 1:
            end_r = blade.sections[sec + 1].start_r
            if end_r is None:
                end_r = final_r
        else:
            fixed_section = True
            end_r = np.inf

        while i < blade.num_slices and rs[i] <= end_r:
            # Section hasn't ended yet
            if fixed_section:
                # No interpolation; repeat this id until end
                ids.append(sec)
            else:
                # Interpolate to next
                ids.append(sec + (rs[i] - section.start_r) / (end_r - section.start_r))
            i += 1

    # Correction to avoid NaNs
    rs[-1] *= 0.995

    # Calculate lift/drag coefficients at each section
    lift_coefficients = [
        np.interp(
            [section.angle_deg],
            section.airfoil_stats.index,
            section.airfoil_stats['Cl']
        )[0]
        for section in blade.sections
    ]
    drag_coefficients = [
        np.interp(
            [section.angle_deg],
            section.airfoil_stats.index,
            section.airfoil_stats['Cd']
        )[0]
        for section in blade.sections
    ]
    # Interpolate them to each slice
    lift_coefficients = _interpolate_to_slices(lift_coefficients, ids)
    drag_coefficients = _interpolate_to_slices(drag_coefficients, ids)

    # Calculate "local" tip speed ratios, i.e. relative tangential velocities
    local_tip_speed_ratios = angular_velocity * rs / environment.free_stream_velocity

    # Setup arrays with initial conditions
    twists = np.pi/2 - 2/3 * np.arctan(1 / local_tip_speed_ratios)
    chords = _chord_lengths(twists, rs, local_tip_speed_ratios, blade_count)
    solidities = _local_solidities(chords, rs, blade_count)
    axial_inductions = (
        1 +
        (4 * np.cos(twists)**2) /
        (solidities * lift_coefficients * np.sin(twists))
    ) ** -1
    radial_inductions = (1 - 3 * axial_inductions) / (4 * axial_inductions - 1)
    rel_rs = rs / final_r

    # Iterate to find optimal solution
    for i in range(ITERATION_LIMIT):
        last_axial_inductions = axial_inductions.copy()
        last_radial_inductions = radial_inductions.copy()

        twists = np.arctan(
            local_tip_speed_ratios *
            (1 + radial_inductions) /
            (1 - axial_inductions)
        )
        chords = _chord_lengths(twists, rs, local_tip_speed_ratios, blade_count)
        solidities = _local_solidities(chords, rs, blade_count)
        frac = -blade_count/2 * (1 - rel_rs) / (rel_rs * np.cos(twists))
        tip_loss_correction = 2/np.pi * np.arccos(np.exp(frac))

        frac = (
            solidities *
            (lift_coefficients * np.sin(twists) + drag_coefficients * np.cos(twists)) /
            (4 * tip_loss_correction * np.cos(twists)**2)
        )
        axial_inductions = frac / (1 + frac)

        frac = (
            solidities *
            (lift_coefficients * np.cos(twists) - drag_coefficients * np.sin(twists)) /
            (4 * tip_loss_correction * np.cos(twists)**2)
        )
        radial_inductions = frac * (1 - axial_inductions)

        axial_error = np.max(np.abs(axial_inductions - last_axial_inductions))
        radial_error = np.max(np.abs(radial_inductions - last_radial_inductions))

        if max(axial_error, radial_error) < ERROR_TOLERANCE:
            break
        elif i == ITERATION_LIMIT - 1:
            warnings.warn(f"Failed to converge after {ITERATION_LIMIT} iterations")

    return pd.DataFrame(
        {
            'radius': rs,
            'airfoil_1': [
                blade.sections[int(np.floor(i))].airfoil_name
                for i in ids
            ],
            'airfoil_2': [
                blade.sections[int(np.ceil(i))].airfoil_name
                for i in ids
            ],
            'airfoil_factor': [i % 1.0 for i in ids],
            'twist': twists,
            'chord': chords,
            'solidity': solidities,
            'lift_coefficient': lift_coefficients,
            'drag_coefficient': drag_coefficients,
            'axial_induction': axial_inductions,
            'radial_induction': radial_inductions
        }
    )

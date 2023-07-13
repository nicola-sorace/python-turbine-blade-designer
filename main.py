"""
Note the confusing distinction between "section" and "slice":
- Blade design is bounded by user-defined values at arbitrary points along the
  blade; these points are called "sections"
- The blade is discretized into thin "slices" for numerical computation
"""

import os
import yaml
from Blade import Blade, Environment

output_dir = "output"

if __name__ == '__main__':
    with open("config.yaml") as f:
        config = yaml.safe_load(f.read())

    blade = Blade(
        sections=[
            {
                'start_r': section.get('start_r'),
                'end_r': section.get('end_r'),
                'airfoil_name': section['airfoil'],
                'angle_deg': section['angle_of_attack'],
                'forced_chord': section.get('forced_chord'),
                'single_slice': section.get('single_slice', False),
                'straight_to_next': section.get('straight_to_next', False),
                'thickness': section.get('thickness')
            }
            for section in config['sections']
        ],

        environment=Environment(
            config['free_stream_velocity'],
            config['fluid_density'],
            config['dynamic_viscosity']
        ),

        target_power=config['target_power'],
        expected_efficiency=config['expected_efficiency'],
        tip_speed_ratio=config['tip_speed_ratio'],
        blade_count=config['blade_count'],

        num_slices=config['slice_count']
    )

    # Export optimized geometry values
    (
        blade
        .slices
        .to_csv(os.path.join(output_dir, "geometry.csv"))
    )

    # Calculate and export estimated forecs
    (
        blade
        .estimate_forces()
        .to_csv(os.path.join(output_dir, "forces.csv"))
    )

    # Generate shape and export as STEP and STL
    shape = blade.build_shape()
    shape.export_step(os.path.join(output_dir, "blade.step"))
    shape.export_stl(os.path.join(output_dir, "blade.stl"))

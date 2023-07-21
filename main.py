"""
Note the confusing distinction between "section" and "slice":
- Blade design is bounded by user-defined values at arbitrary points along the
  blade; these points are called "sections"
- The blade is discretized into thin "slices" for numerical computation
"""

import os
import yaml
from Blade import Blade, Environment, BladeStem
from plots import draw_plots

output_dir = "output"

if __name__ == '__main__':
    with open("config.yaml") as f:
        config = yaml.safe_load(f.read())

    print("Finding optimal blade shape...")
    blade = Blade(
        stem=BladeStem(
            start=config['stem']['start'],
            length=config['stem']['length'],
            diameter=config['stem']['diameter']
        ),
        sections=[
            {
                'start_r': section.get('start_r'),
                'end_r': section.get('end_r'),
                'airfoil_name': section['airfoil'],
                'angle_deg': section['angle_of_attack']
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

    print("Exporting optimized parameters...")
    df_shape = blade.slices
    df_shape.to_csv(os.path.join(output_dir, "geometry.csv"))

    print("Calculate and export estimated forces...")
    df_forces = blade.estimate_forces()
    df_forces.to_csv(os.path.join(output_dir, "forces.csv"))

    print("Generate and export geometry...")
    shape = blade.build_shape(
        config.get('hollow', {}).get('thickness'),
        config.get('hollow', {}).get('min_chord'),
    )
    shape.export_step(os.path.join(output_dir, "blade.step"))
    shape.export_stl(os.path.join(output_dir, "blade.stl"))

    print("Generating plots...")
    draw_plots(blade, df_shape, df_forces, output_dir)

    print("Done")

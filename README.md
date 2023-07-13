# Turbine Blade Designer
This is a Python project to design optimized wind turbine blade geometry, using the blade element momentum method.

It is based on the approach described in [this paper](https://grantingram.org/download/wind_turbine_design.pdf) by [Grant Ingram](https://grantingram.org/).

## Dependencies

Requires Python 3.10 with these libraries:

- `PyYaml`
- `numpy`
- `pandas`
- [build123d](https://github.com/gumyr/build123d)

## Configuration

## Usage

Once the `config.yaml` file is ready, generate the blade geometry by running `main.py`:
```bash
python main.py
```

This will produce the following files into the `output` folder:

- `geometry.csv` - The calculated properties of the optimized turbine blade, for each discretized slice: twist, chord length, etc.
- `forces.csv` - An estimate of the radial and axial forces experienced at each slice of the blade, under design conditions.
- `blade.step` and `blade.stl`: CAD representations of the optimized blade.

Additionally, the following values are outputted to `stdout`:
- Blade radius
- Ideal rotational velocity and torque (after losses)
- Expected drag force, torque, and bending torque (before losses)

> The `Blade.estimate_forces()` function can be called with an optional `Environment` parameter.
> This allows calculating performance values at conditions outside the design environment.

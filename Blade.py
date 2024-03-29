import os
import pandas as pd
from dataclasses import dataclass
from typing import Optional
from build123d import Part

from optimization import optimize_blade
from build_shape import build_blade_shape
from estimate_forces import estimate_blade_forces

FOILS_PATH = "foil_data"

# Point of rotation for airfoil twist
ROTATION_ORIGIN = (0.3, 0.0)


@dataclass
class Environment:
    free_stream_velocity: float
    fluid_density: float
    dynamic_viscosity: float


@dataclass
class BladeStem:
    start: float
    length: float
    diameter: float


@dataclass
class BladeSection:
    blade: 'Blade'
    # Starting distance along blade length
    # (a value of None indicates the end of the blade)
    start_r: Optional[float]
    # Ending distance along blade length
    end_r: Optional[float]
    # Name of the airfoil profile
    airfoil_name: str
    # Target angle of attack
    angle_deg: float

    def __post_init__(self):
        if self.airfoil_name not in self.blade.airfoil_stats:
            self.blade.airfoil_stats[self.airfoil_name] = pd.read_csv(
                os.path.join(FOILS_PATH, self.airfoil_name, 'polar.csv'),
                header=9,
                index_col=0
            )
        if self.airfoil_name not in self.blade.airfoil_shapes:
            df = pd.read_csv(
                os.path.join(FOILS_PATH, self.airfoil_name, 'shape.csv'),
            )
            df.x = df.x - ROTATION_ORIGIN[0]
            df.y = -df.y - ROTATION_ORIGIN[1]
            self.blade.airfoil_shapes[self.airfoil_name] = df.to_numpy()

    @property
    def airfoil_stats(self):
        return self.blade.airfoil_stats[self.airfoil_name]


class Blade:
    def __init__(
            self,
            stem: BladeStem,
            sections: list[dict],
            environment: Environment,
            target_power: float,
            expected_efficiency: float,
            tip_speed_ratio: float,
            blade_count: int,
            num_slices: int = 30
    ):
        # Cached dictionary of airfoil aerodynamic properties
        self.airfoil_stats = {}  # airfoil_name -> pd.DataFrame
        # Cached dictionary of airfoil shape, as lists of 2D coordinates
        self.airfoil_shapes = {}  # airfoil_name -> np.array[n, 2]

        self.stem = stem
        self.sections = [
            BladeSection(self, **section)
            for section in sections
        ]
        self.environment = environment
        self.target_power = target_power
        self.expected_efficiency = expected_efficiency
        self.tip_speed_ratio = tip_speed_ratio
        self.blade_count = blade_count
        self.num_slices = num_slices

        self.slices = optimize_blade(
            self,
            environment,
            target_power,
            expected_efficiency,
            tip_speed_ratio,
            blade_count
        )

    def build_shape(self, hollow_thickness, hollow_min_chord) -> Part:
        return build_blade_shape(self, hollow_thickness, hollow_min_chord)

    def estimate_forces(
            self,
            environment: Optional[Environment] = None
    ) -> pd.DataFrame:
        if environment is None:
            environment = self.environment

        return estimate_blade_forces(self, environment)

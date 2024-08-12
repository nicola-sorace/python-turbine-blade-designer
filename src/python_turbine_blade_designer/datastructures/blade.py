import pandas as pd
from build123d import Part
from . import BladeStem
from . import Environment
from . import BladeSection
# from python_turbine_blade_designer import build_blade_shape, estimate_blade_forces, optimize_blade
from .. import build_blade_shape, estimate_blade_forces, optimize_blade


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
            environment: Environment | None = None
    ) -> pd.DataFrame:
        if environment is None:
            environment = self.environment

        return estimate_blade_forces(self, environment)

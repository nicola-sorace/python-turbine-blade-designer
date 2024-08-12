import os
import pandas as pd
from dataclasses import dataclass


FOILS_PATH = os.path.join(os.path.dirname(__file__), "../foil_data")

# Point of rotation for airfoil twist
ROTATION_ORIGIN = (0.3, 0.0)


@dataclass
class BladeSection:
    blade: 'Blade'
    # Starting distance along blade length
    # (a value of None indicates the end of the blade)
    start_r: float | None
    # Ending distance along blade length
    end_r: float | None
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

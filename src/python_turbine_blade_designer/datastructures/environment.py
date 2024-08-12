from dataclasses import dataclass


@dataclass
class Environment:
    free_stream_velocity: float
    fluid_density: float
    dynamic_viscosity: float

# Base SI units throughout (m, s, kg, N, etc.) unless otherwise stated

### Imports
import os
import numpy as np
import pandas as pd

### Functions
# Linear interpolation
def lerp(a, b, f):
    return a * (1-f) + b * f

# Sinusoidal interpolation
def sin_lerp(a, b, f):
    return a + (1 - (np.cos(f * np.pi) + 1) / 2) * (b - a)

def local_tsr(r, omega, V):
    return (omega * r) / V

def initial_twist(local_tsr):
    return np.pi/2 - 2/3 * np.arctan(1 / local_tsr)

def initial_ind_a(twist, local_solidity, Cl):
    return (1 + (4 * np.cos(twist)**2) / (
        local_solidity * Cl * np.sin(twist)))**-1

def initial_ind_r(ind_a):
    return (1 - 3 * ind_a) / (4 * ind_a - 1)

def twist(local_tsr, ind_a, ind_r):
    return np.arctan(local_tsr * (1 + ind_r) / (1 - ind_a))

def chord_length(r, twist, local_tsr, B):
    return (8 * np.pi * r * np.cos(twist)) / (3 * B * local_tsr)

def local_solidity(r, chord, B):
    return (B * chord) / (2 * np.pi * r)

def tip_loss_correction(r, twist, R, B):
    frac = -B/2 * (1 - r/R) / ((r/R) * np.cos(twist))
    return 2/np.pi * np.arccos(np.exp(frac))

def ind_a(local_solidity, twist, tip_loss_factor, Cl, Cd):
    frac = local_solidity * (Cl * np.sin(twist) + Cd * np.cos(twist)) / (
            4 * tip_loss_factor * np.cos(twist)**2)
    return frac / (1 + frac)

def ind_r(local_solidity, twist, tip_loss_factor, Cl, Cd, ind_a, local_tsr):
    frac = local_solidity * (Cl * np.cos(twist) - Cd * np.sin(twist)) / (
            4 * tip_loss_factor * local_tsr * np.cos(twist)**2)
    return frac * (1 - ind_a)

### Define basic design parameters

# Directory to search for airfoil data
FOILS_PATH = 'foil_data'

# Fluid properties
V = 10  # Free-stream velocity
RHO = 1.225  # Fluid density
MU = 16.82e-6  # Dynamic viscosity

# Desired/assumed turbine properties
DESIRED_POWER = 1e3  # Target power output
EFFICIENCY = 0.3 * 0.75  # Expected efficiency (blades * generator)
TSR = 5  # Tip speed ratio
B = 3  # Number of turbine blades

# Blade resolution (number of discrete sections for BEM theory)
RES = 30

### Calculate resultant properties

# Calculate the required blade radius based on above parameters
R = np.sqrt((2*DESIRED_POWER) / (EFFICIENCY * RHO * np.pi * V**3))
print('Blade radius (from center of rotation):', R)

# List of the radius at each section
# rs = np.linspace(SECTIONS[0]['start_r'], R, RES)
rs = np.array([0.1, 0.2] + list(np.linspace(0.3, R, RES)))
# rs[-1] *= 0.99999  # Correction to avoid NANs
rs[-1] *= 0.995  # Correction to avoid NANs

# Rotational properties
omega = (TSR * V/R)  # Angular velocity
rpm = 60 * omega / (2 * np.pi)  # Angular velocity (RPM)
T = DESIRED_POWER / omega  # Required torque
print('Target torque:', T)

### Setup sections for solving

'''
Section configuration

Define the airfoil to use at different distances from the center of rotation.
Setting both 'start_r' and 'end_r' forces an exact foil for that section of the
blade segment. If only 'start_r' is defined, the airfoil is enforced only at
that specific radius. All undefined blade sections will smoothly interpolate
between the adjacent foils. Blade will automatically end at radius 'R'.

Possible dictionary keys:
 start_r: Radius at which the section starts
 end_r (optional): Enforces the section up to this radius
 airfoil: Name of the airfoil to be used
 thickness (optional): Specify the airfoil's relative max thickness
 angle_deg: Desired Angle of Attack (in degrees)
 forced_size (optional): Chord length to enforce (requires 'end_r')
 interp (optional): Force smooth chord length from last section (BROKEN)
'''
SECTIONS = [
            {'start_r': 0.1, 'end_r': 0.2,
             'airfoil': 'circle', 'angle_deg': 5,
             'forced_size': 0.06, 'thickness': 1},
            {'start_r': 0.3,
             'airfoil': 'NACA0018', 'angle_deg': 5,
             'interp': True, 'thickness': 0.18},
            {'start_r': 0.6,
             'airfoil': 'NACA4418', 'angle_deg': 2.5},
            {'start_r': R,
             'airfoil': 'NACA4418', 'angle_deg': 6.5},
        ]

# Create indexing for foil names
foil_names = []
for s in SECTIONS:
    try:
        s['foil_id'] = foil_names.index(s['airfoil'])
    except ValueError:
        foil_names.append(s['airfoil'])
        s['foil_id'] = len(foil_names) - 1

# Load foil properties from CSVs
foil_props = [pd.read_csv(os.path.join(FOILS_PATH, s['airfoil'], 'polar.csv'),
              header=9, index_col=0)
              for s in SECTIONS]

# Get lift and drag coefficients by interpolation
for i, s in enumerate(SECTIONS):
    df = foil_props[s['foil_id']]
    s['Cl'] = np.interp([s['angle_deg']], df.index, df['Cl'])[0]
    s['Cd'] = np.interp([s['angle_deg']], df.index, df['Cd'])[0]

# Generate foil indices at each blade section (decimal index for interpolation)
section_ids = np.zeros(len(rs))
for i, r in enumerate(rs):
    for j, s in enumerate(SECTIONS):
        if j == len(SECTIONS) - 1 and r >= s['start_r']:
            # The last section continues forever
            section_ids[i] = j
            break
        if r < s['start_r']:
            if j == 0:
                # Must be a rounding error; assign foil
                section_ids[i] = j
                break
            # Interpolate between last foil and this one
            prior_s = SECTIONS[j - 1]
            int_start = prior_s.get('end_r', prior_s['start_r'])
            int_end = s['start_r']
            f = (r - int_start) / (int_end - int_start)
            section_ids[i] = lerp(j-1, j, f)
            break
        if 'end_r' in s:
            if s['start_r'] <= r <= s['end_r']:
                # Inside fixed foil range
                section_ids[i] = j
                break
            # Move onto next foil
            continue

### Iteratively calculate twist for each section

# Setup initial conditions
local_tsrs = [local_tsr(r, omega, V) for r in rs]
ts = [initial_twist(local_tsr) for local_tsr in local_tsrs]
cs = [chord_length(r, t, local_tsr, B)
      for r, t, local_tsr in zip(rs, ts, local_tsrs)]
local_solidities = [local_solidity(r, c, B)
                    for r, c in zip(rs, cs)]

# Interpolate section properties to each section
def section_lerp(prop_name):
    return [lerp(SECTIONS[int(np.floor(i))][prop_name],
            SECTIONS[int(np.ceil(i))][prop_name],
            np.mod(i, 1))
            for i in section_ids]


Cls = section_lerp('Cl')
Cds = section_lerp('Cd')
ind_as = np.array([initial_ind_a(t, local_solidity, Cl)
                  for t, local_solidity, Cl in zip(ts, local_solidities, Cls)])
ind_rs = np.array([initial_ind_r(ind_a) for ind_a in ind_as])

# Iterate to find optimal solution
for j in range(1000):
    old_as = ind_as.copy()
    old_rs = ind_rs.copy()
    for i in range(len(rs)):
        # Iterate over blade sections
        ts[i] = twist(local_tsrs[i], ind_as[i], ind_rs[i])
        #TODO Avoid optimizing fixed chord length sections
        cs[i] = chord_length(rs[i], ts[i], local_tsrs[i], B)
        local_solidities[i] = local_solidity(rs[i], cs[i], B)
        Q = tip_loss_correction(rs[i], ts[i], R, B)
        ind_as[i] = ind_a(local_solidities[i], ts[i], Q,
                          Cls[i], Cds[i])
        ind_rs[i] = ind_r(local_solidities[i], ts[i], Q,
                          Cls[i], Cds[i], ind_as[i], local_tsrs[i])

    # Check for convergence
    error_a = np.max(np.abs(ind_as - old_as))
    error_r = np.max(np.abs(ind_rs - old_rs))
    if max(error_a, error_r) < 1e-15:
        print(f'Converged in {j} iterations')
        break
    elif j == 999:
        print('ERROR: Failed to converge after {j} iterations')

# Fixed sections

for i, r in enumerate(rs):
    for j, s in enumerate(SECTIONS):
        if 'end_r' in s and s['start_r'] <= r <= s['end_r']:
            if 'forced_size' in s:
                cs[i] = s['forced_size']
            break
        elif j != 0:
            last_s = SECTIONS[j-1]
            last_r = last_s.get('end_r', last_s['start_r'])
            if s.get('interp', False) and last_r <= r <= s['start_r']:
                i_start = np.argmin(np.abs(rs - last_r))
                i_end = np.argmin(np.abs(rs - s['start_r']))
                f = (r - last_r) / (s['start_r'] - last_r)
                thickness = lerp(last_s['thickness'], s['thickness'], f)
                cs[i] = sin_lerp(cs[i_start], cs[i_end], f)


### Calculate forces on blade at target rotational speed

# Width of each section (for force calculations)
# dr = rs[1] - rs[0]
drs = (np.append(rs[1:], rs[-1]) - np.insert(rs[:-1], 0, rs[0])) / 2

# Axial forces
dF_as = [local_solidity * np.pi * RHO *
         (V**2 * (1-ind_a)**2) / (np.cos(twist)**2) *
         (Cl*np.sin(twist) + Cd*np.cos(twist)) * r * dr
         for local_solidity, ind_a, twist, Cl, Cd, r, dr in
         zip(local_solidities, ind_as, ts, Cls, Cds, rs, drs)]
# Radial forces (NOT torque)
dF_rs = [local_solidity * np.pi * RHO *
         (V**2 * (1-ind_a)**2) / (np.cos(twist)**2) *
         (Cl*np.cos(twist) - Cd*np.sin(twist)) * r * dr
         for local_solidity, ind_a, twist, Cl, Cd, r, dr in
         zip(local_solidities, ind_as, ts, Cls, Cds, rs, drs)]
# Torque contributions
dTs = dF_rs * rs

print('Total drag force:', np.sum(dF_as))
print('Total torque:', np.sum(dF_rs * rs))

### Write blade properties to file

aoas_deg = np.deg2rad(section_lerp('angle_deg'))
twists_rad = ts + np.deg2rad(aoas_deg)
twists_deg = np.rad2deg(ts) + aoas_deg

# Remap interpolation to be in terms of foil rather than section
airfoils = [(foil_names[SECTIONS[int(np.floor(f))]['foil_id']],
            foil_names[SECTIONS[int(np.ceil(f))]['foil_id']])
            for f in section_ids]
airfoils = [a if a == b else a+','+b for a, b in airfoils]
interp_factors = section_ids

df = pd.DataFrame(data={
            'radius': rs,
            'angle_of_twist_deg': twists_deg,
            'angle_of_twist_rad': twists_rad,
            'chord_length': cs,
            'airfoils': airfoils,
            'interp_factor': interp_factors,
            'axial_force': dF_as,
            'radial_force': dF_rs,
        })
df.to_csv('blade_design.csv')

print(df)

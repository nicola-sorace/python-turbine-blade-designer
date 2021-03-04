import numpy as np
import pandas as pd

RES = 35
R = 0.5

angles = np.linspace(0, 2*np.pi, 35, endpoint=False)
xs = R * np.cos(angles) + 0.3
ys = R * np.sin(angles)

df = pd.DataFrame(data={
        'x': xs,
        'y': ys,
    })

df.to_csv('shape.csv', index=False)

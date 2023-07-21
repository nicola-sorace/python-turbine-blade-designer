import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle
try:
    import seaborn as sns
    sns.set_theme()
except ImportError:
    print("Install Seaborn for prettier plots")
from Blade import Blade


def draw_plots(
        blade: Blade,
        df_shape: pd.DataFrame,
        df_forces: pd.DataFrame,
        output_dir: str
):
    fig, axs = plt.subplots(6, 1, sharex=True, figsize=(10, 12))
    # Twists & chords
    axs[0].set_title("Twist (degrees)")
    axs[0].plot(df_shape.radius, np.degrees(df_shape.twist))
    axs[1].set_title("Chord (m)")
    axs[1].plot(df_shape.radius, df_shape.chord)
    axs[1].set_ylim(0, None)
    # Lift/drag coefficients
    axs[2].set_title("Drag Coefficient")
    axs[2].plot(df_shape.radius, df_shape.drag_coefficient)
    axs[2].set_ylim(0, None)
    axs[3].set_title("Lift Coefficient")
    axs[3].plot(df_shape.radius, df_shape.lift_coefficient)
    axs[3].set_ylim(0, None)
    # Induction factors
    axs[4].set_title("Induction factors")
    axs[4].plot(df_shape.radius, df_shape.axial_induction, label="Axial")
    axs[4].plot(df_shape.radius, df_shape.radial_induction, label="Radial")
    axs[4].legend(loc='upper left')
    axs[4].set_ylim(0, None)
    # Forces
    axs[5].set_title("Forces (N)")
    axs[5].plot(df_forces.radius, df_forces.axial_force, label="Drag")
    axs[5].plot(df_forces.radius, df_forces.radial_force, label="Lift")
    axs[5].legend(loc='upper left')
    axs[5].set_ylim(0, None)
    axs[-1].set_xlabel("Distance from rotation axis (m)")
    axs[-1].set_xlim(0, None)
    plt.tight_layout()
    fig.subplots_adjust(top=0.9)

    def label_region(name: str, start=None, end=None):
        if start is None and end is None:
            end = blade.slices.radius.max()
        y = 0.91
        color = 'crimson'
        fig_start = fig_end = None
        if start is not None:
            fig_start, _ = fig.transFigure.inverted().transform(
                axs[0].transData.transform((start, 0))
            )
            fig_end = fig_start
        if end is not None:
            fig_end, _ = fig.transFigure.inverted().transform(
                axs[0].transData.transform((end, 0))
            )
            if fig_start is None:
                fig_start = fig_end
        fig_mid = (fig_start + fig_end) / 2
        fig.text(
            fig_mid, y,
            name,
            ha='left',
            va='center',
            rotation_mode='anchor',
            rotation=90,
            fontsize=11,
            color=color
        )

        for ax in axs:
            if start is not None and end is not None:
                y0, y1 = ax.get_ylim()
                ax.add_patch(Rectangle(
                    (start, y0),
                    end-start, y1-y0,
                    fill=False,
                    linestyle='dashed',
                    linewidth=1.5,
                    hatch='/',
                    color=color
                ))
            elif start is not None:
                ax.axvline(start, color=color, linestyle='dashed')
            elif end is not None:
                ax.axvline(end, color=color, linestyle='dashed')

    label_region(
        "Stem",
        blade.stem.start,
        blade.stem.start + blade.stem.length
    )
    # label_region("Tip", df_shape.radius.max())
    for section in blade.sections:
        label_region(
            section.airfoil_name,
            section.start_r,
            section.end_r
        )

    plt.show()
    fig.savefig(os.path.join(output_dir, 'plots.svg'))

# =========================================================
# scripts/global_processors/compare_sampling_grid_nb.py
# =========================================================

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from config_gt import MAIN_DIR


# ======================================
# CUSTOM COLORS
# ======================================

METHOD_COLORS={

    "m0":"blue",
    "m1":"red",
    "m2":"green"
}

GRID_ALPHA=.55
GRID_WIDTH=1.5
POINT_SIZE=60


# ======================================
# Remove only boundary points
# ======================================

def remove_boundaries(df):

    xvals=np.sort(
        df["x1"].unique()
    )

    yvals=np.sort(
        df["x2"].unique()
    )

    xmin,xmax=(
        xvals[0],
        xvals[-1]
    )

    ymin,ymax=(
        yvals[0],
        yvals[-1]
    )

    df=df[

        (df["x1"]!=xmin)
        &
        (df["x1"]!=xmax)
        &
        (df["x2"]!=ymin)
        &
        (df["x2"]!=ymax)

    ]

    return df


# ======================================
# callable
# ======================================

def run(main_dir):

    main_dir=Path(main_dir)

    methods=[]

    for m in ["m0","m1","m2"]:

        dirs=list(
            main_dir.glob(
                f"{m}_*"
            )
        )

        if len(dirs)==0:
            continue

        df=pd.read_csv(
            dirs[0]/"ground_truth.csv"
        )

        # only remove boundary points
        df=remove_boundaries(df)

        methods.append(
            (m,df)
        )

    if len(methods)==0:
        return


    # ====================================
    # density background
    # ====================================

    allx=np.concatenate([

        df["x1"].values

        for _,df in methods

    ])

    ally=np.concatenate([

        df["x2"].values

        for _,df in methods

    ])

    xy=np.vstack([

        allx,
        ally

    ])

    kde=gaussian_kde(
        xy
    )

    xx,yy=np.mgrid[

        allx.min():allx.max():300j,

        ally.min():ally.max():300j

    ]

    coords=np.vstack([

        xx.ravel(),
        yy.ravel()

    ])

    z=kde(
        coords
    ).reshape(
        xx.shape
    )

    plt.figure(
        figsize=(15,12)
    )

    plt.contourf(

        xx,
        yy,
        z,

        levels=25,
        alpha=.35

    )


    # ====================================
    # grids
    # ====================================

    for method,df in methods:

        color=METHOD_COLORS[method]

        x=np.sort(
            df["x1"].unique()
        )

        y=np.sort(
            df["x2"].unique()
        )

        for yy in y:

            plt.plot(

                x,
                [yy]*len(x),

                "-",

                color=color,

                alpha=GRID_ALPHA,

                linewidth=GRID_WIDTH

            )

        for xx in x:

            plt.plot(

                [xx]*len(y),
                y,

                "-",

                color=color,

                alpha=GRID_ALPHA,

                linewidth=GRID_WIDTH

            )

        plt.scatter(

            df["x1"],
            df["x2"],

            color=color,

            s=POINT_SIZE,

            label=method

        )


    plt.xticks([])
    plt.yticks([])

    plt.legend()

    plt.tight_layout()

    out=(

        main_dir/
        "sampling_grid_compare_nb.png"

    )

    plt.savefig(
        out,
        dpi=300
    )

    plt.close()

    print(
        f"Saved: {out}"
    )


# ======================================
# standalone
# ======================================

if __name__=="__main__":

    run(
        MAIN_DIR
    )
# =========================================================
# sampler_selectivity_m2.py
# Picasso-style selectivity sampling
# Dynamic r computation
#
# resolution = number of intervals
# points      = resolution + 1
# =========================================================

import numpy as np
from functools import lru_cache


# ==========================================================
# Dynamic Picasso skew computation
# ==========================================================

@lru_cache(maxsize=None)
def _compute_r(resolution,
               target_space=0.20,
               target_points=0.80,
               tol=1e-6):

    n = resolution + 1

    k = int(np.floor(target_points * n))

    def ratio(r):

        num = (
            0.5 +
            sum(r**i for i in range(1, k))
        )

        den = (
            0.5 +
            sum(r**i for i in range(1, n-1))
            + 0.5*(r**(n-1))
        )

        return num / den

    lo = 1.000001
    hi = 100.0

    while hi-lo > tol:

        mid = (lo+hi)/2

        val = ratio(mid)

        if val > target_space:
            lo = mid
        else:
            hi = mid

    return (lo+hi)/2


# ==========================================================
# Generate selectivity locations
# ==========================================================

def _target_selectivities(
        resolution,
        distribution="EXPONENTIAL",
        startpoint=0.0,
        endpoint=1.0):

    n = resolution + 1

    # ------------------------------------
    # Uniform
    # ------------------------------------

    if distribution.upper()=="UNIFORM":

        return np.linspace(
            startpoint,
            endpoint,
            n
        ).tolist()


    # ------------------------------------
    # Picasso exponential
    # ------------------------------------

    elif distribution.upper()=="EXPONENTIAL":

        r = _compute_r(resolution)

        # exact Picasso normalization

        a = 1.0
        cur = a
        total = a/2

        for i in range(1, n+1):

            cur *= r

            if i != n:
                total += cur
            else:
                total += cur/2

        a = 1/total


        # generate axis

        vals=[]

        cur=a
        cumulative=a/2

        for i in range(1,n+1):

            vals.append(
                startpoint +
                cumulative
            )

            cur*=r

            increment=(
                cur *
                (endpoint-startpoint)
            )

            if i==n:
                increment/=2

            cumulative += increment


        vals[0] = startpoint
        vals[-1] = endpoint

        return vals


    else:

        raise ValueError(
            f"Unknown distribution={distribution}"
        )


# ==========================================================
# Existing code unchanged
# ==========================================================

def _read_pg_stats(conn, table, column):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT histogram_bounds::text,
               most_common_vals::text,
               most_common_freqs
        FROM pg_stats
        WHERE tablename=%s
        AND attname=%s
        """,
        (table,column)
    )

    row=cur.fetchone()

    cur.close()

    if row is None:
        raise RuntimeError(
            f"No pg_stats row for "
            f"{table}.{column}"
        )

    return row


def _parse_array_text(s, caster):

    if s is None:
        return []

    s=s.strip()

    if s.startswith("{"):
        s=s[1:-1]

    if not s:
        return []

    return [
        caster(
            x.strip().strip('"')
        )
        for x in s.split(",")
    ]


def _cast_for_column(conn,table,column):

    cur=conn.cursor()

    cur.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name=%s
        AND column_name=%s
        """,
        (table,column)
    )

    row=cur.fetchone()

    cur.close()

    dtype=row[0]

    if dtype in (
        "integer",
        "bigint",
        "smallint"
    ):
        return int,dtype

    if (
        dtype.startswith("numeric")
        or dtype in (
            "real",
            "double precision"
        )
    ):
        return float,dtype

    if dtype=="date":

        import datetime

        def to_date(s):
            return datetime.date.fromisoformat(s)

        return to_date,dtype

    return float,dtype


def _interp(lo, hi, frac):

    if hasattr(lo,"toordinal"):

        a=lo.toordinal()
        b=hi.toordinal()

        return type(lo).fromordinal(
            round(
                a+
                frac*(b-a)
            )
        )

    return lo + frac*(hi-lo)


def _build_cdf_table(
        hist_bounds,
        mcv_vals,
        mcv_freqs):

    mcf_sum=sum(mcv_freqs) if mcv_freqs else 0.0

    B=max(
        len(hist_bounds)-1,
        1
    )

    bucket_mass=(
        (1-mcf_sum)/B
    )

    mcv_lookup=dict(
        zip(
            mcv_vals,
            mcv_freqs
        )
    )

    pts=[]
    cdf=0

    if not hist_bounds:

        for v in sorted(
                mcv_lookup.keys()):

            cdf+=mcv_lookup[v]

            pts.append(
                (v,cdf)
            )

        return pts

    pts.append(
        (
            hist_bounds[0],
            0.0
        )
    )

    for i in range(
            1,
            len(hist_bounds)):

        cdf += bucket_mass

        pts.append(
            (
                hist_bounds[i],
                cdf
            )
        )

    return pts


def _invert(cdf_pts,target_sel):

    if target_sel<=cdf_pts[0][1]:
        return cdf_pts[0][0]

    for i in range(
            1,
            len(cdf_pts)):

        vlo,clo=cdf_pts[i-1]
        vhi,chi=cdf_pts[i]

        if clo<=target_sel<=chi:

            if chi==clo:
                return vlo

            frac=(
                (target_sel-clo)
                /
                (chi-clo)
            )

            return _interp(
                vlo,
                vhi,
                frac
            )

    return cdf_pts[-1][0]


def sample(conn,
           table,
           column,
           resolution):

    hist_str,\
    mcv_str,\
    mcv_freqs=(
        _read_pg_stats(
            conn,
            table,
            column
        )
    )

    cast,_=(
        _cast_for_column(
            conn,
            table,
            column
        )
    )

    hist_bounds=(
        _parse_array_text(
            hist_str,
            cast
        )
    )

    mcv_vals=(
        _parse_array_text(
            mcv_str,
            cast
        )
    )

    mcv_freqs=(
        list(mcv_freqs)
        if mcv_freqs
        else []
    )

    cdf_pts=(
        _build_cdf_table(
            hist_bounds,
            mcv_vals,
            mcv_freqs
        )
    )

    sels=(
        _target_selectivities(
            resolution,
            "EXPONENTIAL"
        )
    )

    return [
        _invert(
            cdf_pts,
            s
        )
        for s in sels
    ]


def selectivities(
        resolution):

    return _target_selectivities(
        resolution,
        "EXPONENTIAL"
    )
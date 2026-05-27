# =========================================================
# sampler_selectivity_m2.py
#
# Picasso selectivities
# +
# exact SQL percentile_cont()
#
# resolution=10
#
# => 11 points
# =========================================================

import math
import numpy as np
from functools import lru_cache
import psycopg2.sql as sql


@lru_cache(maxsize=None)
def _compute_r(
        resolution,
        target_space=0.20,
        target_points=0.80,
        tol=1e-6):

    n=resolution+1

    k=int(
        round(
            target_points*
            resolution
        )
    )

    def ratio(r):

        num=(
            0.5
            +
            sum(
                r**i
                for i in range(
                    1,
                    k
                )
            )
        )

        den=(
            0.5
            +
            sum(
                r**i
                for i in range(
                    1,
                    n-1
                )
            )
            +
            0.5*(r**(n-1))
        )

        return num/den


    lo=1.000001
    hi=100


    while hi-lo>tol:

        mid=(lo+hi)/2

        val=ratio(mid)

        if val>target_space:
            lo=mid
        else:
            hi=mid

    return (lo+hi)/2


def _target_selectivities(
        resolution):

    n=resolution+1

    r=(
        _compute_r(
            resolution
        )
    )

    a=1
    cur=a
    total=a/2


    for i in range(
            1,
            n+1):

        cur*=r

        if i!=n:
            total+=cur
        else:
            total+=cur/2


    a/=total


    cur=a
    cumulative=a/2

    vals=[]


    for i in range(
            1,
            n+1):

        vals.append(
            cumulative
        )

        cur*=r

        inc=cur

        if i==n:
            inc/=2

        cumulative+=inc


    vals=np.array(vals)

    vals/=vals[-1]

    vals[0]=0
    vals[-1]=1

    return vals.tolist()


def _read_sorted_values(
        conn,
        table,
        column):

    query=sql.SQL("""
        SELECT {col}
        FROM {tbl}
        WHERE {col} IS NOT NULL
        ORDER BY {col}
    """).format(
        col=sql.Identifier(column),
        tbl=sql.Identifier(table)
    )

    cur=conn.cursor()

    cur.execute(query)

    vals=[
        r[0]
        for r in cur.fetchall()
    ]

    cur.close()

    return vals


def _percentile_cont_exact(
        values,
        p):

    n=len(values)

    if n==0:
        return None

    if n==1:
        return values[0]

    rank=1+p*(n-1)

    j=math.floor(rank)

    gamma=rank-j


    j-=1

    if j<0:
        return values[0]

    if j>=n-1:
        return values[-1]


    xj=values[j]
    xjp1=values[j+1]

    return (
        (1-gamma)*xj
        +
        gamma*xjp1
    )


def sample(
        conn,
        table,
        column,
        resolution):

    sels=(
        _target_selectivities(
            resolution
        )
    )

    vals=(
        _read_sorted_values(
            conn,
            table,
            column
        )
    )

    return [

        _percentile_cont_exact(
            vals,
            s
        )

        for s in sels
    ]


def selectivities(
        resolution):

    return _target_selectivities(
        resolution
    )
# =========================================================
# sampler_selectivity_m1.py
#
# resolution=10
#
# 0.0,0.1,...,1.0
#
# => 11 points
#
# Manual implementation:
# exact SQL percentile_cont()
# =========================================================

import math
import psycopg2.sql as sql


def _target_selectivities(resolution):

    return [
        i/resolution
        for i in range(
            resolution+1
        )
    ]


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
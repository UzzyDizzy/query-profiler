# =========================================================
# sampler_selectivity_m3.py
#
# M3:
# Random selectivity sampling (axis-wise)
#
# resolution = number of intervals
#
# Example:
#
# resolution = 10
#
# grid version:
# 0.0, 0.1, 0.2, ..., 1.0
#
# => 11 points
#
# M3 version:
#
# keep:
# 0.0 and 1.0
#
# and generate RANDOM points in-between
#
# Example:
#
# 0.0,
# 0.03,
# 0.17,
# 0.28,
# ...
# 0.91,
# 1.0
#
# => total = resolution + 1 points
#
# =========================================================

import random
import psycopg2.sql as sql


# =========================================================
# generate random selectivities
# =========================================================
def _target_selectivities(
    resolution,
    seed=None
):

    rng = random.Random(seed)

    # keep boundaries
    sels = [0.0]

    # generate internal random points
    internal_count = resolution - 1

    internal = [
        rng.random()
        for _ in range(internal_count)
    ]

    internal.sort()

    sels.extend(internal)

    sels.append(1.0)

    return sels


# =========================================================
# main sampler
# =========================================================
def sample(
    conn,
    table,
    column,
    resolution,
    seed=None
):

    sels = _target_selectivities(
        resolution,
        seed
    )

    query = sql.SQL("""
        SELECT percentile_cont(%s::float8[])
        WITHIN GROUP(
            ORDER BY {col}
        )
        FROM {tbl}
    """).format(
        col=sql.Identifier(column),
        tbl=sql.Identifier(table)
    )

    cur = conn.cursor()

    cur.execute(
        query,
        (sels,)
    )

    values = cur.fetchone()[0]

    cur.close()

    values = _coerce(
        values,
        conn,
        table,
        column
    )

    return values


# =========================================================
# datatype coercion
# =========================================================
def _coerce(
    values,
    conn,
    table,
    column
):

    cur = conn.cursor()

    cur.execute("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name=%s
        AND column_name=%s
    """,
    (table, column))

    row = cur.fetchone()

    cur.close()

    dtype = (
        row[0]
        if row
        else "double precision"
    )

    if dtype in (
        "integer",
        "bigint",
        "smallint"
    ):
        return [
            int(round(v))
            for v in values
        ]

    return [
        float(v)
        for v in values
    ]


# =========================================================
# expose selectivities
# =========================================================
def selectivities(
    resolution,
    seed=None
):

    return _target_selectivities(
        resolution,
        seed
    )


# =========================================================
# example
# =========================================================
if __name__ == "__main__":

    res = 10

    sels = selectivities(
        resolution=res,
        seed=42
    )

    print("Random Selectivities:")
    print(sels)
    print("Number of points:", len(sels))
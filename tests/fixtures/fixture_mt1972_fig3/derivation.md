# `fixture_mt1972_fig3` — hand derivation

The gold-standard parity fixture. Reproduces the scale-variance decomposition
of the 16×16 checkerboard matrix in **Figure 3 of Moellering & Tobler (1972)**.
The paper reports `TSS = 1152`, `TDF = 255`; the R reference file
`reference/raster-R-implementation/scale-variance-example.R` confirms both
values in Example 4 comments. The per-level breakdown below is derived from
first principles — every number is a closed-form count, no floating-point.

## Input

A 16×16 integer raster of the values `{2, 5, 8}`. Extent `(0, 16) × (0, 16)`,
CRS omitted (input carries none; scale column reports pixel units). Stored
in this fixture as `input.tif`. The exact matrix is embedded verbatim in
`_build_hand_derived.py` — its structure:

- **Top-left 8×8 quadrant**: 2-5 checkerboard (32 twos, 32 fives).
- **Top-right 8×8**: 5-8 checkerboard (32 fives, 32 eights).
- **Bottom-left 8×8**: 5-8 checkerboard (32 fives, 32 eights).
- **Bottom-right 8×8**: 2-5 checkerboard (32 twos, 32 fives).

## Parameters

- `base_level_factor = 2`
- `num_levels = None` → auto = `floor(log₂(16)) + 1 = 5`
- `agg_fun = "mean"`
- `na_handling = "drop_na"` (no NAs present)

Five levels are produced: 16×16 → 8×8 → 4×4 → 2×2 → 1×1.

## Counts of {2, 5, 8}

- **2s**: top-left 32 + bottom-right 32 = **64**.
- **8s**: top-right 32 + bottom-left 32 = **64**.
- **5s**: everywhere else = 256 − 64 − 64 = **128**.

Total sum = `64·2 + 128·5 + 64·8` = `128 + 640 + 512` = **1280**.
Grand mean = `1280 / 256` = **5.0**.

## Total sum of squares

`TSS = Σ (value − 5)²` over all 256 cells.
Each 2 contributes `(2−5)² = 9`; each 8 contributes `(8−5)² = 9`; each 5 contributes `0`.

`TSS = 64·9 + 128·0 + 64·9 = 576 + 0 + 576 = **1152**.`  ✓ (matches paper)

`TDF = N − 1 = 256 − 1 = **255**.`  ✓

## Level rasters (iterative 2×2 mean aggregation)

**Level 2 (8×8)** — mean of every 2×2 block of level 1:

- Every 2×2 in the top-left 8×8 averages to `(2+2+5+5)/4 = 3.5`.
- Every 2×2 in the top-right 8×8 averages to `(5+5+8+8)/4 = 6.5`.
- Symmetry → bottom-left 8×8 of level-2 = 6.5, bottom-right 8×8 = 3.5.

Level 2 is therefore a 2×2 block structure: `[[3.5, 6.5], [6.5, 3.5]]` with each block 4×4.

**Level 3 (4×4)** — mean of every 2×2 block of level 2. Each 2×2 block at level 2 is constant (all 3.5 or all 6.5), so level 3 inherits the same 2×2 macro-pattern, now with each block 2×2:
```
3.5 3.5 | 6.5 6.5
3.5 3.5 | 6.5 6.5
-----------------
6.5 6.5 | 3.5 3.5
6.5 6.5 | 3.5 3.5
```

**Level 4 (2×2)** — each 2×2 of level 3 is already constant:
```
3.5 6.5
6.5 3.5
```

**Level 5 (1×1)** — mean of level 4 = `(3.5 + 6.5 + 6.5 + 3.5) / 4 = 5.0` = grand mean.

## Sum of squares per level

`SS_level_n = Σ_(original cells) (value_level_(n+1) − value_level_n)²`

### Level 1 → Level 2

In each 2×2 block of level 1 (all structurally identical):
- Parent value: 3.5, 6.5, 6.5, or 3.5 (by quadrant).
- Within the block, values are `{2, 2, 5, 5}` or `{5, 5, 8, 8}` — in both cases two cells deviate `±1.5` from the parent mean.
- Block contribution: `4 · (1.5)² = 4 · 2.25 = 9.0`.

There are **16 blocks per quadrant × 4 quadrants = 64 blocks**. So:

`SS_1 = 64 · 9 = **576**.`

### Level 2 → Level 3

In every 8×8 quadrant, `value_level_2 ≡ value_level_3` (both take the same value throughout the quadrant — 3.5 in TL/BR, 6.5 in TR/BL). All differences are 0.

`SS_2 = **0**.`

### Level 3 → Level 4

Same argument: within each 8×8 quadrant, `value_level_3 ≡ value_level_4`.

`SS_3 = **0**.`

### Level 4 → Level 5

Level 5 is the grand mean 5.0. Level 4 is 3.5 (TL, BR) or 6.5 (TR, BL), constant across each 8×8 quadrant of the original (64 cells per quadrant). Each original cell contributes `(5.0 − 3.5)² = 2.25` or `(5.0 − 6.5)² = 2.25`.

Per quadrant: `64 · 2.25 = 144`. Four quadrants:

`SS_4 = 4 · 144 = **576**.`

### Level 5 → synthetic top (grand mean)

Level 5 is already one cell whose value equals the grand mean. `SS_5 = 0`.

### Identity check

`Σ SS_n = 576 + 0 + 0 + 576 + 0 = **1152** = TSS.`  ✓

## Degrees of freedom per level

Cell-count-difference form: `df_n = N_level_n − N_level_(n+1)` (non-NA cells, no NAs here).

| level | N_level_n | N_level_(n+1) | df_n |
|-------|-----------|---------------|------|
| 1     | 256       | 64            | 192  |
| 2     | 64        | 16            | 48   |
| 3     | 16        | 4             | 12   |
| 4     | 4         | 1             | 3    |
| 5     | 1         | 1 (synthetic) | 0    |

`Σ df_n = 192 + 48 + 12 + 3 + 0 = **255** = TDF.`  ✓

## Mean squares, shares, cumulative share

- `MS_n = SS_n / df_n`, `NaN` when `df_n = 0`.
- `ss_share_n = SS_n / TSS`. Paper-canonical (sums to 1).
- `ms_share_n = MS_n / Σ(MS_n excluding NaN)`. Denominator = `3 + 0 + 0 + 192 = 195`.
- `ss_cumulative_n = Σ_{m≤n} ss_share_m`.
- `scale_n = base_resolution · factor^(n−1) = 1 · 2^(n−1) = {1, 2, 4, 8, 16}` (pixel units, no CRS).

| level | scale | sum_squares | df  | mean_square | ss_share | ms_share    | ss_cumulative |
|-------|-------|-------------|-----|-------------|----------|-------------|---------------|
| 1     | 1     | 576         | 192 | 3.0         | 0.5      | 3/195       | 0.5           |
| 2     | 2     | 0           | 48  | 0.0         | 0.0      | 0           | 0.5           |
| 3     | 4     | 0           | 12  | 0.0         | 0.0      | 0           | 0.5           |
| 4     | 8     | 576         | 3   | 192.0       | 0.5      | 192/195     | 1.0           |
| 5     | 16    | 0           | 0   | NaN         | 0.0      | NaN         | 1.0           |

These are the exact expected values committed in `expected_components.csv`
and `expected_totals.json`. Any implementation that disagrees with them on
this input has a bug.

`raster.npy` is a derived artifact built from `input.tif` by
`tests/fixtures/_build_npy.py`; the `.tif` remains the source of truth for
parity tests. The `.npy` exists so the WASM-deployed playground can load the
fixture without `rasterio`/GDAL.

## References

- Moellering, H., & Tobler, W. (1972). Geographical Variances. *Geographical Analysis*, 4(1), 34–50. See page numbers surrounding Figure 3.
- `reference/raster-R-implementation/scale-variance-example.R` Example 4.

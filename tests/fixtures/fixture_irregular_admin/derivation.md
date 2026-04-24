# `fixture_irregular_admin` — hand derivation

Pure-tabular fixture exercising the `scale_variance` core on a ragged
admin-style hierarchy (counties within states within regions). Fan-out
varies — some states have 3 counties, others 5; one region has 2 states,
another 4 — which means the closed-form even-case shortcut does not apply
and the irregular-case formulae of Moellering & Tobler Table 3 are exercised.

Values are chosen to make every level's SS an integer and the grand mean a
round number, for easy by-hand verification.

## Structure and values

| region | state | counties (value) |
|--------|-------|------------------|
| R1 | S1 | C1 (10), C2 (20), C3 (30) |
| R1 | S2 | C4 (8), C5 (14), C6 (20), C7 (26), C8 (32) |
| R2 | S3 | C9 (40), C10 (50), C11 (60) |
| R2 | S4 | C12 (38), C13 (44), C14 (50), C15 (56), C16 (62) |
| R2 | S5 | C17 (70), C18 (80), C19 (90) |
| R2 | S6 | C20 (68), C21 (74), C22 (80), C23 (86), C24 (92) |

Counts: 2 regions, 6 states, 24 counties. Region 1 has 2 states (8 counties),
Region 2 has 4 states (16 counties).

## Level means (paper-canonical, direct over finest-level observations)

- **State means** (direct mean of the state's county values):
  S1 = `(10+20+30)/3 = 20`, S2 = `(8+14+20+26+32)/5 = 20`,
  S3 = `(40+50+60)/3 = 50`, S4 = `(38+44+50+56+62)/5 = 50`,
  S5 = `(70+80+90)/3 = 80`, S6 = `(68+74+80+86+92)/5 = 80`.
- **Region means** (direct mean of the region's counties — **not** a mean of state means, because the paper's X̄_{i..} is the mean over all level-1 cells under parent *i*):
  R1 = `(60 + 100) / 8 = 20`. R2 = `(150 + 250 + 240 + 400) / 16 = 65`.
- **Grand mean**: `(160 + 1040) / 24 = 1200 / 24 = **50.0**`.

## Sum of squares per level

`SS_level_n = Σ_(counties) (value_level_(n+1) − value_level_n)²`

### Level 1 (counties → states)

Each state contributes its within-state sum of squared deviations from the state mean.

| state | values                 | Σ (value − state_mean)²                           |
|-------|------------------------|---------------------------------------------------|
| S1    | 10, 20, 30             | 100 + 0 + 100 = **200**                           |
| S2    | 8, 14, 20, 26, 32      | 144 + 36 + 0 + 36 + 144 = **360**                 |
| S3    | 40, 50, 60             | 100 + 0 + 100 = **200**                           |
| S4    | 38, 44, 50, 56, 62     | 144 + 36 + 0 + 36 + 144 = **360**                 |
| S5    | 70, 80, 90             | 100 + 0 + 100 = **200**                           |
| S6    | 68, 74, 80, 86, 92     | 144 + 36 + 0 + 36 + 144 = **360**                 |

`SS_1 = 200 + 360 + 200 + 360 + 200 + 360 = **1680**.`

### Level 2 (states → regions)

For each county, `value_level_3 − value_level_2` = (region mean) − (state mean). This is constant within each state.

- R1 (region mean 20):
  - S1 (state mean 20): `(20−20)² = 0` per county × 3 counties = **0**.
  - S2 (state mean 20): `0` × 5 = **0**.
- R2 (region mean 65):
  - S3 (50): `(65−50)² = 225` × 3 = **675**.
  - S4 (50): `225` × 5 = **1125**.
  - S5 (80): `(65−80)² = 225` × 3 = **675**.
  - S6 (80): `225` × 5 = **1125**.

`SS_2 = 0 + 0 + 675 + 1125 + 675 + 1125 = **3600**.`

### Level 3 (regions → grand mean)

Each county contributes `(grand_mean − region_mean)²`, constant within a region.

- R1 (mean 20): `(50−20)² = 900` × 8 counties = **7200**.
- R2 (mean 65): `(50−65)² = 225` × 16 counties = **3600**.

`SS_3 = 7200 + 3600 = **10800**.`

### Total SS and identity check

`TSS = Σ (value − 50)² over all 24 counties`:
- R1 counties 1–8 squared deviations:
  `(10−50)² + (20−50)² + (30−50)² = 1600 + 900 + 400 = 2900`
  `(8−50)² + (14−50)² + (20−50)² + (26−50)² + (32−50)² = 1764 + 1296 + 900 + 576 + 324 = 4860`
  R1 contribution: `2900 + 4860 = 7760`.
- R2 counties 9–24:
  `(40−50)² + 0 + (60−50)² = 100 + 0 + 100 = 200`
  `(38−50)² + (44−50)² + 0 + (56−50)² + (62−50)² = 144 + 36 + 0 + 36 + 144 = 360`
  `(70−50)² + (80−50)² + (90−50)² = 400 + 900 + 1600 = 2900`
  `(68−50)² + (74−50)² + (80−50)² + (86−50)² + (92−50)² = 324 + 576 + 900 + 1296 + 1764 = 4860`
  R2 contribution: `200 + 360 + 2900 + 4860 = 8320`.

`TSS = 7760 + 8320 = **16080**.`

Identity: `SS_1 + SS_2 + SS_3 = 1680 + 3600 + 10800 = **16080** = TSS.`  ✓

## Degrees of freedom per level

Per-parent form: `df_n = Σ_(parents at n+1) (distinct children at n − 1)`.

- `df_1 = (#counties per state − 1)` summed over states = `(3−1)+(5−1)+(3−1)+(5−1)+(3−1)+(5−1) = 2+4+2+4+2+4 = **18**`.
- `df_2 = (#states per region − 1)` summed over regions = `(2−1)+(4−1) = **4**`.
- `df_3 = #regions − 1 = 2 − 1 = **1**`.
- `Σ df_n = 18 + 4 + 1 = **23** = 24 − 1 = TDF.`  ✓

## Mean squares, shares, cumulative

- `MS_1 = 1680/18 = 280/3 ≈ 93.333`
- `MS_2 = 3600/4 = 900`
- `MS_3 = 10800/1 = 10800`
- `Σ MS = 280/3 + 900 + 10800 = 35380/3 ≈ 11793.333`

- `ss_share = SS/TSS = SS/16080`:
  - Level 1: `1680/16080 = 7/67 ≈ 0.1045`
  - Level 2: `3600/16080 = 15/67 ≈ 0.2239`
  - Level 3: `10800/16080 = 45/67 ≈ 0.6716`
  - Sum: `67/67 = 1`  ✓

- `ms_share = MS / Σ MS`:
  - Level 1: `(280/3) / (35380/3) = 280/35380 = 14/1769 ≈ 0.00791`
  - Level 2: `900 / (35380/3) = 2700/35380 = 135/1769 ≈ 0.07631`
  - Level 3: `10800 / (35380/3) = 32400/35380 = 1620/1769 ≈ 0.91577`

- `ss_cumulative`: `7/67, 22/67, 1.0`.
- `scale` column: `NaN` at every level (tabular input carries no intrinsic scale).

All these values are what gets committed to `expected_components.csv` and
`expected_totals.json` and what `scale_variance` is asserted against.

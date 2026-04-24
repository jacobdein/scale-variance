# Scale variance: theory and notation

This document grounds the algorithm implemented by `scalevar` in Moellering and Tobler (1972), *Geographical Variances*, and pins down the exact formulation the packages use. The original paper is at [../reference/Moellering-1972-Geographical Variances.pdf](../reference/Moellering-1972-Geographical%20Variances.pdf). Two R reference implementations exist in [../reference/](../reference/) — see that folder's README for their provenance and relative authority.

## The model

Consider a quantity `X` measured at the finest (lowest) level of a fully-nested hierarchy with `k` levels above the grand mean. Using Moellering and Tobler's notation for a three-level hierarchy (level 1 = α effect, level 2 = β effect, level 3 = γ effect, grand mean = µ):

```
X_ijk = µ + α_i + β_ij + γ_ijk              (Eq. 1)
```

Where:

- `µ` is the grand mean across all observations.
- `α_i = X̄_i.. − X̄...` is the deviation of the level-1 parent `i` from the grand mean.
- `β_ij = X̄_ij. − X̄_i..` is the deviation of the level-2 parent `ij` from its level-1 parent.
- `γ_ijk = X_ijk − X̄_ij.` is the deviation of a finest-level observation from its level-2 parent.

This is a fully nested fixed-effects ANOVA (type I). The decomposition makes no error term — we assume complete enumeration, not sampling.

## The partition (Eq. 12)

Squaring and summing Equation 1 over all observations (the cross-terms drop out because of the nesting structure):

```
Σ (X_ijk − X̄...)²  =  Σ (X̄_i.. − X̄...)²  +  Σ (X̄_ij. − X̄_i..)²  +  Σ (X_ijk − X̄_ij.)²

SS_total           =  SS_α                 +  SS_β                  +  SS_γ     (Eq. 12)
```

This is the core identity. Total variation around the grand mean partitions cleanly into contributions from each level. Dividing each term by the total yields the **share of total variance attributable to that level**:

```
ss_share_level_n  =  SS_level_n / SS_total
```

These shares sum to 1 by construction (Eq. 12). This is the paper-canonical decomposition and the default quantity reported by `scalevar` in its `ss_share` column.

### Mean squares and a different normalization

Dividing each `SS_level_n` by its degrees of freedom gives the classical **mean square** for that level:

```
MS_level_n  =  SS_level_n / df_level_n
```

These are the "scale variance components" of Moellering & Tobler Tables 2 and 3 and are useful for comparison *between levels of different sizes*, because `df` reflects the number of independent cells at that scale.

`scalevar` optionally reports an alternative normalization `ms_share = MS_level_n / sum(MS)` for users who want a df-weighted version. This is **not** the paper-canonical quantity — it is sometimes useful, but the default for "variance share" in the output is `ss_share`.

The earlier polygon-form R reference normalized to `ms_share` as the primary output. That was a deviation from the paper, and the packages correct it by making `ss_share` the default and reporting both values explicitly. See [`../reference/README.md`](../reference/README.md) for the full provenance.

## The even case

When the hierarchy has constant fan-out — every level-`n+1` parent contains exactly the same number of level-`n` children — the algebra simplifies. For a 2D grid with 2× linear nesting (4:1 area ratio), each parent has exactly 4 children at every level. In this regime:

```
df_α  =  I − 1                           # I = number of level-top parents
df_β  =  Σ_i (J_i − 1)                   # J_i = children of parent i at the next level down
df_γ  =  Σ_i Σ_j (K_ij − 1)
```

With constant `J` and `K`, the components can be written directly from the mean squares (see Moellering & Tobler Table 2).

## The irregular case

When the fan-out varies — either because the hierarchy is intrinsically ragged (counties-in-states, where some states have 3 counties and others have 67) or because some cells have missing data — the shortcut does not apply. The components must be computed from the sums of squared deviations and the degrees of freedom directly (Table 3 of the paper):

```
variance_component_level_n  =  SS_level_n / df_level_n
```

**This is the form `scalevar` implements.** It is strictly more general than the even case — it reduces to the even case when fan-out is constant — and it handles the realistic situation where some bins have missing data.

### Two equivalent expressions of `df_level_n`

For the irregular case, the degrees of freedom at level `n` can be written in two equivalent forms:

**Per-parent form** (used by the polygon reference):

```
df_level_n  =  Σ_(parents at level n+1)  (children_count − 1)
```

For each level-`n+1` parent, count its distinct level-`n` children, subtract 1, sum across parents.

**Cell-count difference form** (used by the raster reference):

```
df_level_n  =  N_level_n − N_level_(n+1)
```

Where `N_level_n` is the count of non-NA cells at level `n`.

These are algebraically identical whenever each level-`n` cell maps to exactly one level-`n+1` parent — which is true by construction in a fully nested hierarchy. Proof: the per-parent sum `Σ (c_p − 1)` equals `(Σ c_p) − P`, where `P` is the number of parents with at least one non-NA child. `Σ c_p` is the total number of non-NA level-`n` cells (each cell is counted once, under its unique parent), which is `N_level_n`. `P` is the number of non-NA level-`n+1` cells, which is `N_level_(n+1)`.

The packages are free to use whichever form is more efficient for a given input type — per-parent for tabular input, cell-count-difference for raster input — and the parity suite asserts they agree to machine precision.

## The top synthetic level

Both R references add a synthetic top level that represents the grand mean: its "value" is the mean of all level-1 values. This makes the decomposition symmetric — level `n`'s contribution is always computed against the mean of its parent at level `n+1`, including the topmost level which has a single parent (the entire study area). `scalevar` preserves this convention.

A `k`-level hierarchy yields `k` variance components — one per user-supplied level — and an additional synthetic level `k+1` representing the grand mean, which is used only to close the sum.

## The raster case as a special case

When the input is a raster, the hierarchy is generated by repeated aggregation: level 1 is the original raster, level `n+1` is level `n` aggregated by a factor of `b` (typically 2, sometimes 3 or 4) in each linear dimension. Each level-`n` cell has a unique, unambiguous level-`n+1` parent — the cell that contains it after aggregation.

In this regime:

- The "id column" at level `n` is simply the cell index in the level-`n` aggregated raster.
- The aggregation function (mean, sum, median, modal, …) is configurable. The paper implicitly assumes mean; the package allows any function that `terra::aggregate` or its Python equivalent accepts.
- The per-level value attached to each finest-level cell is the value of the level-`n` cell that contains it, obtained by *disaggregating* the level-`n` raster back to level-1 resolution (nearest-neighbor — every level-1 cell under the same level-`n` parent receives the same level-`n` value).

The SS and df computations are then:

```
SS_level_n  =  Σ_(over original cells)  (value_level_(n+1) − value_level_n)²
df_level_n  =  N_nonNA_level_n − N_nonNA_level_(n+1)
```

Which is algebraically identical to the tabular irregular-case formulation above. The packages' raster path calls into the same core after extracting values and IDs.

## The algorithm, step by step (tabular core)

Given a table with one row per finest-level observation, columns `id_level_1 ... id_level_k`, and a value column `value`:

1. **Drop rows where `value` is NA.** Level-1 cells with no data are excluded; parent means are computed from available children only.
2. **Append the synthetic top level.** Add `id_level_(k+1) = max(id_level_k) + 1` and `value_level_(k+1) = mean(value)` to every row.
3. **Compute level means.** For each level `n ≥ 2`, aggregate `value` (or `value_level_(n-1)`, equivalently) by `id_level_n` using the chosen aggregation function (default `mean`) and join these values back onto the main table as `value_level_n`.
4. **Compute sum of squares at each level.** For each level `n` in `1..k`, compute `SS_n = Σ (value_level_(n+1) − value_level_n)²` summed over all rows.
5. **Compute degrees of freedom at each level.** For each `n`, either the per-parent form or the cell-count-difference form (see above). Both yield the same number.
6. **Compute per-element contributions.** For each level `n`, group by `id_level_n` and record `value_level_n`, `value_level_(n+1)`, `sv = (value_level_(n+1) − value_level_n)²`, `sv_per_df = sv / df_n`. These are the **scale variance elements** — useful for mapping *where* variance accumulates at each scale.
7. **Compute per-level components.** `MS_n = SS_n / df_n`. `ss_share_n = SS_n / TSS`. Optionally `ms_share_n = MS_n / sum(MS)`.
8. **Compute total SS and total df** for reporting: `TSS = Σ (value − grand_mean)²`, `total_df = N − 1`.
9. **Sanity checks.** Assert `|Σ SS_n − TSS| < tolerance` and `Σ df_n == total_df` (both identities hold exactly in theory; floating-point tolerance applies in practice).

## Relationship to other methods

- **Spectral / wavelet variance.** Scale variance is a discrete, hierarchy-defined analogue of spectral analysis. Where spectral analysis requires regular sampling and decomposes by wavelength, scale variance accepts any nested aggregation and decomposes by hierarchical level.
- **Nested ANOVA (Type I, fixed effects).** Mathematically equivalent. Scale variance reframes the output — emphasizing the variance share at each scale rather than testing an effect for significance.
- **Moran's I and local spatial statistics.** Different question. Moran's I tests for clustering at a fixed scale; scale variance partitions variance *across* scales simultaneously.
- **Geographically weighted variance / multi-scale GWR.** Related intent (quantifying scale of effect), different machinery (continuous kernels vs. discrete hierarchy).

## What we do not implement (and why)

- **Significance testing.** The fixed-effects, complete-enumeration framing of Moellering & Tobler does not include an error term. Users who want hypothesis tests on the components should use a standard nested-ANOVA workflow (e.g. `aov` in R, `statsmodels` in Python) — `scalevar` exposes enough intermediate output (`SS`, `df`) to plug into those workflows.
- **Imputation.** When finest-level values are missing, the package drops them and proceeds. Upstream imputation (e.g. kriging, as used in the bird diversity study) is the user's responsibility; the packages stay narrow.
- **Improving the hierarchy.** Per Moellering & Tobler §1: "we do not here seek to improve the hierarchy." The package treats the hierarchy as given.
- **Significance-adjusted shares or confidence intervals.** Deferred; noted in the roadmap.

## References

- Moellering, H., & Tobler, W. (1972). Geographical Variances. *Geographical Analysis*, 4(1), 34–50.
- Scheffé, H. (1959). *The Analysis of Variance*. Wiley. (Classical nested ANOVA treatment.)

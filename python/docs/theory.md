# Theory

The full mathematical derivation lives at the repository root in [`docs/theory.md`](https://github.com/jacobdein/scale-variance/blob/main/docs/theory.md) — the canonical, language-agnostic treatment that the Python package and the R sibling both implement.

For convenience, key identities the Python implementation enforces:

## The decomposition (Moellering & Tobler 1972, Eq. 12)

$$
\sum_{ijk} (X_{ijk} - \bar X_{\ldots})^2 \;=\; \sum_{ijk} (\bar X_{i\ldots} - \bar X_{\ldots})^2 \;+\; \sum_{ijk} (\bar X_{ij\ldots} - \bar X_{i\ldots})^2 \;+\; \sum_{ijk} (X_{ijk} - \bar X_{ij\ldots})^2
$$

$$
SS_\text{total} \;=\; SS_{\text{level 1}} + SS_{\text{level 2}} + \cdots + SS_{\text{level k}}
$$

The shares `ss_share_n = SS_n / TSS` sum to 1 by construction. This is the **paper-canonical** quantity — `components.ss_share` in the result.

## Degrees of freedom

Two equivalent expressions for `df_level_n`:

**Per-parent form** (used by the tabular core):

$$
df_n \;=\; \sum_{\text{parents at level } n{+}1} \bigl(\text{distinct children at level } n \;-\; 1\bigr)
$$

**Cell-count-difference form** (equivalent, natural for rasters):

$$
df_n \;=\; N_{\text{non-NA at level } n} \;-\; N_{\text{non-NA at level } n{+}1}
$$

Both forms give the same number whenever each level-`n` cell maps to exactly one level-`n+1` parent — true by construction in a fully nested hierarchy. See the proof in [`docs/theory.md`](https://github.com/jacobdein/scale-variance/blob/main/docs/theory.md) (section "Two equivalent expressions of df_level_n").

## Sanity checks (enforced at end of compute)

| Identity | Tolerance |
|---|---|
| `Σ SS_n == TSS` | `1e-9` relative |
| `Σ df_n == total_df` | exact |

If either is violated, the compute function **raises** — this never happens in normal use; a violation implies a bug.

## What is *not* in the Python implementation

- **Significance testing.** The fixed-effects, complete-enumeration framing of Moellering & Tobler does not include an error term. `scalevar` exposes the intermediate `SS` and `df` values — pipe those into `statsmodels` if you want hypothesis tests.
- **Imputation.** Rows with NA at the finest level are dropped. Upstream imputation (e.g. kriging, as used in the original bird-diversity research codebase) is the user's responsibility.
- **Automatic hierarchy construction.** Per Moellering & Tobler §1: "we do not here seek to improve the hierarchy." The package treats the hierarchy as given.

## References

- Moellering, H., & Tobler, W. (1972). Geographical Variances. *Geographical Analysis*, 4(1), 34–50. <https://doi.org/10.1111/j.1538-4632.1972.tb00455.x>
- The 1972 paper PDF is bundled in the repo: [`reference/Moellering-1972-Geographical Variances.pdf`](https://github.com/jacobdein/scale-variance/blob/main/reference/Moellering-1972-Geographical%20Variances.pdf).

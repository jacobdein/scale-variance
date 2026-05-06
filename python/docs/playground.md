# Playground

A live, interactive explorable of the Moellering & Tobler (1972) decomposition,
running entirely in your browser via Pyodide. Nothing is sent to a server.

[**Open the playground →**](playground/){ .md-button .md-button--primary target="_blank" }

The playground reproduces Figure 3 from the original 1972 paper — a 16×16
checkerboard-of-checkerboards. Drag the `base_level_factor` slider and watch the
lollipop chart reshape. With the default settings (`base_level_factor=2`,
`agg_fun='mean'`) the totals match the paper exactly: `TSS = 1152`, `TDF = 255`.

Click **Generate Methods Appendix** to get:

- A paste-ready Python snippet pinned to the current `scalevar` release, with the
  fixture array inlined so it stands alone.
- A paper-language interpretation of your current parameter choices, suitable
  for the Methods chapter of a thesis with light editing.
- A shareable permalink encoding the parameters.
- The 1972 paper's BibTeX, ready to copy.

The playground is a sibling project to the `scalevar` Python package, not part
of it. Source: [`playground/`](https://github.com/jacobdein/scale-variance/tree/main/playground).

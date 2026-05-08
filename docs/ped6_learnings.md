# PED6 Reference Notes

These notes summarize behavior observed from the user-provided PED6 reference
package. The reference files stay in `local_data/` and are not committed.

## Modes

- PED6 has an input mode with structured family data and automatic drawing.
- PED6 has an edit mode that stores only a graphical raster: symbols, lines,
  and text cells.
- Edit-mode `.PED` files are layout files, not relationship data.
- Input-mode import/export uses `.PIP`, CSV, LINKAGE-style text, and BOADICEA
  export.

## Legacy `.PED` Grid

- Header starts with `PED hjp Kiel`.
- The second line contains `colRows: <columns> @ <rows>~` and display options.
- Cells are stored column-major.
- Cell types seen:
  - `E`: empty
  - `Mrf`: male symbol
  - `Wrf`: female symbol
  - `Srf`: other symbol such as diamond, abort, triangle
  - `Lrn`: line segment
  - `Tra`: free text
- Cell stream ends with `~~~`.

## Symbol Vocabulary

`PED.SYM` lists default symbols and line tools. Important examples:

- `mannc`, `frauc`: plain square/circle
- `konduktorc`, `konduktorinc`: carrier-style symbols
- `mannv`, `frauv`: vertically divided/fill variants
- `mannh`, `frauh`: horizontally divided/fill variants
- `manndh`, `fraudh`, `manndv`, `fraudv`: bar variants
- `mannrautec`, `fraurautec`: inner diamond variants
- `abortc`, `rautec`, `dreieckc`: special non-binary symbols

## Line Vocabulary

Common line tokens include:

- `horizontal`, `vertikal`, `plus`
- `l`, `ldown`, `lreverse`, `ldownreverse`
- `t`, `treverse`, `tstop`
- `brokenh`, `doppelt`, `doppellr`, `doppelthorizontal`
- arrow and complex join variants such as `vertikalpfeil`, `yreverse`,
  `wreverse`

## CSV/LINKAGE Shape

PED6 CSV import expects:

```text
Family ID, Individual ID, Father ID, Mother ID, Gender
```

Optional following columns:

- Phenotype or affection status
- Marker/decorator column for arrow/deceased markers
- Up to four text labels around the symbol
- Additional rows below the symbol

The structured import model should therefore stay separate from the edit-mode
grid model.

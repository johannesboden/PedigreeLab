# PedigreeLab

Linux-friendly prototype for editing genetic pedigree files.

The MVP stores pedigrees as `.ped` files using the common six-column pedigree
shape:

```text
family_id individual_id paternal_id maternal_id sex phenotype
```

`0` means unknown parent. Sex follows the PLINK convention: `1` male, `2`
female, `0` unknown. Phenotype is stored as free text for now.

Canvas positions are saved as comments so the `.ped` file remains readable by
basic tools:

```text
# PedigreeLab position P001 120 240
```

## Run

```bash
python3 -m pedigreelab.server --file samples/example.ped --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.

## Current MVP

- Load and save `.ped` files.
- Draw parents, partners, and children.
- Add a person.
- Add parents for the selected person.
- Add a child for the selected person.
- Remove the selected person and clear broken parent links.
- Edit ID, sex, phenotype, parents, and canvas position.
- Auto-save changes after edits, drag-and-drop, layout updates, and relation changes.
- Auto-layout by generation.
- Export the visible pedigree as SVG with embedded `.ped` metadata.

The `.ped` parser is intentionally isolated in `pedigreelab/ped_io.py` so a
real sample file can be mapped without touching the UI.

## Legacy Graphical PED Export

Some `.ped` files are not row-based genetics data, but graphical grid files
with entries like `Lrn`, `Mrf`, `Wrf`, and `Srf`. These can be rendered as SVG
and PNG:

```bash
python3 -m pedigreelab.legacy_ped_image input.ped --svg output.svg --png output.png
```

The SVG embeds the original `.ped` text in its metadata.

When the web app is started with this kind of file, it switches into a grid
editor automatically:

```bash
python3 -m pedigreelab.server --file local_data/beispiel_legacy.ped --port 8766
```

In grid mode, users can click cells, choose symbols or line tools, add notes,
and rely on the same auto-save mechanism.

See `docs/ped6_learnings.md` for implementation notes derived from the PED6
reference package.

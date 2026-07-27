# EML to MBOX

Converts a selected directory of `.eml` files into an MBOX export and optional recipient analysis.

## Configuration

Copy the tracked example before running the script:

```bash
cp config.example.json config.json
```

`config.json` may contain personal email addresses and is ignored by Git. Generated `.mbox`, `.csv`, and `.xlsx` exports are also ignored and must not be committed.

## Run

```bash
python eml_to_mbox.py
```

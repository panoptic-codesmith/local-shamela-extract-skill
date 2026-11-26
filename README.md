# shamela-extract

A Vibe skill for extracting the full text of downloaded books from a local
Maktaba Shamela (shamela.ws) Linux install into clean, LLM-digestible Arabic
markdown — the source-side workflow for Arabic-to-English book translation
projects, replacing OCR entirely.

## Install

```sh
git clone https://github.com/panoptic-codesmith/local-shamela-extract-skill \
  ~/.vibe/skills/shamela-extract
```

(or clone elsewhere and symlink into `~/.vibe/skills/`)

## Contents

| Path | Purpose |
|---|---|
| `SKILL.md` | The procedure: install discovery, catalog queries, decoder state, output contract |
| `scripts/shamela_probe.java` | Stored-fields dump via the install's bundled Lucene 10.4 jars + JRE |
| `scripts/shamela_decode.py` | Pure-Python header/LZ4 scanner for the stored-fields files |
| `template/AGENTS.md` | Project-side standing rules; copied into each new project dir on first extraction |

The project `AGENTS.md` template is also available as a gist:
https://gist.github.com/panoptic-codesmith/ec634d9e63ecf14aca62c9af7f36e274

## Status

Catalog/metadata reading (SQLite) is proven. Stored-field body-text decoding
(LZ4-compressed Lucene 10.4 chunks) is at the reverse-engineering frontier;
`SKILL.md` Step 4 records the exact known state so future sessions continue
from it rather than restarting. The install is only ever accessed read-only.

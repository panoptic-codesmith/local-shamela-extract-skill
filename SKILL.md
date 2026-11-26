---
name: shamela-extract
description: Extract the full text of downloaded books from a local Maktaba Shamela (shamela.ws) Linux install into clean, LLM-digestible Arabic markdown, for Arabic-to-English translation projects. Load when the user wants source material from their Shamela library — instead of OCR — for a book or translation project.
---

# Shamela Extract

Extract downloaded books from the local Maktaba Shamela Linux install into a
clean markdown corpus for LLM translation work. This replaces OCR as the
source-text workflow: the text is born-digital, so there are no confidence
scores, no per-page fragments, and no correction journals.

## Locate the install

Probe for `database/master.db` — do not hardcode the path (the install is a
user-extracted AppImage buffer that can move). Known location:

    ~/Downloads/appimage_buffer/shamela/
      database/
        master.db                          # catalog: books, authors, categories (SQLite)
        cover.db                           # covers (SQLite)
        service/S1.db                      # Quran text — rows are Shamela-encoded blobs
        service/S2.db                     # Arabic roots dictionary
        store/{page,book,title,author,...}/  # Lucene 10.4 indexes: downloaded book text,
                                             # LZ4-compressed stored fields
      app/linux/64/jre/2/bin/java          # bundled JRE
      app/lucene/2/                        # bundled Lucene 10.4 jars

**Read-only mandate:** never write to anything under the install. Open SQLite
with `mode=ro` URI (`sqlite3.connect('file:...?mode=ro', uri=True)`). A stray
write can corrupt the library (note the `S2.db-wal` / `-shm` files: the app
expects to own that directory).

## Environment facts

- **Python discovery is adaptive**: try `python3 -c 'import sqlite3'` first; if
  it fails, walk `python3.14`, `python3.13`, `python3.12`, … until one works.
  Known quirk on one Rocky Linux 10 container: `python3`/`python3.12` are
  broken (bad prefix) while `python3.14` works — do not assume this holds on
  other machines or distros.
- `typst` (for the downstream translation phase, not extraction) is typically
  at `~/.cargo/bin/typst`.
- Approval gates have historically blocked: executing the bundled Java,
  deep binary probing of `.fdt` files from the Downloads tree, and running
  scripts out of `/tmp` — stage scripts in the *project* tree instead, and if
  a read-only probe is denied twice, hand the command to the user rather than
  hammering the gate.
- Humans can peek at any downloaded book through the Shamela app GUI; the
  catalog is directly openable in any SQLite browser. The stored book text is
  LZ4-compressed binary — invisible to `strings`; only a script can read it.

## Idempotency

- The install is never modified: every access is read-only, so any number of
  re-runs is safe.
- Re-extraction to the same `--out` dir is overwrite semantics: `book.md` /
  `sections/` are regenerated cleanly, never appended or duplicated. Running
  the skill repeatedly leaves a clean, deterministic tree.
- Before reusing an existing `quran-index.json`, validate it (parseable JSON,
  sane structure/verses count); if invalid or truncated, rebuild it. A corrupt
  index must never silently propagate.

## Step 1 — identify the book

```python
import sqlite3
con = sqlite3.connect('file:<install>/database/master.db?mode=ro', uri=True)
rows = con.execute("""
  SELECT book_id, book_name, authors, major_ondisk, minor_ondisk
  FROM book WHERE book_name LIKE ?
""", ('%<search>%',)).fetchall()
```

- `major_ondisk != 0` → the book is downloaded and extractable
  (`=2` additionally flags a multi-part book where `minor_ondisk` parts are on
  disk). If `major_ondisk = 0`, the book is catalog-only: tell the user to
  download it inside the app first.
- Grab `authors` / author death date too — the death date drives the
  honorific-ligature rules in normalization below.

## Step 2 — output contract

Target directory: the skill is invoked with an `--out <dir>` for the project
(the user keeps each project in its own tree; do NOT write into the install or
into unrelated projects).

Emit `<outdir>/<book-slug>/`:

- **< 150 KB text → single `book.md`.** **≥ 150 KB → `sections/NN-slug.md`**
  split at the top heading level plus a `toc.md` index. Never emit an
  assembled full-text duplicate alongside sections (drift hazard).
- **YAML frontmatter on `book.md` (or `toc.md`)** — provenance replaces the
  entire OCR-era confidence system:

```yaml
source: shamela.ws
book_id: <id>
title_ar: <arabic title>
author: <author>
author_died: <AH/CE if known>
category: <category>
extracted_at: <ISO date>
shamela_version: <from database or install>
sections: N            # only when split
```

- **Headings:** build the hierarchy from Shamela's TOC metadata (`store/title`
  index / catalog), as `#`…`####` with stable slugs. Do not guess.
- **Normalization at extraction time:**
  - drop page markers like `(ص ٢٣)` / `ص 23` — fragments must never split
    paragraphs; emit continuous prose,
  - footnotes → markdown `[^N]` syntax,
  - keep editorial brackets `«…»` as delivered,
  - Qur'an spans keep ﴿…﴾ with full harakat exactly as extracted,
  - collapse honorifics to single-codepoint ligatures (table below).

**Ligature table (apply at extraction):**

| Ligature | Replaces | For |
|---|---|---|
| ﷺ (U+FDFA) | صلى الله عليه وسلم | the Prophet Muhammad only |
| ﷾ (U+FDFB) | سبحانه وتعالى | Allah only |
| ﵀ (U+FDF0) | رحمه الله | scholars |
| ﵁ (U+FDF1) | رضي الله عنه | the Prophet's companions |
| ﷷ (U+FDF7) | عليه سلام | prophets other than Muhammad (Isa, Musa, Ibrahim, Yusuf…) |

Dual/plural forms («رضي الله عنهما», «رحمهم الله») stay spelled out. Never
attach a ligature to anyone else.

## Step 3 — quran-index (conditional, project-level)

If `<outdir>/quran-index.json` exists → reuse it, skip extraction. Else build
it once (it is book-independent — the user copies it between projects):

- Preferred: decode the bundled mushaf `service/S1.db` (table `b`, columns
  `i, s, l, d, a, b` — rows are Shamela-encoded blobs, e.g. leading `\x14`,
  not plain UTF-8).
- Fallback if S1 decoding stalls: mark each verse with `surah:ayah` by
  verifying the ﴿…﴾ span against the standard mushaf from the model's own
  knowledge, and let the index grow verse-by-verse as citations are resolved.

Then annotate this book's ﴿…﴾ spans inline as `[سورة: آية]`, resolved by
matching against the index.

## Step 4 — extract the body text

The text of downloaded books lives ONLY in the Lucene indexes (fields seen in
`store/page`: `book_key, book, page, body, m_body, n_body`, plus `date`,
`author`, `group`). It is `Lucene90StoredFieldsHighData`: header magic
`0x3FD76C17` + coded name + version, chunks of packed ints +
LZ4-compressed blobs. Status of the two staged decoders in `scripts/`:

- `shamela_probe.java` — opens the index through the bundled Lucene 10.4 jars
  (`app/linux/64/jre/2/bin/java -cp 'app/lucene/2/*:...' …`) and dumps stored
  fields per document. Never yet executed here (gate-blocked). This is the
  clean route: try it first; if the gate denies twice, print the exact command
  for the user to run and take over from its output.
- `shamela_decode.py` — pure-Python header parser + LZ4 block scanner
  (`python3.14 scripts/shamela_decode.py <file.fdt>`). Proven to run and parse
  headers/codes; the chunk/packed-ints payload layout is NOT yet cracked
  (brute-force LZ4 scan found 0 plain-Arabic blobs, so the blob framing
  differs from a raw LZ4 block). Continue reverse-engineering from here
  rather than restarting: known-bad assumptions to revisit are chunk-start
  offset after the (still unidentified) 4 bytes following the header, and
  PackedInts encoding of doc base/doc count/lengths.

Sequencing rule: attempt Java-bundled route → Python decoder → if the
payload stays sealed, fall back to asking the user to copy the book text out
of the Shamela GUI (manual layer, breaks automation but unblocks the
project), and record what is missing in the session notes.

## Step 5 — finishing

- Optional `manifest.json` one-line-per-book file when extracting in batch.
- **New project directories:** when the `--out` dir does not yet contain an
  `AGENTS.md`, seed it by copying this skill's `template/AGENTS.md` to
  `<outdir>/AGENTS.md` — it carries the project-side standing rules (read-only
  install, idempotency, ligature table, output contract, translation layout,
  recompile rule). If an `AGENTS.md` already exists, leave it untouched; never
  write outside `--out` or the skill directory.
  The template is also published as a gist
  (https://gist.github.com/panoptic-codesmith/ec634d9e63ecf14aca62c9af7f36e274)
  — the bundled copy in this skill directory is the source of truth; the gist
  is a convenience for external bootstrap.
- Never modify the install; leave index `.lock` files untouched.

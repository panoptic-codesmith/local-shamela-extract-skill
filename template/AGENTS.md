# Shamela Extraction & Translation Workflow

Source material comes from a local Maktaba Shamela (shamela.ws) install, via the
global skill `shamela-extract` (`~/.vibe/skills/shamela-extract/`). The skill owns
the full procedure (install layout, catalog queries, decoder state, output
contract); this file holds the project-side standing rules.

The OCR-era protocol that used to live here is retired. Any OCR tooling present
in the tree (`tools/ocr_review.py` and per-page exports) is a last-resort
fallback for texts that exist in no digital library — never the default path.

Run Vibe from the project root.

## Golden rules (extraction)
1. Extraction always runs through the `shamela-extract` skill — load it. Do not
   re-derive the install layout, decoder state, or output contract from scratch.
2. The Shamela install is strictly read-only: open SQLite with
   `sqlite3.connect('file:...?mode=ro', uri=True)`; never write anything under
   the install (including `.lock` / WAL files).
3. Provenance replaces confidence: extracted text is born-digital. There are no
   OCR scores, no correction journals, no snapshots. Record source metadata
   (book_id, author, author_died, category, extracted_at, shamela_version) in
   the extract's YAML frontmatter instead.
4. Re-extraction is idempotent: outputs overwrite cleanly, never append or
   duplicate. An existing `quran-index.json` is validated before reuse
   (parseable JSON, sane verse count); if invalid or truncated, rebuild it.
   The index is project-level and portable — copy it between projects freely.
5. Locate the install by probing for `database/master.db`; do not trust a
   hardcoded path (it is a user-extracted AppImage buffer that can move).
6. Python is discovered adaptively, per the skill (on this box `python3` is
   broken and `python3.14` works; do not assume that elsewhere).

## Arabic ligature convention (honorifics)
Use the single-codepoint honorific ligatures, and ONLY for the person they belong to:
- ﷺ (U+FDFA, «صلى الله عليه وسلم») — only after the Prophet Muhammad.
- ﷾ (U+FDFB, «سُبْحَانَهُ وَتَعَالَى») — only after Allah.
- ﵀ (U+FDF0, «رحمه الله») — only for scholars.
- ﵁ (U+FDF1, «رضي الله عنه») — only for the Prophet's companions.
- ﷷ (U+FDF7, «عليه سلام») — for any prophet other than Muhammad (Isa, Musa,
  Ibrahim, Yusuf, ...).
Apply at extraction time: collapse the spelled-out phrase to its ligature.
Never attach a ligature to anyone else — dual/plural forms («رضي الله عنهما»,
«رحمهم الله») have no assigned ligature and stay spelled out.

## Extraction output contract (summary — the skill holds the full version)
- `<outdir>/<book-slug>/book.md` for books under ~150 KB; for larger ones
  `sections/NN-slug.md` split at the top heading level plus a `toc.md` index —
  never an assembled full-text duplicate.
- Headings come from Shamela's TOC metadata, never guessed.
- Normalize at extraction: drop page markers («ص 23»), footnotes → `[^N]`,
  keep editorial brackets «...», keep ﴿...﴾ Qur'an spans with full harakat, tag
  citations `[سورة: آية]` resolved against `quran-index.json`.
- Optional batch `manifest.json`, one line per book.

## Translation / final product (English `.typ` books)

Final English translations live in `final_product/<Book>/en/` and compile with:
`typst compile <book>-en.typ <book>-en.pdf --font-path ../../fonts`
(fonts are in `final_product/fonts/`; body = EB Garamond, Qur'an blocks = Amiri,
Arabic headings = Kitab).

STANDING RULE — "recompile": when the user says "recompile <file>" for any
`.typ` under this tree, it means they just edited and saved that file. Compile
it immediately with no questions and report errors/warnings if any. Do not
"re-fix", reformat, or otherwise touch the file — the user's saved edit is the
source of truth.

## Outputs per book
- Source extract: `book.md` (or `sections/` + `toc.md`) with provenance
  frontmatter, plus the project-level `quran-index.json`.
- Translation: `final_product/<Book>/en/<book>-en.typ` and compiled PDF.
- Historical (OCR era), if any exist in this tree: legacy `<Book>/` exports
  with their `corrections-log.md`, `review.html`, and related artifacts are
  read-only history.

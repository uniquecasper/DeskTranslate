# Export saved vocabulary to Anki

DeskTranslate can export the vocabulary entries you explicitly saved in Learning.

1. Open **Learning**.
2. Optionally choose source/target language filters and enter a search term. Export uses all saved entries matching those filters, not just the currently visible page.
3. Select **Export Anki CSV…** and choose a destination.
4. In Anki, use **File → Import**, choose the CSV file, select the note type/deck, and map `Front` to the front field and `Back` to the back field. The language-code columns are optional.

The file is UTF-8 CSV with Anki text-import metadata for column names and comma separation. See the [Anki text-file import manual](https://docs.ankiweb.net/importing/text-files.html) for supported file headers and import options.

The export includes only source term, translation and the two language codes. It does not include database IDs, timestamps, credentials or spaced-repetition scheduling data. It is created only after you explicitly select the export action and choose a file location.

To reduce spreadsheet formula-injection risk, formula-like terms beginning with `=`, `+`, `-` or `@` are rejected rather than silently changed. Edit the saved term before exporting it. The export does not modify or delete your DeskTranslate vocabulary.

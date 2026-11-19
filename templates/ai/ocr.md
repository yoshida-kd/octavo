---
title: Transcribe an image (OCR)
input: [image, pdf-pages]
output: '{dir}/{name}.md'
---
Transcribe all the text in this image as Markdown.

- Keep the reading order. Keep headings as headings, lists as lists, and tables as Markdown tables.
- Copy the text exactly as printed, in its own language and script. Do not translate, correct or
  summarize it.
- Mark a word you cannot read as [illegible].
- Leave out page headers, footers and page numbers.
- Output only the transcription, with no comments before or after it.

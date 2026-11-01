# Android third-party reference notices

DeskTranslate's Android implementation was informed by the following public projects. The current implementation reuses their documented architecture and independently written equivalents; no source files from these three repositories have been copied into DeskTranslate.

- [MangaLens](https://github.com/avadhesh1017/MangaLens) — MIT License, copyright (c) 2026 Avadhesh. Its screen-translation capture and overlay concepts were reviewed as implementation references.
- [ALSTMobile](https://github.com/navidseyedain/ALSTMobile) — MIT License, copyright (c) 2026 Navid Seyedain. Its MediaProjection flow, OCR bounding-box model, draggable floating control and coordinate-aligned overlay lifecycle were reviewed as implementation references.
- [TextGrab](https://github.com/AhmetCanArslan/TextGrab) — MIT License. Its word/line OCR structure, confidence-aware recognition, selectable text model and translation-engine separation were reviewed as implementation references.
- [AidanPark/screen-translator](https://github.com/AidanPark/screen-translator) — the Apache-2.0-licensed source at commit `8717cf0` (2026-09-23) was consulted for area-crop and stable translation-target design. No source code from that repository was copied. Later revisions use PolyForm Noncommercial 1.0.0; those revisions are not used as a source-code dependency.

The MIT license notices for MangaLens and ALSTMobile are reproduced below because their detailed implementation patterns are referenced in this application.

## MangaLens — MIT License

Copyright (c) 2026 Avadhesh

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## ALSTMobile — MIT License

Copyright (c) 2026 Navid Seyedain

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# DeskTranslate 2.2.0

DeskTranslate 2.2 improves the efficiency and observability of the Windows screen-translation pipeline.

## What's new

- Reduce repeated window-inspection overhead by validating a bound application window directly, while retaining process-identity checks, occlusion safeguards and safe fallback behavior.
- Reduce visual change-gate work by downsampling before grayscale conversion.
- Avoid sending the same recognized subtitle to a translation provider repeatedly when only its background changes. Genuine text and punctuation revisions remain eligible for translation.
- Inspect the latest accepted capture, OCR, stabilization, translation and delivery timings from the status tooltip. Diagnostic output is limited to numeric stage durations and excludes recognized/translated content and secrets.
- Preserve the dictionary-backed vocabulary, source-code protection and spaced-repetition learning improvements introduced in 2.1.0.

## Windows release and verification

The release contains the Windows x64 installer, portable ZIP, matching library source archive, SBOMs, build provenance, SHA-256 manifest, Sigstore signature bundles and GitHub build attestations. The release pipeline runs the pinned Windows pre-deployment suite, packaged-runtime and installer-upgrade checks, artifact privacy scan, two-hour steady endurance and thirty-minute fault endurance before publishing.

The executables are not Authenticode publisher-signed because no trusted publisher certificate is configured. Sigstore signatures and GitHub attestations provide verifiable build identity/provenance, but do not replace Windows publisher reputation; Windows may display an unknown-publisher or SmartScreen warning.

Physical interaction on the user's Windows device is not claimed by hosted CI.

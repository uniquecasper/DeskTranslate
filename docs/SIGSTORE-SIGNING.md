# Sigstore signing for Windows artifacts

The 2.0.1 qualification workflow signs every generated Windows executable and portable ZIP with **keyless Sigstore signing** after qualification succeeds.

## What the signature proves

- GitHub Actions obtains a short-lived signing identity through OIDC; no long-lived private signing key or publisher PFX is stored in repository secrets.
- Sigstore records signing evidence in its transparency log.
- The workflow immediately verifies each signature against the exact repository workflow identity and GitHub Actions OIDC issuer.
- Each signed file receives an adjacent `.sigstore.json` bundle. The release-candidate workflow artifact includes these bundles alongside the files they verify.

The action is pinned to Sigstore's `gh-action-sigstore-python` v3.4.0 commit.

## Verify a downloaded file on Windows

Install the Sigstore verifier:

```powershell
py -m pip install --upgrade sigstore
```

For a file signed by a manual run on `main`, verify it with:

```powershell
py -m sigstore verify identity `
  --bundle "DeskTranslate.exe.sigstore.json" `
  --cert-identity "https://github.com/uniquecasper/DeskTranslate/.github/workflows/release.yml@refs/heads/main" `
  --cert-oidc-issuer "https://token.actions.githubusercontent.com" `
  "DeskTranslate.exe"
```

Use the exact ref shown in the successful GitHub Actions run if the workflow was run from a different branch. For example, a push-triggered run on the candidate branch uses `refs/heads/claude/windows-installer-2-0-1`, not `refs/heads/main`. Verify the EXE and ZIP separately with their matching bundle files.

A successful verification confirms that the downloaded bytes match the file signed by the expected DeskTranslate GitHub Actions workflow identity. A failed verification means the file must not be treated as an authentic artifact from that workflow.

## Important distinction

Sigstore provides cryptographic artifact-signing and provenance verification. It does **not** embed a Windows Authenticode publisher signature into the PE executable, establish a Windows-trusted publisher name, or remove SmartScreen warnings. Authenticode remains a separate release-signing option.

# AOSP replacement sourcing (for the 7 substitution slots, 2026-10-01)

Constraint: replacements must be open-source, license-clean inputs — never
lift APKs from another vendor's proprietary ROM.

## Slots + sources

| Slot (removed) | Replacement | Source path |
|---|---|---|
| WebViewGoogle64 + TrichromeLibrary64 | AOSP System WebView (`com.android.webview`, arm64) | `platform/external/chromium-webview` prebuilt (arm64/webview.apk) from AOSP checkout; version may lag — pin + record version; Chromium-source build deferred |
| NetworkStackGoogle | AOSP NetworkStack (`com.android.networkstack`) | AOSP GSI system image (phh Treble AOSP / LineageOS GSI) extraction; verify package + version |
| DocumentsUIGoogle | AOSP DocumentsUI (`com.android.documentsui`) | same GSI source |
| GooglePackageInstaller | AOSP PackageInstaller (`com.android.packageinstaller`) | same GSI source |
| TagGoogle | AOSP Tag (`com.android.tag`) | same GSI source |
| CaptivePortalLoginGoogle | AOSP CaptivePortalLogin | same GSI source |
| ZBoard_Global (keyboard) | AOSP LatinIME | same GSI source (or LineageOS keyboard); verify default-IME provisioning via SetupWizard_MFV |
| GoogleDialer + Messages | AOSP Dialer + Messaging (or ZTE default if present — CHECK first whether Telecom_MFV already defaults elsewhere) | same GSI source; verify role-holder defaults (RoleManager) post-flash |
| PlayAutoInstallConfig | DELETE (no replacement; setup auto-installs nothing) | — |
| NBBrowser/Weather/Cleanup/Booking/Wallpapers/PhotoEditor | DELETE (user installs alternatives) | — |

## Signature/permission mechanics (must implement in rebuild)

- Transplanted AOSP APKs carry AOSP test-key signatures, NOT the ZTE platform key.
  `signature|privileged` permissions are NOT auto-granted to non-platform priv-apps
  since Android 8 — each transplant needs explicit entries in the corresponding
  `privapp-permissions-*.xml` (we own these files; add stanzas mirroring AOSP).
- System-UID sharedUserId modules (none among transplants — verify by checking
  `sharedUserId` in inventory: NetworkStack/DocumentsUI/PackageInstaller are
  non-sharedUid; confirm at rebuild time).
- WebView provider: `config_webViewPackage` overlay/sysconfig must point at
  `com.android.webview`; TrichromeLibrary arrangement (WebViewGoogle64 dir +
  separate TrichromeLibrary64) must be replaced by the single-APK layout and
  any `webviewproviders.xml` updated.
- Priv-app WATCH: `system/etc/permissions/privapp-permissions-platform.xml`
  (AOSP) already covers AOSP module permissions — cross-check after transplant.

## GSI-as-donor verification checklist (before use)

1. Donor GSI exact version + download URL + SHA-256 recorded in firmware-manifests/.
2. Extract APK + confirm package name, versionCode, targetSdk (SDK 36-compatible).
3. Confirm no GMS classes inside donor APK (run scripts/20-gms-scan.py).
4. Record donor provenance (phh/LineageOS build, open-source).

Status: PLAN ONLY — no donor downloaded yet (Q-18).

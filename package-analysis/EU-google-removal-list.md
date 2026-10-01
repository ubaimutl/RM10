# EU 11.0.5MR1 — Google removal list (static v1, 2026-10-01)

Source: firmware-manifests/EU-apk-inventory.tsv (574 APKs, aapt badging + apksigner certs).
Scope: privileged/system Google runtime + Google overlays + Google sysconfig.
User-facing Google apps (Chrome/Gmail/Maps/…) are trivially removable and listed separately at the end.

## A. Privileged Google core — REMOVE (26 APKs)

All in product/priv-app unless noted:

| Path | Package | Notes |
|------|---------|-------|
| product/priv-app/GmsCore/GmsCore.apk | com.google.android.gms | GMSCore — the core itself |
| product/priv-app/GmsCore/m/independent/AndroidPlatformServices/AndroidPlatformServices.apk | com.google.android.gms.policy_sidecar_aps | GMS sidecar |
| system_ext/priv-app/GoogleServicesFramework/GoogleServicesFramework.apk | com.google.android.gsf | GSF |
| product/priv-app/Phonesky/Phonesky.apk | com.android.vending | Play Store |
| system_ext/priv-app/SetupWizard/SetupWizard.apk | com.google.android.setupwizard | Google SUW (ZTE SetupWizard_MFV remains) |
| product/priv-app/GooglePartnerSetup/GooglePartnerSetup.apk | com.google.android.partnersetup | privileged setup integration |
| product/priv-app/GoogleOneTimeInitializer/GoogleOneTimeInitializer.apk | com.google.android.onetimeinitializer | first-boot init |
| product/priv-app/ConfigUpdater/ConfigUpdater.apk | com.google.android.configupdater | config OTA |
| product/priv-app/GoogleRestore/GoogleRestore.apk | com.google.android.apps.restore | restore flow |
| product/priv-app/SearchSelector/SearchSelector.apk | com.google.android.apps.setupwizard.searchselector | EEA search selector |
| product/priv-app/Velvet/Velvet.apk | com.google.android.googlequicksearchbox | system search |
| product/priv-app/AndroidSystemIntelligence/AndroidSystemIntelligence.apk | com.google.android.as | ASI |
| product/priv-app/PrivateComputeServices/PrivateComputeServices.apk | com.google.android.as.oss | PCS |
| product/priv-app/AndroidAutoStub/AndroidAutoStub.apk | com.google.android.projection.gearhead | Auto stub |
| product/priv-app/AndroidDeveloperVerifier/AndroidDeveloperVerifier.apk | com.google.android.verifier | verifier |
| product/priv-app/FamilyLinkParentalControls/FamilyLinkParentalControls.apk | com.google.android.gms.supervision | supervision |
| product/priv-app/PersonalSafety/PersonalSafety.apk | com.google.android.apps.safetyhub | safety |
| product/priv-app/Turbo/Turbo.apk | com.google.android.apps.turbo | device health |
| product/priv-app/Wellbeing/Wellbeing.apk | com.google.android.apps.wellbeing | wellbeing |
| product/priv-app/GoogleDialer/GoogleDialer.apk | com.google.android.dialer | dialer (needs AOSP/default replacement) |
| product/priv-app/Messages/Messages.apk | com.google.android.apps.messaging | SMS (needs replacement) |
| system_ext/priv-app/GoogleFeedback/GoogleFeedback.apk | com.google.android.feedback | feedback |
| system/system/priv-app/NetworkStackGoogle/NetworkStackGoogle.apk | com.google.android.networkstack | → replace with AOSP NetworkStack |
| system/system/priv-app/DocumentsUIGoogle/DocumentsUIGoogle.apk | com.google.android.documentsui | → replace with AOSP DocumentsUI |
| system/system/priv-app/GooglePackageInstaller/GooglePackageInstaller.apk | com.google.android.packageinstaller | → replace with AOSP PackageInstaller |
| system/system/priv-app/TagGoogle/TagGoogle.apk | com.google.android.tag | → replace with AOSP Tag |

## B. Google system apps (non-privileged) — REMOVE

system/system/app: GoogleExtShared, GooglePrintRecommendationService, GoogleWallet, CaptivePortalLoginGoogle (+7 dpi splits).
product/app (~30): CalculatorGoogle, CalendarGoogle, Chrome64, Drive, Gemini, Gmail2, GoogleContacts, GoogleLocationHistory, Keep, LatinImeGoogle, Maps, Meet, Photos, SpeechServicesByGoogle, SwitchAccess, talkback, TrichromeLibrary64, Videos, WebViewGoogle64 (→ needs AOSP WebView replacement!), YouTube, YTMusic, com.google.android.modulemetadata, com.google.mainline.adservices, com.google.mainline.telemetry.
system_ext/app: GmsEEAType4cIntegration.
product/priv-app note: ImsServiceEntitlement stays (carrier, non-Google).

## C. Google overlays — REMOVE (~15)

product/overlay: GmsConfigOverlay{ADVerifier,ASI,Common,Comms,Geotz,GSA_circletosearch,GSA_Gemini,PersonalSafety,Photos,SearchSelector}, GoogleDocumentsUIOverlay, GoogleExtServicesConfigOverlay, GoogleHealthFitnessFrameworkOverlay, GooglePermissionController{,Framework}Overlay, ModuleMetadataGoogleOverlay, CaptivePortalLoginFrameworkOverlay, UwbResCommonMainline_Sys, WifiResCommonMainline_Sys.
vendor/overlay: GoogleQuickSearchBoxOverlay, WifiResMainlineTarget.
system_ext/overlay: NetworkStackGoogleOverlay, TetheringResGoogleOverlay, WifiResOverlay, ConnectivityResOverlay.
KEEP: all ZTE/RedMagic RROs (incl. SetupWizard_MFV_REDMAGIC_rro — verify its target still exists after SUW removal; RROs targeting removed packages fail safe but log noise), all _Sys AOSP RROs.

## D. Config/metadata cleanup

- system/etc/permissions/privapp-permissions-google-system.xml (grants to removed pkgs — harmless if left, cleaner removed)
- system/etc/sysconfig/google-hiddenapi-package-allowlist.xml, com.google.android.mainline.patchlevel.2.xml
- product/etc/permissions/privapp-permissions-google-{product,comms-suite}.xml, com.google.android.dialer.support.xml, google_contacts_feature.xml, extphonelib_product.xml (review: extphonelib may be referenced by dialer replacement)
- system/etc/permissions/GoogleDocumentsUI_permissions.xml, GoogleNetworkStack_permissions.xml, google_lens_feature.xml, services.turbo.google.xml
- product care_map/apex_info consistency: APEX set is Mainline (com.google.android.* APEX are AOSP Mainline, KEEP).
- system/etc/sysconfig/preinstalled-packages-*.xml: no google entries found — nothing to do.
- init.rc: single GMS comment (OTA dir) — no init service removal needed. VERIFIED: no GMS init services.

## E. Replacements required (AOSP equivalents must be provided)

1. WebView (WebViewGoogle64/Trichrome) — AOSP WebView, else all hybrid apps break. CRITICAL.
2. NetworkStack, DocumentsUI, PackageInstaller, Tag — AOSP variants (standard AOSP modules).
3. Dialer + SMS defaults — AOSP Dialer/Messaging or ZTE defaults (Telecom_MFV + TeleService exist; check default-role holders post-removal).
4. Keyboard — ZBoard_Global is GMS-infused (ads/billing/gms); replace with AOSP LatinIME or keep-if-degraded (runtime test).
5. Location — com.qualcomm.location stays (vendor); FusedLocation (system/app) = Google NLP backend — remove, location falls back to GNSS/QC stack. VERIFY: Settings FLP client-lib usage degrades gracefully.
6. CaptivePortalLogin — AOSP CaptivePortalLogin (connectivity checks).
7. PlayAutoInstallConfig (android.autoinstalls.config.zte.NX789S_NEEA_W) — references NX789S_NEEA; remove or neutralize (auto-installs Play apps on setup).

## F. Deliberately KEPT (Google-signed Mainline infrastructure, not GMS)

com.google.android.* compressed APEX in system/apex (art, conscrypt, resolv, permission, media, etc.) — AOSP Mainline modules; removal would break the OS. They contain no accounts/ads/GMS APIs. Note: on stock they self-update via Play; in our build they stay frozen at shipped versions (document in test matrix: security-update story changes).

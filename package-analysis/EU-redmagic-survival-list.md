# EU 11.0.5MR1 — REDMAGIC survival list with static GMS verdicts (v1, 2026-10-01)

Method: scripts/20-gms-scan.py (strict Java-descriptor refs) over 104 ZTE/Nubia/RedMagic APKs
→ package-analysis/EU-redmagic-gms-scan.tsv. C=class refs, M=manifest permission refs.
"I:"/"P:" string columns are noisy (bundled conscrypt/cronet/photopicker libs) — verdicts below use C+M only.

## KEEP — GMS-clean at class+permission level (no action beyond keeping)

| Package | Path | Role |
|---------|------|------|
| cn.nubia.gamelauncher | system/priv-app/GameSpace | Game Space UI |
| cn.nubia.gamepi | system/priv-app/GamePi | performance/game profiles |
| cn.nubia.keymapcenter | system/priv-app/KeyMapCenter_magic | trigger mapping |
| cn.nubia.fan | system/priv-app/NBFan | fan UI |
| cn.nubia.touping | system/priv-app/NubiaProjectionScreen | projection/desktop |
| cn.nubia.virtualgamehandle | system/priv-app/VirtualGameHandle | virtual gamepad |
| cn.zte.chargeseparation | system/priv-app/ChargeSeparation | bypass charging |
| cn.nubia.colorfullight | system/app/ColorFulLight | RGB (app side; vendor daemons stay) |
| cn.zte.gamefloat | system/app/GameFloatWindow | in-game overlay |
| com.zte.game.plugintrigger | system/app/GamePluginTrigger | trigger plugin |
| com.zte.gamecardassist | system/app/GameCardAssist | game cards |
| cn.nubia.gameassist — SEE DIRTY | system/app/GameAssist | assist (has sign-in/MLKit) |
| cn.nubia.gamehelperline/gamehelpmodule/gamehighlights/gamelab/gamenotes/gamepad/gamewidget/magicelvesbroadcast | system/app/* | game ecosystem |
| com.zte.mifavor.launcher(.adapter/.resource) | system_ext/priv-app + system | launcher stack |
| com.android.systemui (MFV) | system_ext/priv-app/SystemUI_MFV | system UI (only Nearby-Share tile + MLKit proxy STRINGS, no class refs) |
| com.android.settings (MFV) — SEE DIRTY | system_ext/priv-app/Settings_MFV_abroad | settings (sign-in + FLP client lib) |
| com.android.providers.settings (MFV) | system/priv-app/SettingsProvider_MFV | settings provider |
| com.android.server.telecom (MFV) | system/priv-app/Telecom_MFV | telecom |
| com.android.camera (NubiaCamera) | system/priv-app/NubiaCamera | camera |
| com.ztefingerprint.service + com.fingerprint.sensorservice + com.zte.fingerprints + com.zte.faceverify | system/priv-app/* | biometrics (vendor ztecmdaidl-service stays in vendor) |
| com.zte.setupwizard | system/priv-app/SetupWizard_MFV | provisioning (uses READ/WRITE_GSETTINGS perms — GSF-defined; harmless unknown-perm after GSF removal, function to re-test) |
| com.zte.distservice.servicemanager | system/priv-app/ServiceManager | ZTE service fabric |
| com.zte.thermalbridge / com.zte.thermald | system/priv-app + system_ext | thermal |
| com.zte.powersavemode | system/priv-app/PowerSaveMode_ZTE | power profiles |
| com.zte.toolsmanager | system_ext/priv-app/ToolsManager | tools |
| com.zte.nook.modem | system_ext/priv-app/NookModemService | modem service |
| com.zte.mifavor.globalzboard — SEE DIRTY | system/priv-app/ZBoard_Global | keyboard (heavy GMS) |
| com.zte.zsound | system/app/ZSound | audio effects |
| com.zte.emode/flagreset/linkspeedup/storagecleanup(→dirty)/mipop/floatassist/recommend | various | utilities (storagecleanup dirty) |
| com.zte.weather(→dirty)/nubrowser(→dirty)/booking(→dirty) | various | replaceable |
| cn.nubia.*wallpaper*(→dirty-ish) | priv-app | wallpapers (firebase/gservices refs; replaceable) |
| com.zte.aigc(→dirty) | system/priv-app/ZteAigc_abroad | AI features (sign-in) |
| com.zte.xr.gamelauncher(→minor) | system/app/XRLauncher | XR (play-asset refs) |
| com.zte.onemorething/onekeycp/zbackup/zswitch/zdmdaemon×2/dm_mfv/otap/saleinfocollect/radarpermission/vendorlogpermission/wlansniffer/cameraBurn | various | system infra — KEEP but audit zdm/saleinfocollect (DM/telemetry) separately from Google-free goal |
| com.zte.vendor.ifaa (AlipayService) + com.zte.fingerflashpay | system/priv-app | payment biometrics (CN-stack remnants in EU build; keep, non-Google) |
| EMode, FaceVerify, SoterService, ONS, ThermalBridge | various | security/thermal |

## DIRTY — GMS-integrated (replace, remove, or runtime-test degraded mode)

| Package | GMS surface | Disposition |
|---------|-------------|-------------|
| com.zte.mifavor.globalzboard (ZBoard) | ads+billing+firebase+gms(8608)+play-core; AD_ID+finsky perms | REPLACE with AOSP keyboard (privileged IME swap; verify default-IME fallback) |
| com.zte.nubrowser | ads+firebase+gms; AD_ID/finsky/c2dm | REMOVE (replace with any browser) |
| com.zte.weather | billing+firebase+gms; AD_ID | REMOVE (replaceable) |
| com.zte.storagecleanup | ads+firebase+gms; AD_ID | REMOVE (utility) |
| com.booking (NubiaBooking, partner-app) | finsky+firebase+gms/play-core | REMOVE (partner bloat) |
| com.zte.gallerylockscreen + cn.nubia.inspiredwallpaper + RedMagicWallPaper | firebase/gms + AD_ID/finsky | REMOVE or keep-if-degraded (wallpaper; runtime test) |
| cn.nubia.gameassist (GameAssist) | Google Sign-In + MLKit text + photopicker; NO gms perms | RUNTIME-TEST: sign-in-gated paths must fail safe; MLKit on-device works w/o GMS (verify). Non-priv → removable fallback |
| com.android.settings (Settings_MFV) | Google Sign-In + FusedLocation client lib + photopicker | RUNTIME-TEST (privileged, cannot remove): exercise location/sign-in settings pages without GMS; expect ApiException-guarded degradation |
| com.zte.aigc (ZteAigc) | Google Sign-In (269 auth refs) | RUNTIME-TEST: AI login fails safe; core features TBD |
| com.zte.xr.gamelauncher | play-asset(7) | RUNTIME-TEST: XR content install fails safe |
| cn.nubia.redmagickyi | photopicker strings only → effectively CLEAN | KEEP |

## Privileged-but-keep ZTE infra (no GMS, audit separately for privacy, NOT Google)

zdmDaemon_common/install (device management), SaleInfoCollectSystem (telemetry), dm_mfv, OTAP_stockplus, soter, ONS, WlanSnifferTool — outside the Google-free goal; document, do not bundle into v1 removal.

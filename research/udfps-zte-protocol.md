# ZTE UDFPS protocol (NX789J) — extracted from ZteFodDaemon

Source: `sources/redmagic-10-pro-udfps-fix/bin/ZteFodDaemon.dex`, decompiled with jadx 2026-10-01.
Upstream: https://github.com/sequencode/redmagic-10-pro-udfps-fix
Status: VERIFIED (decompiled primary artifact). NX789J-native. Event-node index + geometry must be re-verified against EU stock.

## 1. Binder endpoints

| Role | Descriptor |
|------|------------|
| Fingerprint service | `android.hardware.biometrics.fingerprint.IFingerprint/default` (via ServiceManager, polled ≤30 s) |
| Vendor extension | `IBinder.getExtension()` on the above → `vendor.zte.fingerprint.ztecmdaidl.IZtecmdDaemon` |
| Callback | `vendor.zte.fingerprint.ztecmdaidl.IZtecmdCallback` (Binder `Cb`, TXN HASH=16777213→"notfrozen", VERSION=16777214→1) |

Transactions on `IZtecmdDaemon`: `setNotify(1, Cb)` = TXN 1; `zteCmd(cmd, a1, a2, "")` = TXN 2 (three ints + empty string).

## 2. Capture handshake (cmd10 family)

- Wake: `zteCmd(10, 1, 0)` then `zteCmd(21, 1, 0)`.
- Sustain loop while overlay-present && finger-down:
  `zteCmd(22,1,0)` → sleep 330 ms → `zteCmd(22,0,0)` → re-check → `zteCmd(10,0,0)` → 90 ms →
  re-check → `zteCmd(10,1,0)` + `zteCmd(21,1,0)` → 60 ms → repeat (log every 5th).
- Release: `zteCmd(21,0,0)` + `zteCmd(10,0,0)`.
- HAL death: `DeadObjectException` → `extDead=true` → watchdog thread re-runs `acquireExt()` every 200 ms.

## 3. Finger presence detection (input layer)

- Node: `/dev/input/event7` (raw 24-byte input_event structs parsed in Java).
- Keys: `EV_KEY(1)`, `BTN_TOUCH=330`, `BTN_TOOL_FINGER=325`. Down = position inside FOD circle at key-press; up clears `rawDown`, stamps `lastUpMs` (200 ms grace).
- Axes: `EV_ABS(3)`, `ABS_MT_POSITION_X=53`, `ABS_MT_POSITION_Y=54` (fallbacks 0/1).
- Scaling: raw abs-max X=19455, Y=43007 → display 1216×2688; FOD center (608,2024), radius² threshold 22500 (r=150 touch gate) with optical circle r=95 px drawn.

## 4. Illumination (HBM + overlay)

- HBM node: `/proc/driver/lcd_hbm` ("1"/"0"); keeper thread re-asserts every 10 ms while `hbmKeep&&maskReady`, forces 0 while layer shown-but-idle or within 700 ms post-hide (anti-stuck + anti-flash suppressor).
- Overlay: `SurfaceControl "ZteFodLight"`, buffer 1216×2688, format -3 (TRANSLUCENT), layer `Integer.MAX_VALUE`, layerStack 0, `setTrustedOverlay(true)` (keyguard stays touchable), initial hidden.
- Mask: full-screen `Color.argb(alpha,0,0,0)` CLEAR-punched white circle at (608,2024,r=95). Alpha adaptive: `255 − brightness/maxBacklight × K`, K=175 default (argv[0] tunable), clamped [70,215]; brightness from `/sys/class/backlight/panel0-backlight/brightness`, max from `.../max_brightness` (default 4095).
- Timing: show → redraw mask → +32 ms → `maskReady=true`, `hbmKeep=true`, `writeHbm(1)`. Hide → `writeHbm(0)`, transparent redraw, 700 ms suppress window.

## 5. Framework hooks the daemon relies on

- Overlay detection: `dumpsys SurfaceFlinger --list | grep -c UdfpsControllerOverlay` (>0 = fodUiPresent, 2 consecutive misses = gone, polled 250 ms).
- `virtual_sensors_are_real=1` (`persist.sys.phh.virtual_sensors_are_real` via resetprop, post-fs-data) so framework uses native capture trigger.
- Refresh lock: `settings put system peak_refresh_rate 60 + min_refresh_rate 60` during scan; restore user values after (userPeak/userMin polled every 1.5 s when not boosted).
- SELinux: `allow tee unlabeled dir/file {search open read …}` (module sepolicy.rule).

## 6. What a proper ROM integration needs (no root daemon)

1. Framework UDFPS overlay trigger wired to native path (equivalent of virtual_sensors_are_real) for Goodix/ZTE stack.
2. System-side `IZtecmdDaemon` client issuing the cmd10/21/22 sequence driven by overlay + touch state (replacing app_process daemon + event7 polling; ideally in fingerprint HAL extension or SystemUI/UDFPS controller).
3. HBM control via `lcd_hbm` tied to overlay lifecycle with the same anti-flash/anti-stuck guards.
4. Trusted overlay with adaptive dim mask + sensor hole at (608,2024,r=95) — coordinates MUST be re-derived from EU stock overlay config (see Q-14).
5. 60 Hz clamp during scan with restore.
6. SELinux policy for the new client (binder to IFingerprint extension, input, HBM proc node, backlight sysfs).
7. Verify Goodix HAL identity on EU build (`vendor.goodix.hardware.biometrics.fingerprint` version, `ZteFod`/goodix fingerprint service names) — Phase 4 manifest work.

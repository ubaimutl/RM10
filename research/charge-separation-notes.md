# Charge separation / bypass charging — stock mechanism (static, 2026-10-01)

App: `cn.zte.chargeseparation` (system/priv-app/ChargeSeparation, GMS-clean).
Components: ChargeSeparationApplication/Service/Controller/Activity/Dialog/Receiver + QS tile
(ic_qs_charge_separation_*), threshold seekbar UI.

## Settings keys (the control plane)

- `charge_separation_switch` — master toggle
- `charge_separation_settings_flag`, `charge_separation_function_flag` — feature state
- `charge_separation_threshold` — battery % threshold (seekbar)
- `charge_separation_auto_switch`, `charge_separation_auto_turn_off` — automation
- `battery_limit_timeout` — limit timer

No /sys or /proc paths found in the app dex → the app writes Settings only.
Actuation (Settings → charger hardware) lives downstream: either a vendor
daemon observing the Settings URI (ObserverManager/ContentObserver pattern
present in-app) or kernel/power-HAL policy. CANDIDATES to inspect next:
vendor/bin/poweropt-service, thermal-engine, battery_record_daemon,
vendor/etc/init/*.rc referencing these keys, kernel zte_charger_policy
(source in NX789S tarball), power_supply sysfs (input_suspend/battery_charging_enabled).

## Diagram (current)

ChargeSeparation UI/QS → Settings.Global keys above → (consumer TBD: vendor daemon or kernel policy) → charger IC

## Implication for Google-free ROM

Control plane is AOSP Settings + ZTE app — no GMS in the chain (static).
Keep app + SettingsProvider_MFV + vendor power stack; verify consumer reads
keys without GMS (no reason to suspect otherwise). Runtime test: toggle +
measure charge current.

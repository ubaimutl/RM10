# TEST MATRIX (candidate-build acceptance)

A build is a CANDIDATE until every applicable row passes on real EU/global NX789J hardware.
No hardware testing is authorized yet; this matrix is the definition of done for Phase 10.

## BOOT
- [ ] Cold boot to launcher, no crash loops (logcat clean of GMS-missing FATALs)
- [ ] Reboot (warm) stable across 5 cycles
- [ ] FBE decryption + lockscreen (PIN/password) enroll + unlock
- [ ] No SetupWizard stall without Google account (AOSP provisioning path works)

## DISPLAY
- [ ] Native 2688×1216
- [ ] 60/90/120/144 Hz switching (peak/min_refresh_rate honored)
- [ ] Brightness + auto-brightness
- [ ] UDFPS HBM illumination does not corrupt display state

## REDMAGIC
- [ ] Game Space launches, game detection works
- [ ] Shoulder triggers: mapping UI, in-game tap mapping, latency acceptable
- [ ] Fan manual + automatic modes (RPM readback)
- [ ] RGB/logo/shoulder/fan LEDs
- [ ] Performance modes switch (power HAL profiles)
- [ ] Game overlay (slide-in) functional
- [ ] Charge separation / bypass charging toggle + verified current behavior

## PHONE
- [ ] SIM detection, LTE, 5G, mobile data, SMS
- [ ] Incoming + outgoing call audio (earpiece/mic), VoLTE per stock support
- [ ] Wi-Fi calling only if stock EU supports it (document, don't regress)

## CONNECTIVITY
- [ ] Wi-Fi connect + throughput; Bluetooth pair + A2DP + HFP/mic
- [ ] NFC detect + transaction path present
- [ ] USB MTP/ADB; USB-C display output (projection/desktop where stock has it)

## AUDIO
- [ ] Speaker, earpiece, microphones, in-call routing (audioserver + vendor ext present)

## SECURITY/HARDWARE
- [ ] Fingerprint enroll + unlock (incl. low brightness), sensors (accel/gyro/als/mag)

## MEDIA
- [ ] Front/back camera photo + video; hardware decode; DRM status DOCUMENTED (expected: Widevine L3 after unlock — must be disclosed, not hidden)

## REDMAGIC EXTRAS
- [ ] Projection/desktop mode, external display, gamepad/controller support

## GOOGLE-FREE VALIDATION
- [ ] No privileged Google packages in built images (manifest scan)
- [ ] No boot/framework hard dependency on GMS (dependency graph clean)
- [ ] No persistent GMS-missing crash loops (logcat audit 15 min post-boot)
- [ ] All REDMAGIC features above work with no Google account and no microG
- [ ] Network audit: clean-boot capture, DNS/TLS endpoints classified (Google/ZTE/Qualcomm/infra/NTP/captive-portal/unknown); no privileged-Google system traffic

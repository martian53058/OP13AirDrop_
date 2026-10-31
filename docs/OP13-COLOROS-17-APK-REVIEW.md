# OP13 ColorOS 17 target APK review

Date: 2026-10-31
Target reported by the owner: PJZ110 / OP5D0DL1, ColorOS 17.0.0.103, Android 17 (SDK 37), KernelSU, kernel 6.6.118-android15-8-g9bc34d5b0c79-abogki537459655-4k.

This report records static inspection of two APK inputs supplied in chat. No APK binaries are committed to this repository, and no phone diagnostics or device operations were performed.

## Supplied inputs

| Input | Size | SHA256 |
|---|---:|---|
| `一加互传_17.2.45.apk` | 26,172,227 bytes | `ec389c5532db3f7124e83faa3bf060db9f41195730074e5fbf7fcd1f0d591dde` |
| `Quick Share extension_1.0.980159239.apks` | 3,356,236 bytes | `7806f096c2bff7bd7c9db283d6fd477a9a55a5dd139e32794d97fdc4b723365d` |

## OShare 17.2.45

Manifest inspection:

- Package: `com.coloros.oshare`
- Version: `17.2.45`
- Version code: `17002045`
- Target SDK: 37
- Four DEX files.

Static DEX evidence confirms the major OShare resolver anchors:

| Role | Observed target |
|---|---|
| OShare application | `com.oplus.oshare.OShareApplication` |
| Device adapter | `com.oplus.oshare.ui.DeviceAdapter` |
| Device extension | `Lv9/d;` |
| Device wrapper | `Ll9/b;` |
| Oplus device API | `com.oplus.oshare.OplusOshareDevice` in `classes3.dex` |
| Color device API | `com.color.oshare.ColorOshareDevice` in `classes.dex` |
| Oplus state enum | `com.oplus.oshare.OplusOshareState` in `classes3.dex` |
| Device manager | `Lv9/a;` |
| Share activity | `com.oplus.oshare.ui.ShareActivity` |
| Send service | `com.oplus.oshare.OShareClient$6` |
| Direct Share server | `com.oplus.oshare.ui.direct.DirectShareServer` |
| Receive activity | `com.oplus.oshare.ui.ReceiveDialogActivity` |

The wrapper has constructors for both `OplusOshareDevice` and `ColorOshareDevice`. The Oplus device API methods and Oplus state enum expected by the base resolver are present. The receive resolver's semantic anchors are also present: `ReceiveDialogActivity.S0(Intent): void`, and `k1(Context, String, int, String, String, String): Dialog`; the latter invokes the expected COUI builder constructor `(Context, int)`.

The Direct Share resolver exposed one concrete incompatibility:

- In this APK, `DirectShareServer.T(int, List, callback): void` invokes `DirectShareServer.H(List, boolean): List`.
- The previous resolver accepted only `H(List): List`.
- The Chooser bridge only consumes the returned list and does not depend on the extra boolean argument.

The source has been updated to accept exactly these two known filter contracts while retaining strict declaring-class, return-type, and parameter checks. The resolver test's baseline assertion now accepts either descriptor.

Static DEX inspection is not equivalent to running DexKit against the APK on Android. The exact APK has not yet been passed through the Android DexKit harness, and OShare hooks have not been runtime-tested on the phone.

## Mosey 60715 bundle and 15-split adaptation

The owner confirmed that `Quick Share extension_1.0.980159239.apks` was exported from the phone while no module was active. The archive contains 15 APKs (one base plus 14 configuration/ABI splits).

- Base APK SHA256: `7ab2deaea6c9c2bdd5ba0f935d6143c115f5ceb11cb8b63066496ad27a28da49`.
- This exactly matches `BASE_SHA` in `mosey/callback/build.py`.
- All 14 split hashes were verified against the uploaded archive and added to `module/APP-SHA256SUMS`.

The earlier live-package hash `54dd7fb3...` differs from the clean archive base. It was obtained at a different time/view; a previously mounted callback APK is one possible explanation, but that cannot be proven from the hash alone. The clean 7ab2 archive is now the callback source of truth. The callback builder's SHA and Smali checks remain enabled.

The six-entry split-count assumption has been removed from the packaging path by making the target's full 15-APK set explicit:

- `tools/mosey_apks.py` validates the archive's exact APK basename set and every SHA256 before staging files.
- `tools/package-coex.py` now requires `--mosey-apks`, stages all 15 original APKs under `system/system_ext/priv-app/MoseyApp`, and extends `APP-CALLBACK-SHA256SUMS` with the 14 unchanged split hashes while preserving the patched base hash.
- `tools/check-coex.py` checks the original and callback manifests against the staged APKs.
- Six new host tests cover extraction, stale split removal, missing/extra/duplicate APKs, hash mismatch, and callback-manifest extension.

This fixes the repository's known six-versus-fifteen split packaging mismatch. It does not by itself prove that the callback patch runs correctly inside Mosey on Android.

## Uploaded WLAN module analysis

The two uploaded files match the paths previously reported under `/vendor/lib/modules`. They are valid ARM64 ELF relocatable kernel modules with modversion CRC sections.

| Module | Size | `vermagic` | GNU build ID | Imported CRC records |
|---|---:|---|---|---:|
| `qca_cld3_peach_v2.ko` | 19,736,456 bytes | `6.6.118-android15-8-o-4k` | `ec9df3687e6f223b8a92eeaa7f188ef526255f2c` | 588 |
| `mac80211.ko` | 1,963,888 bytes | `6.6.118-android15-8-o-g1524d9b076be-4k` | `6bba56348fcdd70c10131c7da6cb1f71fb1bd8ab` | 317 |

The two modules have 173 shared symbol-version entries, and all 173 CRCs agree. Their modversion flags are also the same: `SMP preempt mod_unload modversions aarch64`.

Their embedded release prefixes differ from the phone's reported `uname -r`, but this alone is not a rejection condition for a modversions-enabled module. In the public OnePlus SM8750 common-kernel source, `same_magic()` skips the release prefix when CRCs are present and compares the remaining vermagic flags; the loader then checks imported symbol CRCs against the running kernel. This behavior is visible in the official source branch for PJZ110 15.0.0.851:

- [OnePlus common-kernel module/version.c](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750/blob/oneplus/sm8750_v_15.0.0_oneplus_13/kernel/module/version.c)
- [PJZ110 15.0.0.851 common-kernel commit](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750/commit/9920459dfb0080dd8a81c41d95701483857f804a)

This is useful ABI evidence, but it is not a substitute for the target kernel's own `Module.symvers`. The 173 shared CRCs only establish agreement between the two uploaded modules, not agreement with the running kernel's full export table.

The uploaded module build IDs also differ from the stock-module IDs recorded in the old repository snapshot:

- Old snapshot QCA ID: `f9b56d574a80d18b2b93f44817ac44ddd4753f24`.
- Uploaded QCA ID: `ec9df3687e6f223b8a92eeaa7f188ef526255f2c`.
- Old snapshot mac80211 ID: `06b950ed78a4206dd03433f563067448057b4925`.
- Uploaded mac80211 ID: `6bba56348fcdd70c10131c7da6cb1f71fb1bd8ab`.

Therefore the old captured kernel payload must not be assumed to be a bit-for-bit match for this phone. The uploaded original modules are useful target references; rebuilding the custom Wonder/WLAN modules still requires the exact kernel build inputs and ABI comparison.

## Kernel source status

The public official OnePlus source I could verify includes:

- [SM8750 common kernel, PJZ110 15.0.0.851 branch](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750/tree/oneplus/sm8750_v_15.0.0_oneplus_13).
- [SM8750 modules/device-tree, PJZ110 15.0.0.851 branch](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/tree/oneplus/sm8750_v_15.0.0_oneplus_13).
- [SM8750 Android 16 / OnePlus 13 branch](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750/tree/oneplus/sm8750_b_16.0.0_oneplus_13).

The PJZ110 15.0.0.851 source is a useful device-specific reference; the Android 16 branch is a newer nearby reference. Neither has been verified as the exact source for the reported ColorOS 17.0.0.103 build fingerprint `V.487427a-2227f32-224bc4c` and kernel release `6.6.118-android15-8-g9bc34d5b0c79-abogki537459655-4k`. I will not silently substitute either branch for the exact .103 source.

## Remaining required inputs

Already received:

- Clean Mosey60715 APKS bundle with all 15 APKs.
- OShare 17.2.45 APK.
- Original `qca_cld3_peach_v2.ko`.
- Original `mac80211.ko`.

Still needed:

1. `/system_ext/bin/mosey_server`.
2. `/system_ext/lib64/libmosey_daemon_ffi.so`.
3. The exact .103 kernel source branch/archive and its matching generated `.config` and `Module.symvers`.

For the two Mosey native files, use a root-capable file manager and navigate directly to the paths above. If the file manager cannot see `/system_ext`, try its equivalent `/system/system_ext` path or search the root filesystem for the exact filenames. These files are proprietary system components and are not part of the public kernel source.

`.config` may be available as `/proc/config.gz` if the kernel exposes IKCONFIG_PROC; this is a file to copy, not a command to run. `Module.symvers` is normally generated in the kernel build directory and is not usually installed on the phone. If you do not have it, provide the exact source URL/branch and build configuration, or the matching firmware's kernel build artifacts. The old snapshot archive `local-inputs/coex/module.tar` and installer base ZIP are also not present in the public repository; upload them if you still have those local build inputs.

## Current status

- OShare 17.2.45: static DEX anchors inspected; the chooser resolver now supports the exact `List, boolean` filter contract as well as the older `List` contract.
- Mosey60715: clean base matches the callback builder; all 15 APK hashes are now recorded and the package builder accepts the complete APKS archive.
- WLAN: both original modules inspected; 173 shared CRCs agree, but target-kernel CRC verification remains outstanding.
- Kernel source: two Wonder source defects and WLAN rollback preflight guards are fixed on the adaptation branch; custom modules have not been rebuilt for .103.
- Device: untouched. No module has been installed, flashed, or tested on the phone.

## Host validation completed

ActionAgent run [41205930830](https://github.com/martian53058/OP13AirDrop_/actions/runs/41205930830) completed successfully on 2026-10-31.

- Repository/static checks passed (345 files).
- All 159 Python tests passed, including six new Mosey APKS packaging tests.
- `oshare/tests/run.sh` passed all resolver-adjacent, send, receive, chooser, callback, and state-machine regressions.
- WebUI dependency install, API tests, refresh tests, TypeScript check, and Vite production build passed.
- The LSPosed helper JAR built successfully.
- The OShare Android Java sources compiled successfully with Gradle 8.13, JDK 17, compile SDK 36, and a validation-only target SDK 36 override.

The app's checked-in defaults remain compile SDK 37 and target SDK 37. The CI runner did not expose an Android 37 platform package, so this successful host compile is not a claim that the API 37 configuration was compiled. It also did not build/sign a release APK, run DexKit against the supplied APK on Android, or install/test on a phone.

The WebUI dependency audit reported three high-severity npm advisories; no automatic dependency upgrades were applied.

The workflow's optional issue-comment step received HTTP 410 because Issues are disabled for this repository. This did not affect ActionAgent execution, its successful result, or artifact upload.

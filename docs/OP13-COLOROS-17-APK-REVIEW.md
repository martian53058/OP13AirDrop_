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

## Mosey 60715 bundle

The APKS archive contains 15 APKs: one base plus 14 splits. Its base APK has SHA256:

`7ab2deaea6c9c2bdd5ba0f935d6143c115f5ceb11cb8b63066496ad27a28da49`

This is exactly the `BASE_SHA` pinned by `mosey/callback/build.py` and the `base.apk` hash currently in `module/APP-SHA256SUMS`.

The 14 split APK hashes match the earlier device-provided SHA256 output, including the nine additional configuration splits not present in the repository's six-entry `APP-SHA256SUMS` manifest. The extra splits are resource configuration APKs; the arm64 split carries `liblivephoto_puller_jni.so`.

There is still a material base-APK discrepancy:

- Supplied APKS bundle base: `7ab2de...`
- Earlier installed active `/data/app/.../base.apk` hash from the owner's output: `54dd7fb3...`

The repository's `app-check.sh` requires the active split count to equal the six entries in `APP-SHA256SUMS`, so it rejects the reported 15-path active package. More importantly, the callback builder is pinned to the supplied 7ab2de base and exact smali hashes. Do not merely replace `BASE_SHA` or remove those checks.

The next required input is the exact installed active Mosey `base.apk` from the path previously shown by the owner:

`/data/app/~~IzXVk4J4Z4S-Z2wiugm9-Q==/com.google.android.mosey-K5m8Rt5i9Gi_S1sVMQd4iw==/base.apk`

Copy that file with a root-capable file manager and upload it. No command or diagnostic script is needed. The supplied APKS base can serve as the known 7ab2de reference; after receiving the active base, compare its DEX payload with that reference before choosing whether one patched base can safely serve both the system and active APK mount points or whether two patched payloads are required.

The system image APK at `/system_ext/priv-app/MoseyApp/base.apk` should also be copied if it is not byte-identical to the supplied 7ab2de base. This avoids assuming the system and active package bases are the same build.

## Kernel source status

The official OnePlusOSS SM8750 kernel modules/device-tree repository currently exposes the Android 16 / 16.0.9.401 branch, not a verified source snapshot for the reported ColorOS 17.0.0.103 fingerprint. The common-kernel repository likewise does not currently provide a confirmed matching .103 branch in its public branch list.

- [Official OnePlusOSS SM8750 modules and device tree](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750)
- [Official OnePlusOSS SM8750 common kernel](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750)

The .401 tree is a useful nearby reference for the 6.6.118 family, but it must not be represented as an exact match for the owner's `V.487427a-2227f32-224bc4c` build. Before rebuilding or replacing WLAN modules, obtain the target device's original modules and compare their vermagic, symbol CRCs, exported symbols, and ABI against the build inputs.

## Next required files

Please copy these files with a root-capable file manager and upload them here:

1. Active Mosey base APK:
   `/data/app/~~IzXVk4J4Z4S-Z2wiugm9-Q==/com.google.android.mosey-K5m8Rt5i9Gi_S1sVMQd4iw==/base.apk`
2. System Mosey base APK, only if it differs from the supplied APKS base:
   `/system_ext/priv-app/MoseyApp/base.apk`
3. Original WLAN modules:
   `/vendor/lib/modules/qca_cld3_peach_v2.ko`
   `/vendor/lib/modules/mac80211.ko`
4. Mosey native service files:
   `/system_ext/bin/mosey_server`
   `/system_ext/lib64/libmosey_daemon_ffi.so`

If the exact .103 kernel source archive is available, also provide its matching `.config` and `Module.symvers`. The official .401 source is not a substitute for those exact build artifacts.

## Current status

- OShare 17.2.45: static anchors inspected; chooser filter signature adaptation committed.
- Mosey: supplied bundle base matches the repository's old callback input, but not the active base hash previously reported by the owner.
- Kernel: two source-level Wonder fixes and preflight/rollback guards are committed on the adaptation branch; target ABI has not been verified.
- Device: untouched. No module has been installed, flashed, or tested on the phone.


## Host validation completed

ActionAgent run [41202312350](https://github.com/martian53058/OP13AirDrop_/actions/runs/41202312350) completed successfully on 2026-10-31.

- Repository/static checks passed (345 files).
- All 153 Python tests passed.
- `oshare/tests/run.sh` passed all resolver-adjacent, send, receive, chooser, callback, and state-machine regressions.
- WebUI dependency install, API tests, refresh tests, TypeScript check, and Vite production build passed.
- The LSPosed helper JAR built successfully.
- The OShare Android Java sources compiled successfully with Gradle 8.13, JDK 17, compile SDK 36, and a validation-only target SDK 36 override.

The app's checked-in defaults remain compile SDK 37 and target SDK 37. The CI runner did not expose an Android 37 platform package, so this successful host compile is not a claim that the API 37 configuration was compiled. It also did not build/sign a release APK, run DexKit against the supplied APK on Android, or install/test on a phone.

The WebUI dependency audit reported three high-severity npm advisories; no automatic dependency upgrades were applied.

The workflow's optional issue-comment step received HTTP 410 because Issues are disabled for this repository. This did not affect ActionAgent execution, its successful result, or artifact upload. Enabling Actions write permissions alone does not enable the repository's Issues feature.

"""
run = true
name = "ColorOS 17 full source regression and component build"
reason = "Run all host regressions and build every source-controlled userspace component using the pinned Android 17 toolchain"
timeout = 1800
priority = 10

[commands]
before = [
  "python3 tools/build-lsposed.py --sdk \"$ANDROID_HOME\"",
  "python3 tools/build-native.py --sdk \"$ANDROID_HOME\" --ndk \"$ANDROID_NDK_HOME\""
]
run = [
  "python3 tools/check.py",
  "python3 -m unittest discover -s tests -p 'test_*.py' -v",
  "sh oshare/tests/run.sh",
  "cd webui && npm ci",
  "node tests/test-api.mjs",
  "node tests/test-webui-refresh.mjs",
  "cd webui && npm run check && npm run build",
  "oshare/gradlew -p oshare --no-daemon :app:compileReleaseJavaWithJavac :app:processReleaseResources"
]
after = []

[output]
mode = "both"
path = ".action-agent/output/coloros-17-full-validation.log"
artifact = true
commit = false

[execution]
cwd = "."
shell = "bash"
continue_on_error = false
reset_on = "always"
after = "always"
"""

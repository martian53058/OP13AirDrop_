"""
run = true
name = "Final source validation after WebUI dependency repair"
reason = "Re-run the complete host regression suite and build all source-controlled userspace components after the verified dependency lockfile update"
timeout = 1800
priority = 10

[commands]
before = [
  "python3 tools/build-lsposed.py --sdk \"$ANDROID_HOME\"",
  "python3 tools/build-native.py --sdk \"$ANDROID_HOME\" --ndk \"$ANDROID_NDK_HOME\""
]
run = [
  "python3 .action-agent/tasks/release-input-audit.py",
  "python3 tools/check.py",
  "python3 -m unittest discover -s tests -p 'test_*.py' -v",
  "sh oshare/tests/run.sh",
  "cd webui && npm ci --no-fund",
  "cd webui && npm audit --audit-level=high",
  "node tests/test-api.mjs",
  "node tests/test-webui-refresh.mjs",
  "cd webui && npm run check && npm run build",
  "oshare/gradlew -p oshare --no-daemon :app:compileReleaseJavaWithJavac :app:processReleaseResources"
]
after = [
  "mkdir -p .action-agent/output/build-artifacts/native .action-agent/output/build-artifacts/lsposed",
  "cp -a build/native/. .action-agent/output/build-artifacts/native/",
  "cp build/lsposed/lsposed-setup.jar .action-agent/output/build-artifacts/lsposed/"
]

[output]
mode = "both"
path = ".action-agent/output/final-source-validation.log"
artifact = true
commit = false

[execution]
cwd = "."
shell = "bash"
continue_on_error = false
reset_on = "always"
after = "always"
"""

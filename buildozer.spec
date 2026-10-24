# =============================================================================
# J.A.R.V.I.S. Mk.II — Buildozer Specification (Android APK)
# =============================================================================

[app]

# Title / application name
title = JARVIS Mk.II
package.name = jarvis
package.domain = com.stark.enterprise

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml
source.exclude_exts = spec,pyc,db,env,log,sh,ps1,conf,service,yml,html,md,gitignore
source.exclude_dirs = tests, bin, venv, __pycache__, .git, dashboard, node_modules

# Versioning
version = 2.0.0
version.code = 2

# Requirements (cryptography included for E2EE)
requirements = python3,kivy,websockets,cryptography

# Android permissions
android.permissions = INTERNET,WAKE_LOCK,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,USE_FINGERPRINT,BIOMETRIC,POST_NOTIFICATIONS,CAMERA,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# Android API levels
android.api = 34
android.minapi = 24

# Window / orientation
android.window = true
android.orientation = portrait

# Services & background
android.wakelock = True
android.foreground_service = True
android.foreground_service_type = dataSync|mediaProjection
android.service = android_client/main.py
android.entrypoint = android_client/main.py

# Icon & branding
android.icons = android/res/mipmap-anydpi-v26/ic_launcher.xml
android.launcher_name = JARVIS Mk.II

# Splash screen
android.splash_screen = android/res/drawable/splash.xml

# App shortcuts (launcher quick actions)
android.shortcuts = android/res/values/shortcuts.xml

# Proguard / multidex
android.multidex = True
android.add_implementation = androidx.multidex:multidex:2.0.1

# Logs
log_level = 2

# P4A branch
p4a.branch = develop

[buildozer]

# Build log
log_level = 2

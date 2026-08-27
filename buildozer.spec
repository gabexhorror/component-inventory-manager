[app]
title = Component Inventory
package.name = componentinventory
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy==2.2.1
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.entrypoint = main.py
android.permissions = INTERNET
android.private_storage = True

[buildozer]
log_level = 2
warn_on_root = 1
Flatpak build/publish steps

##### Dependencies
- appstream-util
- flatpak-builder

Build warpinator.

##### Check appdata file
```
appstream-util validate-relax obj-x86_64-linux-gnu/data/org.x.Warpinator.appdata.xml
```

##### Check desktop file
```
desktop-file-validate obj-x86_64-linux-gnu/data/org.x.Warpinator.desktop
```

##### Build & Test

Switch to your clone of `https://github.com/flathub/org.x.Warpinator.git`

Install sdk and platform (currently 3.38):
```
flatpak install runtime/org.gnome.Sdk/x86_64/3.38
flatpak install runtime/org.gnome.Platform/x86_64/3.38
```

Build:
```
flatpak-builder build-dir --force-clean org.x.Warpinator.json
```

Install:
```
flatpak-builder --user --force-clean --install build-dir  org.x.Warpinator.json
```

Test:
```
flatpak run org.x.Warpinator

```

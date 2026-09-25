# Native, game-engine, embedded, and Apple build systems

## Build System Detection (niche)

| File | Build system | Extract |
|------|-------------|---------|
| `CMakeLists.txt` | CMake | `cmake_minimum_required(VERSION ...)`, `project(... LANGUAGES ...)`, `find_package(...)` calls (→ SDKs) |
| `meson.build` | Meson | `project('name', ['cpp'], meson_version : '...')` |
| `BUILD.bazel`, `WORKSPACE` | Bazel | Root `WORKSPACE` dependencies |
| `*.xcodeproj`, `*.xcworkspace` | Xcode | Scheme names, deployment target |
| `*.uproject` | Unreal Engine | `EngineAssociation` field (engine version) |
| `ProjectSettings/ProjectVersion.txt` | Unity | `m_EditorVersion` field |
| `project.godot` | Godot | `config/features=PackedStringArray("4.2", ...)` |
| `platformio.ini` | PlatformIO | `platform`, `board`, `framework` |
| `*.ino` | Arduino | Board from comment headers or `arduino-cli.yaml` |
| `Package.swift` | Swift Package Manager | `swift-tools-version` |
| `Podfile` | CocoaPods | `platform :ios, 'X.Y'` |

## Source Dependencies Detection (niche)

| Source | Pattern | Meaning |
|--------|---------|---------|
| `CMakeLists.txt` / `*.cmake` | `FetchContent_Declare` / `ExternalProject_Add` | CMake auto-fetches at configure time — network required for first configure |
| `CMakeLists.txt` | `add_subdirectory(../<name>)` or `add_subdirectory(${CMAKE_SOURCE_DIR}/../<name>)` | Sibling repo expected — document path + clone URL |
| `west.yml` (Zephyr) | `manifest: projects:` blocks | West workspace — `west init` / `west update` |
| `repo` tool / `default.xml` (AOSP-style) | Any content | `repo sync` flow |

## C++ dependency managers

Check `vcpkg.json`, `conanfile.txt`, `conanfile.py` — a C++ dep-manager bootstrap step belongs in Installation.

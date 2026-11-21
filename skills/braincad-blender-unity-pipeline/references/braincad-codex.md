# BrainCAD Ver0_1 & Codex Reference

## 1. Active Paths & Non-Destructive Versioning

| Purpose | Path | Notes |
| :--- | :--- | :--- |
| Active CAD source | `C:\CADWorks\source\BrainCAD_Ver0_1\BrainCAD` | Primary development repo |
| Deployed app (CADWorks) | `C:\CADWorks\apps\BrainCAD_Ver0_1\BrainCAD.UI.exe` | Updated via `scripts\deploy.ps1` |
| Deployed app (YouTube) | `C:\youtube\tools\BrainCAD_Ver0_1\BrainCAD.UI.exe` | Used by CAD generation pipelines |
| **Protected legacy dirs** | `C:\CADWorks\apps\BrainCAD_Ver0`, `C:\CADWorks\source\BrainCAD_Ver0`, `C:\youtube\tools\BrainCAD_OBJPreview` | **Never overwrite or delete** |
| CAD scene outputs | `C:\youtube\CADmake\<AssetOrBatch>\` | `.ocwproj`, `_Unity_Blender.obj/.mtl`, `_report.json` |
| Codex wrapper | `C:\youtube\scripts\invoke_gpt.ps1` | Enforces UTF-8 & `[CmdletBinding(PositionalBinding=$false)]` |

## 2. Build, Test, and Deploy (`BrainCAD_Ver0_1`)

Always invoke `.ps1` scripts via `powershell -NoProfile -ExecutionPolicy Bypass -File ...` if the machine ExecutionPolicy blocks direct `.ps1` execution (never mutate system-wide policy without explicit user approval).

```powershell
Set-Location "C:\CADWorks\source\BrainCAD_Ver0_1\BrainCAD"

# Sandbox-safe build + native DLL staging + dual-target deploy (0 C4530 warnings):
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\build.ps1" -NoTrackFileAccess -Deploy

# Sandbox-safe C++ EngineTests (47 checks) + C# ProjectTests (550 checks):
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\test.ps1" -NoTrackFileAccess

# Full diagnostic + build + test + deploy with log transcript:
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\check_build_test.ps1" -NoTrackFileAccess -Deploy
```

- `build.ps1` automatically falls back `$env:OCCT_DIR` to `C:\CADWorks\tools\occt\opencascade-7.9.3-vc14-64\cmake` when unset and present.
- `-NoTrackFileAccess` redirects `TMP`/`TEMP` to `build\tmp` and disables MSBuild `TrackFileAccess`, preventing Codex sandbox `No CMAKE_CXX_COMPILER could be found` / Tracker access errors.
- `native\CMakeLists.txt` compiles MSVC with `/utf-8 /EHsc` (zero `C4530` warnings).
- `deploy.ps1` mirrors all Release files to both `C:\CADWorks\apps\BrainCAD_Ver0_1` and `C:\youtube\tools\BrainCAD_Ver0_1`, removes stale files, and verifies file count + SHA256 hashes of `BrainCAD.UI.exe` and `BrainCAD.Engine.dll`.

## 3. Calling Codex CLI (`invoke_gpt.ps1`)

Write a small `.ps1` launcher script and invoke it with **named parameters** (avoid `powershell -File invoke_gpt.ps1 -ContextFiles @(...)` which can split arrays across `powershell -File`):

```powershell
& "C:\youtube\scripts\invoke_gpt.ps1" `
    -TaskType standard `
    -Sandbox workspace-write `
    -WorkDir "C:\youtube" `
    -ContextFiles @("C:\youtube\AGENTS.md", "C:\CADWorks\logs\share\COMMON_STORAGE.md") `
    -Prompt $promptText `
    -OutFile "C:\youtube\CADmake\City_Buildings_v01\codex_report.md"
```

- Routes:
  - `architect` -> `gpt-6.2-astra` (`high`)
  - `standard` -> `gpt-6.2-sol` (`medium`)
  - `light` -> `gpt-6.2-sol` (`low`)
  - `visual` -> `gpt-6.1-terra` (`medium`)
- Note: When Codex writes its own verification markdown file (e.g., `MomijiAve_Extension_verification.md`), `-OutFile` may remain empty; inspect both the `*_report.json` files and Codex's verification `.md` directly.

## 4. Headless Unity Export CLI & Native Engine Resolution

```powershell
# NOTE: BrainCAD.UI.exe is a WinExe GUI subsystem binary.
# In PowerShell, wait synchronously with Start-Process -Wait -PassThru to capture ExitCode!
$proc = Start-Process -FilePath "C:\youtube\tools\BrainCAD_Ver0_1\BrainCAD.UI.exe" -ArgumentList @(
    "--export-unity",
    $projPath,
    $objPath,
    "--report",
    $reportPath
) -Wait -NoNewWindow -PassThru
if ($proc.ExitCode -ne 0) { throw "Export failed: $($proc.ExitCode)" }
```

- Optional flag: `--high-detail` enables fine tessellation (`Native.SetMeshQuality(1)`).
- Exported Unity OBJ coordinates convert BrainCAD (`mm`, Z-up) to Unity (`m`, Y-up, `-Z` forward): `(X * 0.001, Z * 0.001, -Y * 0.001)`. **Important**: When importing these `--export-unity` `.obj` files into Blender 5.3, set `forward_axis='NEGATIVE_Z', up_axis='Y'` (never `up_axis='Z'`, which tips objects onto their side).
- **Native DLL auto-resolution (`NativeGeometry.cs`)**: Searches `BRAINCAD_DIR` env var -> `typeof(Native).Assembly.Location` directory -> `AppContext.BaseDirectory`, and calls `SetDllDirectoryW`. External C# builder projects referencing `BrainCAD.UI.dll` do **not** need to copy any C++/OCCT DLLs into their `bin\` folder.

## 5. `.ocwproj` Schema (v5) & Town-Building Conventions

Observed constraints in `ProjectDocument.cs`:
- `Version`: `5`, `Units`: `"mm"`, max file size `8 MB` (`8,388,608` bytes), `MaxObjects = 1000`.
- Camera: `Yaw` (finite), `Pitch` in `[-85, 85]`, `Zoom` in `[0.2, 8]`.
- Every `Placement` in `Objects` requires `Id` (unique, `<= 128`), `Kind`, `X`/`Y`/`Z` (`|v| <= 1,000,000`), `Size` (v2+), `Rotation` (v4+, quaternion `{X,Y,Z,W}`), plus optional `Color`, `Name`, `Group`, `FilletRadius` (`(0, 10000]`), `Sections` (`Loft`), `Operations` (`Fuse`/`Cut`).
- Box origin is the **minimum corner** (`X`, `Y`, `Z` + positive `Size`).
- **Modular Urban Building Standard (`City_Buildings_v01`)**:
  - Local origin `(0, 0, 0)` at street-facing facade center, facing **`-X`**.
  - Foundation skirt extends down to `Z = -300 mm`; front canopies/trims project into `-X` (`<= 349 mm` so raw export stays within `-0.35 m` clearance).
  - Use unified 9 `Group` names across buildings so Blender/Unity share materials:
    `Foundation`, `Wall_Main`, `Wall_Accent`, `Window_Glass`, `Shop_Glass`, `Frame_Metal`, `Roof_Slab`, `Roof_Mech`, `Signage`.

## 6. Windows / PowerShell 5.1 Pitfalls

- **`rg` (ripgrep) is not installed**: Always use `Get-ChildItem -Recurse` + `Select-String`.
- **PowerShell 5.1 array literals**: `@($a / 1000, $b)` fails with `op_Division` if elements are unparenthesized. Wrap arithmetic elements in `(...)` or `$(...)`: `@(($a / 1000), $b)`.
- **GUI `.exe` exit codes**: Use `Start-Process ... -Wait -PassThru` instead of `& BrainCAD.UI.exe` when synchronous execution and `$proc.ExitCode` checks are required.

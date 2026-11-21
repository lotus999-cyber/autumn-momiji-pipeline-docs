# Blender 5.3 & Unity 6 URP Reference

## 1. Blender 5.3 Headless & OptiX Setup

- Executable: `C:\assetto_custam\tools\blender-5.3.0-windows-x64\blender.exe`
- Headless execution flags:
  ```powershell
  & "C:\assetto_custam\tools\blender-5.3.0-windows-x64\blender.exe" -b --factory-startup --python-exit-code 1 --python script.py
  ```
- Scene scale & frame cleanup: always `--factory-startup`, clear default Cube/Camera/Light, configure Cycles GPU (`OPTIX` on RTX 3070) for baking and preview renders.

## 2. Verified Blender Python Idioms & Pitfalls

1. **`Euler` import (do NOT call `Matrix.Euler`)**:
   ```python
   from mathutils import Vector, Matrix, Euler
   rot_mat = Euler((tilt_x, tilt_y, yaw), 'XYZ').to_matrix()
   ```
2. **`ShaderNodeTexBrick` UV Units & `Fac` Polarity**:
   - When linked to `Texture Coordinate -> UV` with `Scale = 1.0`, `Brick Width = 1.0 / nx` and `Row Height = 1.0 / ny`, **`Mortar Size` is in UV space**: use `~0.0028` for 6x6 stone/sidewalk pavers or `~0.006..0.008` for 2x4..5x14 architectural tiles/concrete (values like `0.014+` bloat joints excessively on fine grids).
   - **`Fac` outputs `1.0` on mortar and `0.0` on brick face**: invert for face masks/heightmaps (`face = 1.0 - fac`) so mortar lines recess rather than protrude. Always inspect baked `_Albedo.png` / `_Normal.png` with `read_file`.
3. **Window Emission Restraint (Daytime Scenes)**:
   - Keep daytime `Emission Strength` subtle (`~0.7-0.95`) on lit interiors/signs; full brightness washes out glass reflections under afternoon sunlight.
4. **Road Markings & Z-Fighting**:
   - Offset lane markings above road crown surface (`z_bot = road_crown_z + 0.001`, `z_top = road_crown_z + 0.006`) so paint strips stay crisp without coplanar flickering.
5. **Organic Tree Seam Fixes (Momiji variants)**:
   - Extract trunk centerlines via Z-slicing rather than shortest-path endpoints to keep the lower trunk centered.
   - Branch base seam transitions: apply gradual inward base tuck (`tuck = 0.82 + 0.18 * smoothstep(0.0, max(0.015, r0 * 0.6), s)`) and inset child twig spawn points (`P - d * (r * 0.4)`).
6. **FBX Export Including Anchor Empties**:
   - Preserve hierarchy empties (e.g., `TreePitAnchor_*`, fixture sockets) using:
     ```python
     bpy.ops.export_scene.fbx(
         filepath=fbx_path,
         use_selection=True,
         axis_forward='-Z',
         axis_up='Y',
         apply_scale_options='FBX_SCALE_UNITS',
         path_mode='RELATIVE',
         mesh_smooth_type='FACE',
         object_types={'MESH', 'EMPTY'},
     )
     ```
7. **Visual Review Gate**:
   - Render 2-3 camera angles (eye-level street view + 3/4 aerial) via Cycles OptiX and inspect each PNG directly with `read_file` before copying FBX files to Unity.
8. **Call `bpy.context.view_layer.update()` Before Reading Linked Empty `.matrix_world`**:
   - Freshly linked/appended parented empties from another `.blend` return Identity `(0, 0, 0)` for `.matrix_world.translation` until `bpy.context.view_layer.update()` evaluates the dependency graph.
9. **Planar Multi-Box Road Shading (`smooth=False`)**:
   - When joining adjacent flat road slabs (e.g. 5-box intersection grids), set `smooth=False` (or strip interior vertical skirt faces before smoothing) so 90° downward side walls do not bend top vertex normals and cast dark shading seams across the carriageway.
10. **`ShaderNodeTexVoronoi` (`Randomness = 0`) Half-Cell UV Offset**:
    - Regular Voronoi feature points at `Randomness = 0` fall on lattice cell corners `(0, 1/scale, ...)`, splitting studs right along tile borders (e.g. 3x3 tactile paving tiles with 12x12 domes). Insert a `ShaderNodeMapping` shifting UV by `(+0.5 / scale, +0.5 / scale)` before `Voronoi` so studs center inside each tile.
11. **3D Signage Contrast, Raw Docstrings & Camera Clearance**:
    - Give extruded 3D text on backlit white fascias its own **non-emissive dark material** (`Konbini_Sign_Text`) rather than sharing emissive colored fascia materials.
    - Use raw docstrings (`r"""..."""`) or escaped backslashes when Python docstrings contain Windows paths like `C:\...\unity\...` (avoids `\uXXXX` `SyntaxError`).
    - Place preview camera coordinates outside building AABBs so shots are never occluded inside neighbor facades.
12. **CAD OBJ Import Hygiene**:
    - Import BrainCAD `--export-unity` OBJs into Blender 5.3 with `forward_axis='NEGATIVE_Z', up_axis='Y'`, call `bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)`, and **never** run `bmesh.ops.bevel` on triangulated/thin-slat CAD OBJ imports (prevents louver/trim spike artifacts).
13. **Pre-Layout Elevation & Furniture Audit**:
    - Query exact world bounds before placing street props, gap infills, bus stops, or pedestrians: e.g., `Road_Sidewalk` (`Z=+0.120m`), `Road_OuterGround` (`Z=+0.108m`), `Konbini_Walkway` (`Z=+0.155m`), `GuardPipe_*` (`X=±6.73..7.23m`), `StreetLight_*` poles, and building entrance bays. Open bus-stop guardrail bays cleanly in the road build scripts rather than placing stops behind guardrails.
14. **Degenerate Bevel UV Repair via Face-Normal Orthonormal Basis `(tangent, bitangent)`**:
    - Axis-aligned Box UV projection collapses narrow/vertical bevel faces when `(u, v)` spans degenerate (`area <= 1e-8`), causing stretched stripes in Unity. Iterate only faces whose UV triangle area falls below threshold, build an orthonormal tangent/bitangent basis `(T, B)` from the polygon normal `N`, and project loop coordinates `(v.co.dot(T), v.co.dot(B))` without altering valid UVs or Empty anchors.

## 3. Unity 6 URP (`6000.6.9f1`, URP `17.6.0`) Builder Patterns

1. **String Compatibility**:
   - Avoid `string.Contains(sub, StringComparison)` (unavailable depending on .NET profile target in Unity C#); use `str.IndexOf(sub, StringComparison.Ordinal) >= 0`.
2. **Protect Unsaved Scenes on Domain Reload**:
   - In `[InitializeOnLoad]` builders, do not auto-discard a dirty open scene:
     ```csharp
     var activeScene = EditorSceneManager.GetActiveScene();
     if (!openSceneIfDirty && activeScene.isDirty) { /* build prefab only & log MenuItem hint */ return; }
     ```
3. **Foliage & Shared Materials**:
   - Set double-sided leaf rendering: `mat.SetFloat("_Cull", 0f); mat.doubleSidedGI = true; mat.enableInstancing = true;`.
   - Call `AssetDatabase.Refresh()` / `ModelImporter.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription` and `imp.AddRemap(...)` + `imp.SaveAndReimport()`.
4. **Dynamic Axis-Sign Placement**:
   - FBX coordinate conversion between Blender and Unity can flip horizontal axis signs depending on root/pivot conventions. Compute `dirX` / `dirZ` dynamically at runtime inside the editor builder from known road anchors (e.g. `TreePitAnchor_R_01` vs `TreePitAnchor_R_09`) and `Road_Asphalt` renderer bounds rather than hardcoding sign assumptions.
5. **Log & Bounds Verification Gate**:
   - After triggering Unity batch or Editor reload/menu build, check `Logs/Editor.log` for zero compilation errors, prefab/scene save confirmation, AND `position` + `Renderer.bounds` values confirming horizontal ground placement.
6. **Single-Root Empty FBX `localRotation` Preservation (`-90°` X Axis Bake)**:
   - Single-root Empty hierarchies exported from Blender (`axis_forward='-Z', axis_up='Y'`, Unity `bakeAxisConversion: 0`) carry `Euler(-90, 0, 0)` (`m_LocalRotation.x = -0.7071068`) on the prefab root to convert Blender Z-up into Unity Y-up.
   - **Never** assign `inst.transform.localRotation = Quaternion.identity;` to instantiated world-aligned roots (roads, lots, buildings) — leave their imported `localRotation` untouched!
   - **Never** assign bare `Quaternion.Euler(0f, yawU, 0f)` to rotated modular single-root prefabs (traffic signals, street props) — always compose around the asset's baked root rotation:
     ```csharp
     inst.transform.rotation = Quaternion.Euler(0f, yawU, 0f) * assetPrefab.transform.localRotation;
     ```
7. **Unity 6 `-batchmode` & WinExe Invocation**:
   - Before invoking headless Unity, check `Get-Process *Unity*` and `Temp\UnityLockfile`; never launch `-batchmode` while Unity Editor is open.
   - If Unity Hub / Editor is completely closed on a Personal license without `com.unity.editor.headless`, `Unity.exe -batchmode` exits with code `198`; advise opening via Unity Hub (`[InitializeOnLoad]`) instead of bypassing license checks.
   - Always invoke WinExe binaries (`BrainCAD.UI.exe`, `Unity.exe`) with `Start-Process -Wait -PassThru` to capture `.ExitCode`.
8. **URP 17 `_EMISSION` Stripping Fix (`RealtimeEmissive`)**:
   - In Unity 6 / URP 17, calling `mat.EnableKeyword("_EMISSION")` alone leaves `m_ValidKeywords: []` in serialized `.mat` YAML and strips emission at runtime. Always set `mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;` (and assign `_EmissionMap` / `_EmissionColor` for illuminated signs such as `Konbini_Fascia_*`, shop signs, headlights, and signal lenses).
9. **URP Transparent Glass Visibility (`ShadowCaster` Disable & No Premultiply)**:
   - Opaque shadows or `_ALPHAPREMULTIPLY_ON` on storefront/vehicle glass hide interior seating, drivers, and shop details. Set `Surface = Transparent`, keep `_ALPHAPREMULTIPLY_ON` disabled, tune alpha explicitly (e.g., `Vehicle_Glass` alpha `0.28` with `Bldg_Glass_Shop` transparent), and call `mat.SetShaderPassEnabled("ShadowCaster", false);`.
10. **Clean Prefab-Time Colliders, Kinematic Vehicles & Stale Remap Cleanup**:
    - Guard static collider generation by excluding non-solid decor meshes (`FallenLeaves`, `Lane`, `Marking`, `Canopy`, `Foliage`, etc.) and setting `ModelImporter.isReadable = true` (plus `mesh.isReadable` check) on static collidable FBXs.
    - Bake `CapsuleCollider` on trees/humans, `MeshCollider` on `TrafficSignals`, and `BoxCollider` + kinematic `Rigidbody` (driven in `FixedUpdate` via `Rigidbody.MovePosition` with pedestrian yielding / lateral push-out) on vehicles (`MomijiVehicleAgent`), avoiding raw mesh colliders on foliage or scattered leaves.
    - Protect `Assets/MomijiAvenue100m/` from generic auto-material postprocessors, call `imp.RemoveRemap(...)` to purge stale GUID remaps before applying current remaps, and match A-frame poster slots by `"Board"` rather than broad `"Sign"` substrings.

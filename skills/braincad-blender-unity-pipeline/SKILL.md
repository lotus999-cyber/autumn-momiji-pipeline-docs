---
name: braincad-blender-unity-pipeline
description: >-
  Orchestrates the 3-stage 3D city and asset pipeline across BrainCAD Ver0_1
  (via OpenAI Codex CLI), Blender 5.3 procedural sculpting and PBR baking, and
  Unity 6 URP automated scene assembly, including model routing and token/wait
  efficiency rules. Use when creating, modifying, or automating CAD models,
  Blender realistic assets, Unity urban scenes, or building BrainCAD_Ver0_1.
---

# BrainCAD -> Blender 5.3 -> Unity 6 URP Pipeline

End-to-end production workflow established for `Autumn_Momiji` / `MomijiAvenue100m` (`BrainCAD Ver0_1` -> `Blender 5.3` -> `Unity 6000.6.9f1`).

## 1. Model Routing Matrix

Match model tier to task type to minimize token waste and rework:

| Role / Stage | Recommended Model / Flag | Scope |
| :--- | :--- | :--- |
| Architecture planning & QA review | `Gemini 4 Neon (medium)` / `Orchestrator` | Multi-stage plans, visual render review, complex debug |
| Complex Blender modeling & PBR baking | `Gemini 4 Neon (medium)` | Procedural trees, road sculpting, Cycles bake shaders, preview renders |
| Rulebooks, Codex driving, Unity integration | `Gemini 4 Hydrogen (medium/low)` | Docs sync, `.ps1` launcher wrappers, asset copy, C# editor builders, verification |
| CAD engine / CLI / UI internals | `GPT-6.2 Astra` (`-TaskType architect`, `high`) | C++/C# internals, DLL search, CLI flags, `.ocwproj` compatibility |
| Modular CAD asset generation | `GPT-6.2 Sol` (`-TaskType standard`, `medium`) | Roads, buildings, props, dimension sweeps, unit tests (`light`/`low` for minor fixes) |

## 2. Wait-Time & Token Efficiency Protocol

Swarm coordinators keep parent context resident; Prompt Cache expires during >5 min waits, causing every wake-up on a ~400k+ token parent context to re-ingest uncached input tokens.

1. **Before heavy waits or new milestones — run `/compact` + overlap independent local work**:
   - Trigger `/compact` (or start a fresh conversation) *before* launching multi-minute Codex or Blender batches. Measured effect: `/compact` + direct parallel background Codex execution reduced uncached input by **63.1%** (`2.93M -> 1.08M`) and raised execution Prompt Cache hit rate to **94.6%**.
   - While Codex runs in background (`~5-10 min`), overlap independent Blender/texture tasks locally rather than waiting idle.
2. **Offload & Shard Heavy Subagents when workload/context grows**:
   - **Heavy Subagent Sharding**: Whenever a standalone Blender sculpting or generation workload exceeds `~10 min`, `~1,500 lines`, or `>= 6` articulated assets (e.g., 8 human characters), split it into **2–3 parallel sharded `invoke_subagent` workers** (e.g., 2×4 characters sharing one canonical material table) so wall-clock time halves and the parent thread does not hit Prompt Cache TTL expiration (`>5 min` idle wait).
   - Delegate heavy multi-image OptiX QA (`>= 4` renders + iterative fix loops) or large standalone Blender generation to `invoke_subagent` (isolated small context) instead of letting the main thread cross `200k+` tokens where model switches (`Plan <-> Exec`) and wait wake-ups re-ingest large uncached blocks. The parent thread inspects only **final confirmed key views (`<= 2–3` images)**.
   - The global `compact-context-guard` hook (`C:\Users\kazu3\.gemini\config\hooks.json`) monitors context size and alerts at `>= 200k` tokens (and every `50k` above) so manual `/compact` can be triggered before long waits or new milestones.
   - Keep `< 3 min` sequential/parallel batches if `invoke_subagent` is not needed.
3. **Swarm & Edit Hygiene**:
   - Post a 1-line status update with expected ETA (e.g. `Codex running (~5-7 min)`) right before starting long background jobs so a monitor does not flag false `[stall]` alerts.
   - Always `read_file` exact target lines immediately before calling `edit_file` to avoid retry loops (achieved 0 mismatch retries across 14 edits).

## 3. Three-Stage Workflow & Verification Gates

### Stage 1: Parametric CAD (`BrainCAD_Ver0_1` + Codex)
1. Invoke Codex through a `.ps1` wrapper using `& "C:\youtube\scripts\invoke_gpt.ps1"` (see [braincad-codex.md](./references/braincad-codex.md)).
2. Keep one `.ocwproj` per modular asset (`<= 250` boxes typical; hard cap `1000`), using unified material group names and local anchor coordinates.
3. Export via headless CLI (`--export-unity ... --report ...`) and verify **triangle counts, group breakdown, and `unityBoundsMin/Max`** before handoff.

### Stage 2: Realistic Sculpting & PBR Bake (`Blender 5.3` + OptiX)
1. Import `*_Unity_Blender.obj` headless via Blender 5.3 (`C:\assetto_custam\tools\blender-5.3.0-windows-x64\blender.exe`).
2. Add bevels/micro-relief, bake 1024x1024 seamless PBR Albedo + Normal maps, export `TreePitAnchor_*` / placement empties (`object_types={'MESH', 'EMPTY'}`), and write `_Unity.fbx` + full preview `.blend`.
3. **Mandatory Gate**: Render OptiX preview shots (street-level + 3/4 aerial) and inspect them visually via `read_file` before Unity integration (catches inverted mortar polarity, Voronoi seam splitting, over-bright emission, multi-box road shading seams, anchor depsgraph misses, or camera obstructions early). See [blender-unity.md](./references/blender-unity.md).

### Stage 3: Scene Assembly (`Unity 6` URP)
1. Copy `_Unity.fbx` and baked `.png` textures into `Assets/<ProjectName>/...`.
2. Update or create an `[InitializeOnLoad]` + `[MenuItem]` `Editor` builder script to configure URP textures, double-sided foliage (`_Cull = 0`), material remaps (preserving single-root FBX `Euler(-90, 0, 0)` orientation!), dynamic anchor placement, prefab save, and `.unity` scene save (guarding `activeScene.isDirty`).
3. **Mandatory Gate**: Inspect `Logs/Editor.log` and the generated `.prefab` to confirm compile finish, prefab/scene save logs, **0 compile/runtime errors**, AND **world `position` + `Renderer.bounds` sanity values** (verifying flat horizontal road/lot placement `Y < 10 m` and non-vertical modular props/signals).

## 4. Detailed References

- CAD paths, build/deploy flags, Codex wrapper rules, `.ocwproj` v5 schema: [braincad-codex.md](./references/braincad-codex.md)
- Blender 5.3 node/mesh idioms and Unity 6 URP C# patterns: [blender-unity.md](./references/blender-unity.md)

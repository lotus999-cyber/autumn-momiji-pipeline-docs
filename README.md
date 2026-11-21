# Autumn_Momiji 3D街並み制作パイプライン（BrainCAD → Blender → Unity）

`BrainCAD Ver0_1`（OpenAI Codex CLI連携）→ `Blender 5.3`（プロシージャル造形・PBRベイク・OptiX QA）→ `Unity 6 (URP)` の3段階で都市街並み・交通シミュレーションを構築するための標準手順書・スキル・構成リポジトリです。

---

## 1. 作成段階別：参照資料マップ

作業のフェーズに応じて、以下の資料を参照してください。

| 作成段階 | 主な作業内容 | 参照すべき資料 |
| :--- | :--- | :--- |
| **全体統括・AI分担・効率化** | モデル使い分け、`/compact` 運用、重サブエージェント並列化、OptiX QA委任 | [skills/braincad-blender-unity-pipeline/SKILL.md](skills/braincad-blender-unity-pipeline/SKILL.md) |
| **Stage 1: CAD設計** | `BrainCAD_Ver0_1` CLI書き出し、`invoke_gpt.ps1` 経由のCodex呼び出し、`.ocwproj` 仕様 | [skills/braincad-blender-unity-pipeline/references/braincad-codex.md](skills/braincad-blender-unity-pipeline/references/braincad-codex.md) |
| **Stage 2: Blender造形・ベイク** | OBJ読込軸設定、PBRベイク、OptiXレンダリング検証、FBX書き出し（Emptyアンカー含む） | [skills/braincad-blender-unity-pipeline/references/blender-unity.md](skills/braincad-blender-unity-pipeline/references/blender-unity.md) (§1〜§2) |
| **Stage 3: Unity統合・実行** | URPマテリアル再マップ、単一ルートFBX回転保持、C#自動構築、`Editor.log` 検証 | [skills/braincad-blender-unity-pipeline/references/blender-unity.md](skills/braincad-blender-unity-pipeline/references/blender-unity.md) (§3) |
| **コンテキスト監視フック** | 200kトークン到達時の `/compact` 促し警告 | [hooks/compact_guard.py](hooks/compact_guard.py) / [hooks/hooks.json](hooks/hooks.json) |

---

## 2. 現行プロジェクトデータ構成（`Autumn_Momiji`）

### 制作環境
- **CAD**: `BrainCAD Ver0_1`（`C:\youtube\tools\BrainCAD_Ver0_1\BrainCAD.UI.exe`）
- **Blender**: `Blender 5.3.0`（`C:\assetto_custam\tools\blender-5.3.0-windows-x64\blender.exe`）
- **Unity**: `Unity 6000.6.9f1` / URP `17.6.0`（`C:\youtube\unity\Autumn_Momiji`）

### アセット・スクリプト一覧
| カテゴリ | Blender作業ディレクトリ | 主な出力（Unity配備先: `Assets/MomijiAvenue100m/`） |
| :--- | :--- | :--- |
| **100m道路・街路樹** | `C:\youtube\unity\Blender_make\MomijiAve_100m\` | `Road_4Lane_MomijiAve_100m_Realistic_Unity.fbx`、もみじ6種（`Momiji_Street_A..F`） |
| **交差点・コンビニ・信号** | `C:\youtube\unity\Blender_make\MomijiAve_Extension_v01\` | `Road_Intersection_Ext_Realistic_Unity.fbx`、`Konbini_Parking_Realistic_Unity.fbx`、信号2種（`Traffic_Signal_MainGo/CrossStop_Unity.fbx`） |
| **都市ビル・独立看板** | `C:\youtube\unity\Blender_make\City_Buildings_v01\` | ビル6種（`City_Bldg_01..06_Unity.fbx`）、独立看板ユニット2種（`SignBoard_Fascia/Blade_Unit.fbx`）、看板PNG 24枚 |
| **街頭小物・ギャップ補完** | `C:\youtube\unity\Blender_make\Tokyo_StreetProps_v01\` | 街路小物・低木・隙間補完 17 FBX、`town_layout_manifest.json`（105件） |
| **人物モデル** | `C:\youtube\unity\Blender_make\Tokyo_Humans_v01\` | 8体型（小学生・高校生・成人・老人 × 男女）FBX |
| **走行車両** | `C:\youtube\unity\Blender_make\Tokyo_Vehicles_v01\` | セダン・ワゴン・都営バス 3 FBX、ナンバー/LED PNG 3枚 |
| **Unity制御・構築** | `C:\youtube\unity\Autumn_Momiji\Assets\` | `Editor/MomijiAvenueSceneBuilder.cs`（`v8`）、`Scripts/Traffic/MomijiTrafficSignalController.cs`、`MomijiVehicleAgent.cs` |

---

## 3. 今後の編集体制・ワークフロー

1. **モデル・アセットの追加・修正**
   - CAD形状を変更する場合は Stage 1（`braincad-codex.md`）に従い `--export-unity` でOBJ出力後、Stage 2 のBlenderスクリプトでPBR化・FBX書き出しを行います。
   - Blender側で修正した場合は、**必ずOptiXレンダリング（`render_*_qa.py`）をサブエージェントで実行し、最終確認画像（2〜3枚）を目視確認してから** Unityへコピーします。
2. **Unityシーンの再構築**
   - アセットや `MomijiAvenueSceneBuilder.cs` を更新したら、Unity Editorウィンドウをフォーカスするか、メニュー **`Tools > Momiji > Build 100m Maple Avenue Scene`** を実行してプレハブ・シーンを再生成します。
   - 再生成後は `Logs/Editor.log` でコンパイルエラー0件および `SpotCheck` 座標を確認します。
3. **セッション・トークン管理**
   - 長時間バッチや新規マイルストーンの前には `/compact` を実行し、`compact-context-guard` フックの警告（200kトークン〜）を目安にコンテキストを軽量に保ちます。

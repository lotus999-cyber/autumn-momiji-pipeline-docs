import json
import os
import sys
import tempfile


def read_latest_context_tokens(transcript_path: str) -> int:
    if not transcript_path or not os.path.isfile(transcript_path):
        return 0
    latest = 0
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "PLANNER_RESPONSE":
            inp = obj.get("input_tokens") or 0
            cache = obj.get("cache_read_tokens") or 0
            if inp or cache:
                latest = int(inp) + int(cache)
                break
    return latest


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        conv_id = payload.get("conversationId") or "default"
        transcript_path = payload.get("transcriptPath") or ""

        ctx = read_latest_context_tokens(transcript_path)
        state_file = os.path.join(tempfile.gettempdir(), f"agy_compact_guard_{conv_id}.json")

        last_bucket = 0
        if os.path.isfile(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as sf:
                    last_bucket = int(json.load(sf).get("last_bucket", 0))
            except Exception:
                last_bucket = 0

        # Reset bucket counter if conversation just compacted
        if ctx < 120000:
            if last_bucket != 0:
                try:
                    with open(state_file, "w", encoding="utf-8") as sf:
                        json.dump({"last_bucket": 0, "last_ctx": ctx}, sf)
                except Exception:
                    pass
            print("{}")
            return

        if ctx < 200000:
            print("{}")
            return

        bucket = ctx // 50000
        if bucket <= last_bucket:
            print("{}")
            return

        try:
            with open(state_file, "w", encoding="utf-8") as sf:
                json.dump({"last_bucket": bucket, "last_ctx": ctx}, sf)
        except Exception:
            pass

        out = {
            "injectSteps": [
                {
                    "systemMessage": {
                        "systemMessage": (
                            f"[CompactGuard] Context reached ~{ctx:,} tokens. "
                            "Offload multi-image visual QA or heavy modeling to sharded subagents, "
                            "and advise user to run /compact before long waits or next milestone."
                        ),
                        "metadata": {
                            "user_markdown": (
                                f"> [!TIP]\n"
                                f"> コンテキストが約 **{ctx:,} tokens** に達しました。"
                                f"次の大きな工程や待機に入る前に `/compact` の実行をおすすめします。"
                            )
                        },
                    }
                }
            ],
            "terminationBehavior": "",
        }
        print(json.dumps(out, ensure_ascii=False))
    except Exception:
        print("{}")


if __name__ == "__main__":
    main()

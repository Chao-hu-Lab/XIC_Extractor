from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOKS = ROOT / ".codex" / "hooks"
sys.path.insert(0, str(HOOKS))

from xic_hook_policy import PRODUCT_SURFACE_PATHS, mentions_any_path  # noqa: E402


def run_hook(
    script: str,
    event: dict[str, object],
    *,
    env_extra: dict[str, str] | None = None,
) -> dict[str, object]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(event),
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    output = result.stdout.strip()
    if not output:
        raise AssertionError(f"{script} emitted no output")
    return json.loads(output)


def assert_contains(value: object, expected: str) -> None:
    text = json.dumps(value, ensure_ascii=False)
    if expected not in text:
        raise AssertionError(f"expected {expected!r} in {text}")


def main() -> int:
    prompt_payload = {
        "hook_event_name": "UserPromptSubmit",
        "turn_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "prompt": "這個功能是不是已經正式產品化？我要確認 promotion tier。",
    }
    assert_contains(
        run_hook("xic_prompt_router.py", prompt_payload),
        "productization-control-plane.md",
    )

    handoff_prompt_payload = {
        "hook_event_name": "UserPromptSubmit",
        "turn_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "prompt": (
            "準備收尾，請更新交接文件，避免下一個 session "
            "因 context compaction 丟資訊。"
        ),
    }
    assert_contains(
        run_hook("xic_prompt_router.py", handoff_prompt_payload),
        "cc-framework-improvements-productization.md",
    )

    pre_payload = {
        "hook_event_name": "PreToolUse",
        "turn_id": "fixture",
        "tool_name": "Bash",
        "tool_use_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "tool_input": {
            "command": "Set-Content xic_extractor\\output\\schema.py '# edit'",
        },
    }
    assert_contains(
        run_hook("xic_pre_tool_guard.py", pre_payload),
        "Product/public surface may be edited",
    )

    apply_patch_payload = {
        "hook_event_name": "PreToolUse",
        "turn_id": "fixture",
        "tool_name": "apply_patch",
        "tool_use_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "tool_input": {
            "patch": "*** Update File: xic_extractor/signal_processing.py\n",
        },
    }
    assert_contains(
        run_hook("xic_pre_tool_guard.py", apply_patch_payload),
        "Product/public surface may be edited",
    )

    post_subdir_payload = {
        "hook_event_name": "PostToolUse",
        "turn_id": "fixture",
        "tool_name": "Bash",
        "tool_use_id": "fixture",
        "cwd": "docs",
        "permission_mode": "default",
        "tool_input": {
            "command": "Set-Content ..\\xic_extractor\\output\\schema.py '# edit'",
        },
        "tool_response": {"stdout": "", "stderr": ""},
    }
    assert_contains(
        run_hook("xic_post_tool_guard.py", post_subdir_payload),
        "productization control plane",
    )

    post_apply_patch_payload = {
        "hook_event_name": "PostToolUse",
        "turn_id": "fixture",
        "tool_name": "apply_patch",
        "tool_use_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "tool_input": {
            "patch": "*** Update File: scripts/run_any_public_cli.py\n",
        },
        "tool_response": {"stdout": "", "stderr": ""},
    }
    assert_contains(
        run_hook("xic_post_tool_guard.py", post_apply_patch_payload),
        "productization control plane",
    )

    non_product_payload = {
        "hook_event_name": "PreToolUse",
        "turn_id": "fixture",
        "tool_name": "Bash",
        "tool_use_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "tool_input": {
            "command": "Set-Content docs\\scratch-note.md '# note'",
        },
    }
    result = subprocess.run(
        [sys.executable, str(HOOKS / "xic_pre_tool_guard.py")],
        input=json.dumps(non_product_payload),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.stdout.strip():
        raise AssertionError("non-product path emitted productization context")

    unrelated_write_with_ambient_product_dirty_payload = {
        "hook_event_name": "PostToolUse",
        "turn_id": "fixture",
        "tool_name": "Bash",
        "tool_use_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "tool_input": {
            "command": "Set-Content docs\\scratch-note.md '# note'",
        },
        "tool_response": {"stdout": "", "stderr": ""},
    }
    result = subprocess.run(
        [sys.executable, str(HOOKS / "xic_post_tool_guard.py")],
        input=json.dumps(unrelated_write_with_ambient_product_dirty_payload),
        cwd=ROOT,
        env={
            **os.environ,
            "XIC_POST_TOOL_GUARD_CHANGED_PATHS_JSON": json.dumps(
                ["xic_extractor/output/schema.py"]
            ),
            "XIC_POST_TOOL_GUARD_HANDOFF_LINE_COUNT": "250",
        },
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.stdout.strip():
        raise AssertionError("unrelated write emitted ambient product dirty warning")

    product_with_control_plane_payload = {
        "hook_event_name": "PostToolUse",
        "turn_id": "fixture",
        "tool_name": "apply_patch",
        "tool_use_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "tool_input": {
            "patch": (
                "*** Update File: xic_extractor/output/schema.py\n"
                "*** Update File: docs/superpowers/plans/"
                "2026-06-15-productization-control-plane.md\n"
            ),
        },
        "tool_response": {"stdout": "", "stderr": ""},
    }
    assert_contains(
        run_hook("xic_post_tool_guard.py", product_with_control_plane_payload),
        "cc-framework-improvements-productization.md",
    )

    product_with_control_plane_and_handoff_payload = {
        "hook_event_name": "PostToolUse",
        "turn_id": "fixture",
        "tool_name": "apply_patch",
        "tool_use_id": "fixture",
        "cwd": ".",
        "permission_mode": "default",
        "tool_input": {
            "patch": (
                "*** Update File: xic_extractor/output/schema.py\n"
                "*** Update File: docs/superpowers/plans/"
                "2026-06-15-productization-control-plane.md\n"
                "*** Update File: docs/superpowers/handoffs/current/"
                "cc-framework-improvements-productization.md\n"
            ),
        },
        "tool_response": {"stdout": "", "stderr": ""},
    }
    result = subprocess.run(
        [sys.executable, str(HOOKS / "xic_post_tool_guard.py")],
        input=json.dumps(product_with_control_plane_and_handoff_payload),
        cwd=ROOT,
        env={
            **os.environ,
            "XIC_POST_TOOL_GUARD_HANDOFF_LINE_COUNT": "40",
        },
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.stdout.strip():
        raise AssertionError(
            "product/control-plane edit with handoff edit emitted warning"
        )

    assert_contains(
        run_hook(
            "xic_post_tool_guard.py",
            product_with_control_plane_and_handoff_payload,
            env_extra={"XIC_POST_TOOL_GUARD_HANDOFF_LINE_COUNT": "250"},
        ),
        "Active handoff is 250 lines",
    )

    for path in (
        "scripts/run_new_cli.py",
        "xic_extractor/extractor.py",
        "xic_extractor/signal_processing.py",
        "..\\xic_extractor\\output\\schema.py",
    ):
        if not mentions_any_path(path, PRODUCT_SURFACE_PATHS):
            raise AssertionError(f"public surface path did not match: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

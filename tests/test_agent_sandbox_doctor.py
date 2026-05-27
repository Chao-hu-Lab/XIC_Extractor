from pathlib import Path

from scripts import agent_sandbox_doctor


def _codes(command: str, workspace_root: Path, allowed_root: Path) -> set[str]:
    findings = agent_sandbox_doctor.classify_command(
        command,
        workspace_root=workspace_root,
        allowed_write_roots=(allowed_root,),
    )
    return {finding.code for finding in findings}


def test_classify_powershell_antipatterns(tmp_path: Path) -> None:
    codes = _codes(
        "export FOO=bar && python - <<'PY'",
        workspace_root=tmp_path,
        allowed_root=tmp_path,
    )

    assert "powershell_export" in codes
    assert "powershell_chain_operator" in codes
    assert "powershell_bash_heredoc" in codes


def test_classify_85raw_background_and_bare_python_raw_runner(
    tmp_path: Path,
) -> None:
    command = (
        "Start-Process python -ArgumentList "
        "'-m scripts.run_alignment --expected-sample-count 85 "
        "--raw-dir C:\\raw --dll-dir C:\\dll'"
    )

    codes = _codes(command, workspace_root=tmp_path, allowed_root=tmp_path)

    assert "background_long_raw_run" in codes
    assert "raw_runner_not_venv" in codes


def test_classify_output_outside_allowed_roots(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    allowed_root = workspace_root
    outside = tmp_path / "external-output"
    command = (
        ".venv\\Scripts\\python.exe -m scripts.run_alignment "
        f'--output-dir "{outside}"'
    )

    findings = agent_sandbox_doctor.classify_command(
        command,
        workspace_root=workspace_root,
        allowed_write_roots=(allowed_root,),
    )

    assert [finding.code for finding in findings] == ["output_outside_writable_roots"]
    assert findings[0].severity == "review"


def test_documented_venv_alignment_command_is_clean(tmp_path: Path) -> None:
    command = (
        ".venv\\Scripts\\python.exe -m scripts.run_alignment "
        "--raw-dir C:\\raw --dll-dir C:\\dll --output-dir output\\alignment "
        "--timing-live-output output\\timing.live.json"
    )

    findings = agent_sandbox_doctor.classify_command(
        command,
        workspace_root=tmp_path,
        allowed_write_roots=(tmp_path,),
    )

    assert findings == ()


def test_main_strict_json_output_reports_blockers(
    tmp_path: Path,
    capsys,
) -> None:
    output = tmp_path / "doctor.json"

    code = agent_sandbox_doctor.main(
        [
            "--workspace-root",
            str(tmp_path),
            "--allowed-write-root",
            str(tmp_path),
            "--command",
            "python -m scripts.run_alignment --raw-dir C:\\raw --dll-dir C:\\dll",
            "--json-output",
            str(output),
            "--strict",
        ]
    )

    stdout = capsys.readouterr().out
    assert code == 2
    assert "preflight_blocked" in stdout
    assert "raw_runner_not_venv" in output.read_text(encoding="utf-8")


def test_default_allowed_write_roots_are_absolute(tmp_path: Path) -> None:
    roots = agent_sandbox_doctor._default_allowed_write_roots(tmp_path)

    assert tmp_path.resolve() in roots
    assert all(root.is_absolute() for root in roots)


def test_probe_write_does_not_clobber_existing_probe_file(tmp_path: Path) -> None:
    existing = tmp_path / ".agent_sandbox_doctor_probe"
    existing.write_text("keep me\n", encoding="utf-8")

    report = agent_sandbox_doctor.build_environment_report(
        workspace_root=tmp_path,
        allowed_write_roots=(tmp_path,),
        probe_write=True,
    )

    assert report.status == "ok"
    assert existing.read_text(encoding="utf-8") == "keep me\n"

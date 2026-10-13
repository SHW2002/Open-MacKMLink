"""Exercise refusal, atomic preparation, reuse and startup gating without activation."""
from pathlib import Path
from unittest.mock import patch

from desktop import workflow, workspace
from manage_startup import verified_paths
from prepare_runtime import prepare
from startup import registry


def check(original, project):
    reports = {}
    paths = verified_paths(project)
    with patch.object(workspace, "processes", return_value=(None, [(123, paths["repair"])])), \
            patch.object(registry, "snapshot", return_value={"32": None, "64": None}), \
            patch.object(workspace, "remembered", return_value={}):
        assert workspace.workspace_for(original) == project
        assert workspace.discover() == original
    reports["existing_repair_reused"] = True
    with patch.object(workspace, "processes", return_value=(None, [])), \
            patch.object(registry, "snapshot", return_value={"32": {"value": 42}, "64": None}), \
            patch.object(workspace, "remembered", return_value={str(original): str(project)}):
        assert workspace.workspace_for(original) == project
    reports["remembered_workspace_reverified"] = True

    unknown = project / "unknown.exe"
    unknown.write_bytes(b"unknown build")
    with patch.object(workflow, "switch") as activate, patch.object(workflow, "manage") as startup:
        try:
            workflow.repair(unknown, True, lambda text: None, project=project)
        except ValueError:
            pass
        else:
            raise AssertionError("Unknown input was accepted")
        activate.assert_not_called()
        startup.assert_not_called()
    reports["unknown_input_refused_before_activation"] = True

    retry = project / "preparation-check"
    retry.mkdir()
    with patch("prepare_runtime.shutil.copytree", side_effect=OSError("simulated copy failure")):
        try:
            prepare(original.parent, project / "artifacts", retry / "runtime", retry)
        except OSError:
            pass
        else:
            raise AssertionError("Copy failure was not reported")
    assert not list(retry.iterdir()), "Partial runtime was left behind"
    prepare(original.parent, project / "artifacts", retry / "runtime", retry)
    preserved = (retry / "runtime/runtime-info.json").read_bytes()
    try:
        prepare(original.parent, project / "artifacts", retry / "runtime", retry)
    except ValueError:
        pass
    else:
        raise AssertionError("Existing runtime was overwritten")
    assert (retry / "runtime/runtime-info.json").read_bytes() == preserved
    reports["failed_preparation_cleaned_and_retry_passed"] = True
    reports["existing_runtime_preserved"] = True

    with patch.object(workflow, "workspace_for", return_value=project), \
            patch.object(workflow, "preflight", side_effect=RuntimeError("disabled in Windows Startup")), \
            patch.object(workflow, "switch") as activate, patch.object(workflow, "manage") as startup, \
            patch.object(workflow, "remember") as remember:
        try:
            workflow.select_runtime(original, "repair", True, lambda text: None)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Startup preflight was skipped")
        activate.assert_not_called()
        startup.assert_not_called()
        remember.assert_not_called()
    reports["startup_refusal_precedes_process_switch"] = True
    return reports

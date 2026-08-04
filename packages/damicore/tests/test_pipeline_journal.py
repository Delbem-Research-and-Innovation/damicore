import json

import pytest

from damicore import ArtifactValidationError, CheckpointMismatchError
from damicore.pipeline import PipelineJournal

pytestmark = pytest.mark.unit


def _manifest(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest = {"status": "created", "stages": {}}
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir, manifest


def test_journal_receipts_validate_outputs(tmp_path):
    run_dir, manifest = _manifest(tmp_path)
    source = tmp_path / "input.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    output = run_dir / "result.txt"
    journal = PipelineJournal(run_dir, manifest)
    started = journal.stage_started("normalizing", [source])
    output.write_text("ok", encoding="utf-8")
    journal.stage_completed("normalizing", started, [output], {"count": 1})
    assert journal.reusable("normalizing")
    output.write_text("bad", encoding="utf-8")
    with pytest.raises(ArtifactValidationError):
        journal.reusable("normalizing")


def test_journal_rejects_malformed_checkpoint(tmp_path):
    run_dir, manifest = _manifest(tmp_path)
    checkpoint = run_dir / "checkpoints/pipeline.json"
    checkpoint.parent.mkdir()
    checkpoint.write_text("not json", encoding="utf-8")
    with pytest.raises(CheckpointMismatchError):
        PipelineJournal(run_dir, manifest)


def test_journal_rejects_checkpoint_schema_extensions(tmp_path):
    run_dir, manifest = _manifest(tmp_path)
    journal = PipelineJournal(run_dir, manifest)
    checkpoint = json.loads(journal.checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["unexpected"] = True
    journal.checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    with pytest.raises(CheckpointMismatchError):
        PipelineJournal(run_dir, manifest)

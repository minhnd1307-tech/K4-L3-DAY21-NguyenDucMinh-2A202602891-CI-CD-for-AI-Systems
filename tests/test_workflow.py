import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


@pytest.mark.parametrize("f1, passes", [
    ("0.6499", False), ("0.65", True), ("0.7149", True),
    ("nan", False), ("inf", False), ("1.1", False), ("", False),
])
def test_quality_gate_blocks_invalid_or_low_f1(f1, passes):
    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows/cicd.yml"
    workflow = yaml.safe_load(workflow_path.read_text())
    script = workflow["jobs"]["quality-gate"]["steps"][0]["run"]
    # Execute the actual gate embedded in the workflow, not a copied condition.
    lines = script.strip().splitlines()
    assert lines[0] == "python - <<'PYEOF'" and lines[-1] == "PYEOF"
    result = subprocess.run(
        [sys.executable, "-c", "\n".join(lines[1:-1])],
        env={**os.environ, "F1_SCORE": f1},
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == passes, result.stderr

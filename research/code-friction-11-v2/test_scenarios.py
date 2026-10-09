#!/usr/bin/env python3
"""Execute the corrected S3 and S7 synthetic fixtures with Node."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCENARIOS = json.loads((ROOT / "packet" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]


def scenario(identifier):
    return next(item for item in SCENARIOS if item["id"] == identifier)


def run_fixture(identifier, runner_source):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
        current = scenario(identifier)
        for item in current["files"]:
            path = root / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item["content"], encoding="utf-8")
        runner = root / "runner.mjs"
        runner.write_text(runner_source, encoding="utf-8")
        result = subprocess.run(
            ["node", str(runner)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise AssertionError(f"{identifier} Node fixture failed:\n{result.stdout}\n{result.stderr}")


class CorrectedScenarioTests(unittest.TestCase):
    def test_s3_legacy_colon_compatibility_and_missing_slash_behavior(self):
        run_fixture(
            "S3-hidden-dependency",
            """
            import { normalizeResourceId } from './src/ids.js';
            import { cacheKey } from './src/cache/key.js';
            import { auditResource } from './src/audit/event.js';
            if (normalizeResourceId(' ABC:1 ') !== 'abc1') throw new Error('legacy colon behavior changed');
            if (cacheKey(' Team/Blue:1 ') === 'resource:team/blue1') throw new Error('slash-preserving task is already implemented');
            if (auditResource(' Team/Blue:1 ', 'read').resourceId === 'team/blue1') throw new Error('audit slash-preserving task is already implemented');
            """,
        )

    def test_s7_before_and_after_keep_defaults_but_lack_opt_out(self):
        for identifier in ("S7-before", "S7-after"):
            run_fixture(
                identifier,
                """
                import { notify } from './src/notify.js';
                const message = { to: 'a', body: 'b', number: '1', text: 'b' };
                const tags = ['urgent'];
                const defaults = notify('email', message, tags);
                const optOut = notify('email', message, tags, { includeTags: false });
                if (defaults.tags !== tags) throw new Error('default tags compatibility changed');
                if (optOut.tags !== tags) throw new Error('includeTags task is already implemented');
                """,
            )


if __name__ == "__main__":
    unittest.main()

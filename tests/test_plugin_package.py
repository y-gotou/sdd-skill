"""Codex プラグインの配布構成を検証する。"""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginPackageTest(unittest.TestCase):
    def test_codex_manifest_and_marketplace_reference_existing_skill(self):
        portable = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(portable["name"], "sdd")
        self.assertEqual(codex["name"], portable["name"])
        self.assertEqual(codex["version"], portable["version"])
        self.assertTrue((ROOT / "skills" / "sdd" / "SKILL.md").is_file())
        self.assertEqual(marketplace["name"], "sdd-skill")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "sdd")
        self.assertEqual(entry["source"], {"source": "local", "path": "./"})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")


if __name__ == "__main__":
    unittest.main()

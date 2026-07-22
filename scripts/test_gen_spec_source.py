#!/usr/bin/env python3
"""Unit checks that gen_spec emits source provenance."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "gen_spec.py"


def load_gen_spec():
    spec = importlib.util.spec_from_file_location("gen_spec", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class BuildSpecSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gs = load_gen_spec()

    def test_emits_source_from_manifest_entry(self):
        entry = {
            "owner": "cptpiepmatz",
            "name": "nu_plugin_highlight",
            "plugin_bin": "nu_plugin_highlight",
            "repo": "cptpiepmatz/nu-plugin-highlight",
            "tag": "v1.4.15+0.113.1",
            "version": "1.4.15",
            "nu_version": ">=0.113.0 <0.114.0",
            "verified_with": ["0.113.1"],
            "description": "Syntax highlighting.",
            "tags": ["plugin", "highlight"],
        }
        rows = [
            {
                "target": "x86_64-unknown-linux-gnu",
                "filename": "nu_plugin_highlight-1.4.15-x86_64-unknown-linux-gnu.tar.gz",
                "sha256": "abc",
                "exe": "nu_plugin_highlight",
            }
        ]
        out = self.gs.build_spec(
            entry,
            rows,
            "https://github.com/tonythethompson/numan-plugins/releases/download/nu_plugin_highlight-1.4.15",
        )
        self.assertEqual(
            out["source"],
            {
                "git": "https://github.com/cptpiepmatz/nu-plugin-highlight",
                "rev": "v1.4.15+0.113.1",
                "cargo_name": "nu_plugin_highlight",
            },
        )
        self.assertEqual(out["repo"], "https://github.com/cptpiepmatz/nu-plugin-highlight")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BuildSpecSourceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

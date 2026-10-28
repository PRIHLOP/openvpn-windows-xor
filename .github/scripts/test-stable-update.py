#!/usr/bin/env python3
"""Regression checks for local XOR adaptations; no network access required."""
import importlib.util
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare", Path(__file__).with_name("prepare-stable-update.py"))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PatchUpdateTests(unittest.TestCase):
    def test_upstream_refresh_preserves_local_adaptations(self):
        with tempfile.TemporaryDirectory() as directory:
            patches = Path(directory)
            for patch in (ROOT / "tunnelblick-patches").glob("*.diff"):
                expected = patch.read_bytes()
                # Reconstruct the upstream forms which caused the 2.7.8 failure.
                upstream = expected
                if patch.name == prepare.PATCH_NAMES[1]:
                    upstream = upstream.replace(
                        b' {\n     setenv_str_i(es, "remote", e->remote, i);',
                        b'     setenv_str_i(es, "local_port", e->local_port, i);\n'
                        b'     setenv_str_i(es, "remote", e->remote, i);')
                    upstream = upstream.replace(b'(int)strlen', b'strlen')
                if patch.name == prepare.PATCH_NAMES[3]:
                    upstream = upstream.replace(b'(uint8_t)(*b ^ ((i + 1) & 0xff))', b'*b ^ i+1')
                adapted = prepare.adapt_patch(patch.name, upstream.replace(b'\n', b'\r\n'), ROOT / "src/openvpn")
                self.assertEqual(adapted, expected)
                self.assertEqual(prepare.adapt_patch(patch.name, adapted, ROOT / "src/openvpn"), adapted)
                (patches / patch.name).write_bytes(adapted)
            before = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT / 'src/openvpn')
            prepare.check_patch_series(ROOT / "src/openvpn", patches)
            self.assertEqual(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT / 'src/openvpn'), before)

    def test_prepare_updates_versions_and_adapts_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["tunnelblick-patches", "windows-msi", "release"]:
                (root / name).mkdir()
            shutil.copytree(ROOT / "tunnelblick-patches", root / "tunnelblick-patches", dirs_exist_ok=True)
            for name in ["README.md", "windows-msi/version.m4", "release/vars.example"]:
                (root / name).write_text((ROOT / name).read_text().replace("2.7.8", "2.7.6"))
            (root / "src").mkdir()
            prepare.run("git", "clone", "--shared", str(ROOT / "src/openvpn"),
                        str(root / "src/openvpn"), cwd=root)
            revision = prepare.run("git", "rev-parse", "HEAD", cwd=root / "src/openvpn")
            responses = [
                {"tag_name": "v2.7.8", "html_url": "https://example.invalid/release"},
                {"sha": revision}, {"sha": "a" * 40},
                [{"name": name, "download_url": name} for name in prepare.PATCH_NAMES],
            ]
            original_run = prepare.run

            def offline_run(*command, cwd):
                if command[:2] == ("git", "fetch"):
                    return ""
                return original_run(*command, cwd=cwd)

            def upstream_download(name):
                return (ROOT / "tunnelblick-patches" / name).read_bytes().replace(
                    b"(int)strlen", b"strlen").replace(
                    b"(uint8_t)(*b ^ ((i + 1) & 0xff))", b"*b ^ i+1").replace(
                    b' {\n     setenv_str_i(es, "remote", e->remote, i);',
                    b'     setenv_str_i(es, "local_port", e->local_port, i);\n'
                    b'     setenv_str_i(es, "remote", e->remote, i);')

            with patch.object(prepare, "api_request", side_effect=responses), \
                 patch.object(prepare, "download", side_effect=upstream_download), \
                 patch.object(prepare, "run", side_effect=offline_run):
                result = prepare.prepare(root, root / "report.md")
            self.assertEqual(result["status"], "prepared")
            self.assertIn("openvpn-install-2.7.8-I001-xor", (root / "README.md").read_text())
            self.assertIn("[2.7.801]", (root / "windows-msi/version.m4").read_text())
            self.assertIn("OPENVPN_CURRENT_VERSION:-2.7.8", (root / "release/vars.example").read_text())
            self.assertIn("OPENVPN_PREVIOUS_VERSION:-2.7.6", (root / "release/vars.example").read_text())
            for name in prepare.PATCH_NAMES:
                self.assertEqual((root / "tunnelblick-patches" / name).read_bytes(),
                                 (ROOT / "tunnelblick-patches" / name).read_bytes())

    def test_unknown_conflict_stops_update(self):
        with tempfile.TemporaryDirectory() as directory:
            patches = Path(directory)
            (patches / '01-broken.diff').write_text(
                'diff --git a/src/openvpn/options.c b/src/openvpn/options.c\n'
                '--- a/src/openvpn/options.c\n+++ b/src/openvpn/options.c\n'
                '@@ -1 +1 @@\n-this context does not exist\n+replacement\n')
            with self.assertRaises(prepare.PreparationError):
                prepare.check_patch_series(ROOT / "src/openvpn", patches)


if __name__ == "__main__":
    unittest.main()

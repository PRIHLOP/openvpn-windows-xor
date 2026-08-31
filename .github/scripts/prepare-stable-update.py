#!/usr/bin/env python3
"""Prepare a conservative update to the latest stable OpenVPN release."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


API_ROOT = "https://api.github.com"
OPENVPN_REPOSITORY = "OpenVPN/openvpn"
TUNNELBLICK_REPOSITORY = "Tunnelblick/Tunnelblick"
PATCH_NAMES = [
    "02-tunnelblick-openvpn_xorpatch-a.diff",
    "03-tunnelblick-openvpn_xorpatch-b.diff",
    "04-tunnelblick-openvpn_xorpatch-c.diff",
    "05-tunnelblick-openvpn_xorpatch-d.diff",
    "06-tunnelblick-openvpn_xorpatch-e.diff",
]


class PreparationError(RuntimeError):
    pass


def api_request(path: str, *, allow_missing: bool = False) -> object | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "openvpn-windows-xor-stable-monitor",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API_ROOT}{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if allow_missing and error.code == 404:
            return None
        raise PreparationError(f"GitHub API request failed ({error.code}): {path}") from error
    except urllib.error.URLError as error:
        raise PreparationError(f"GitHub API request failed: {path}: {error.reason}") from error


def download(url: str) -> bytes:
    headers = {"User-Agent": "openvpn-windows-xor-stable-monitor"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            return response.read()
    except urllib.error.URLError as error:
        raise PreparationError(f"Failed to download {url}: {error.reason}") from error


def run(*command: str, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise PreparationError(f"Command failed: {' '.join(command)}\n{details}")
    return result.stdout.strip()


def replace_once(text: str, pattern: str, replacement: str, description: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise PreparationError(f"Could not update {description}")
    return updated


def write_outputs(path: Path | None, values: dict[str, str]) -> None:
    if not path:
        return
    with path.open("a", encoding="utf-8") as output:
        for key, value in values.items():
            if "\n" in value:
                raise PreparationError(f"Output {key} contains a newline")
            output.write(f"{key}={value}\n")


def write_report(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def gitlink_sha(root: Path) -> str:
    entry = run("git", "ls-files", "-s", "src/openvpn", cwd=root)
    match = re.fullmatch(r"160000 ([0-9a-f]{40}) 0\tsrc/openvpn", entry)
    if not match:
        raise PreparationError("src/openvpn is not a valid gitlink")
    return match.group(1)


def prepare(root: Path, report_path: Path) -> dict[str, str]:
    release = api_request(f"/repos/{OPENVPN_REPOSITORY}/releases/latest")
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        raise PreparationError("The latest OpenVPN release is not a stable published release")

    tag = str(release.get("tag_name", ""))
    version_match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not version_match:
        raise PreparationError(f"Unexpected stable release tag: {tag!r}")
    version = tag.removeprefix("v")
    release_url = str(release.get("html_url", ""))

    commit = api_request(f"/repos/{OPENVPN_REPOSITORY}/commits/{urllib.parse.quote(tag)}")
    if not isinstance(commit, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(commit.get("sha", ""))):
        raise PreparationError(f"Could not resolve OpenVPN tag {tag}")
    release_sha = str(commit["sha"])

    tunnelblick = api_request(f"/repos/{TUNNELBLICK_REPOSITORY}/commits/main")
    if not isinstance(tunnelblick, dict) or not re.fullmatch(
        r"[0-9a-f]{40}", str(tunnelblick.get("sha", ""))
    ):
        raise PreparationError("Could not resolve Tunnelblick main")
    tunnelblick_sha = str(tunnelblick["sha"])

    patch_directory = f"third_party/sources/openvpn/openvpn-{version}/patches"
    encoded_directory = urllib.parse.quote(patch_directory, safe="/")
    patch_listing = api_request(
        f"/repos/{TUNNELBLICK_REPOSITORY}/contents/{encoded_directory}?ref={tunnelblick_sha}",
        allow_missing=True,
    )

    base_report = [
        f"## OpenVPN {version} stable update",
        "",
        f"- OpenVPN release: [{tag}]({release_url})",
        f"- OpenVPN commit: `{release_sha}`",
        f"- Tunnelblick commit: `{tunnelblick_sha}`",
        f"- Tunnelblick patch directory: `{patch_directory}`",
        "",
    ]

    common_outputs = {
        "version": version,
        "tag": tag,
        "release_sha": release_sha,
        "tunnelblick_sha": tunnelblick_sha,
        "branch": f"automation/openvpn-stable-{version}",
        "report": str(report_path),
    }

    if patch_listing is None:
        write_report(
            report_path,
            base_report
            + [
                "### Manual attention required",
                "",
                "Tunnelblick has not published a matching patch directory yet.",
            ],
        )
        return {**common_outputs, "status": "waiting"}

    if not isinstance(patch_listing, list):
        raise PreparationError("Unexpected Tunnelblick patch directory response")
    patches = {str(item.get("name")): item for item in patch_listing if isinstance(item, dict)}
    missing = [name for name in PATCH_NAMES if name not in patches]
    if missing:
        write_report(
            report_path,
            base_report
            + [
                "### Manual attention required",
                "",
                "The matching Tunnelblick directory is incomplete.",
                "",
                "Missing patches: " + ", ".join(f"`{name}`" for name in missing),
            ],
        )
        return {**common_outputs, "status": "waiting"}

    version_file = root / "windows-msi/version.m4"
    version_text = version_file.read_text(encoding="utf-8")
    package_match = re.search(r"define\(\[PACKAGE_VERSION\], \[([^]]+)\]\)", version_text)
    already_current = bool(package_match and package_match.group(1).startswith(f"{version}-"))
    if already_current and gitlink_sha(root) == release_sha:
        write_report(report_path, base_report + ["The repository already tracks this stable release."])
        return {**common_outputs, "status": "noop"}

    submodule = root / "src/openvpn"
    if run("git", "status", "--porcelain", cwd=submodule):
        raise PreparationError("src/openvpn contains local changes")
    run("git", "fetch", "--depth=1", "origin", "tag", tag, "--force", cwd=submodule)
    run("git", "checkout", "--detach", release_sha, cwd=submodule)

    patch_root = root / "tunnelblick-patches"
    for name in PATCH_NAMES:
        url = str(patches[name].get("download_url", ""))
        if not url:
            raise PreparationError(f"Tunnelblick did not provide a download URL for {name}")
        content = download(url).replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        (patch_root / name).write_bytes(content.rstrip(b"\n") + b"\n")

    major, minor, patch = (int(value) for value in version_match.groups())
    product_build = patch * 100 + 1
    version_text = replace_once(
        version_text,
        r"^define\(\[PACKAGE_VERSION\], \[[^]]+\]\)$",
        f"define([PACKAGE_VERSION], [{version}-I001-xor])",
        "PACKAGE_VERSION",
    )
    version_text = replace_once(
        version_text,
        r"^define\(\[PRODUCT_VERSION\], \[[^]]+\]\)$",
        f"define([PRODUCT_VERSION], [{major}.{minor}.{product_build}])",
        "PRODUCT_VERSION",
    )
    product_code = str(uuid.uuid4()).upper()
    version_text = replace_once(
        version_text,
        r"^define\(\[PRODUCT_CODE\], \[\{[^}]+\}\]\)$",
        f"define([PRODUCT_CODE], [{{{product_code}}}])",
        "PRODUCT_CODE",
    )
    version_file.write_text(version_text, encoding="utf-8")

    patch_readme = patch_root / "README.md"
    readme_text = patch_readme.read_text(encoding="utf-8")
    readme_text = re.sub(
        r"openvpn-\d+\.\d+\.\d+/patches",
        f"openvpn-{version}/patches",
        readme_text,
    )
    patch_readme.write_text(readme_text, encoding="utf-8")

    write_report(
        report_path,
        base_report
        + [
            "### Prepared changes",
            "",
            f"- Pin `src/openvpn` to stable tag `{tag}`.",
            "- Refresh Tunnelblick XOR patches 02 through 06 from the pinned Tunnelblick commit.",
            "- Keep the repository-specific DCO patch and validate it with the full patch set.",
            f"- Set the MSI package version to `{version}-I001-xor`.",
            f"- Set the MSI product version to `{major}.{minor}.{product_build}` and generate a new product code.",
        ],
    )
    return {**common_outputs, "status": "prepared"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path, default=Path("stable-update-report.md"))
    args = parser.parse_args()

    root = args.root.resolve()
    report_path = args.report.resolve()
    try:
        outputs = prepare(root, report_path)
        write_outputs(args.output, outputs)
        print(json.dumps(outputs, indent=2))
        return 0
    except PreparationError as error:
        write_report(report_path, ["## Stable update preparation failed", "", "```text", str(error), "```"])
        write_outputs(
            args.output,
            {
                "version": "unknown",
                "report": str(report_path),
                "status": "error",
            },
        )
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

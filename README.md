# OpenVPN for Windows with XOR obfuscation (unofficial)

[![Build](https://github.com/PRIHLOP/openvpn-windows-xor/actions/workflows/build.yaml/badge.svg)](https://github.com/PRIHLOP/openvpn-windows-xor/actions/workflows/build.yaml)

> [!IMPORTANT]
> **This is an unofficial repository.** It is not affiliated with, endorsed by or
> supported by OpenVPN, Inc., the OpenVPN community project, or the Tunnelblick
> project. The installers built here are patched, unofficial builds of the
> OpenVPN Windows client - do not report problems with them to the OpenVPN or
> Tunnelblick issue trackers or support channels. "OpenVPN" is a registered
> trademark of OpenVPN, Inc.
>
> CI artifacts from ordinary pushes and pull requests are intentionally
> unsigned, so Windows SmartScreen will warn about them. Release installers are
> built in the protected signing job described below.

## What this is

A fork of the official build system,
[OpenVPN/openvpn-build](https://github.com/OpenVPN/openvpn-build), that applies
the [Tunnelblick XOR obfuscation patch](https://tunnelblick.net/cOpenvpn_xorpatch.html)
to the OpenVPN sources before packaging the Windows MSI installers. Everything
except [`tunnelblick-patches/`](tunnelblick-patches/), this README and the CI
workflow is upstream code, kept as close to upstream as possible.

The patch adds one configuration directive, `scramble`, which obfuscates the
OpenVPN stream so that it does not look like OpenVPN to simple traffic
classifiers. It is **obfuscation, not security**: it adds no cryptographic
protection whatsoever, and the mask is not a secret. Everything that actually
protects the tunnel is OpenVPN's normal TLS/data-channel crypto.

If you need a server that speaks the same obfuscation, see
[docker-openvpn-xor](https://github.com/lawtancool/docker-openvpn-xor).

## Configuration

Add the identical `scramble` line to the client and the server configuration -
if they differ, the connection simply never completes its handshake:

```
scramble xormask <mask>     # XOR every byte with the repeating mask
scramble xorptrpos          # XOR every byte with its position in the packet
scramble reverse            # reverse the packet payload
scramble obfuscate <mask>   # all three of the above combined
```

`scramble <mask>` without a method name is accepted as a synonym for
`scramble xormask <mask>`.

Using `scramble` automatically disables data channel offload (DCO), which is
on by default on Windows since OpenVPN 2.6. This is required: with DCO the data
channel is handled inside the kernel driver and would bypass the obfuscation
entirely. OpenVPN logs the decision at `--verb 4`:

```
Note: --scramble disables data channel offload.
```

Expect the throughput of a pre-DCO OpenVPN client, since obfuscated traffic
cannot use the offload path.

## Installers

Every push builds unsigned x86, amd64 and arm64 MSI packages; download them from
the artifacts of a [Build workflow run](https://github.com/PRIHLOP/openvpn-windows-xor/actions/workflows/build.yaml).
Tags matching `openvpn-install-*-xor` rebuild the installers in the protected
`release-signing` environment, sign them through Google Cloud KMS, attest their
GitHub build provenance, and publish the signed MSI files and SHA-256 checksum
files on the [releases page](https://github.com/PRIHLOP/openvpn-windows-xor/releases).
Verify a downloaded installer with `sha256sum --check <file>.msi.sha256` and,
when GitHub CLI is available, `gh attestation verify <file>.msi --repo
PRIHLOP/openvpn-windows-xor`.

Repository administrators must require approval for the `release-signing`
environment and restrict it to protected release tags. The Google Workload
Identity Provider must independently restrict tokens to this repository, the
release-tag ref, the `push` event, and the signing workflow. Branch and tag
protection are security controls configured in GitHub, not in this repository.

These packages carry their own MSI upgrade codes and are published as
`openvpn-windows-xor (unofficial build)`, so they neither replace nor get
replaced by official OpenVPN installations. Installing both at once is still a
bad idea - they share the `OpenVPN` install directory and service names.

## Building

The build runs on Windows and is documented upstream in
[`windows-msi/README.rst`](windows-msi/README.rst). In short:

```powershell
git clone --recurse-submodules https://github.com/PRIHLOP/openvpn-windows-xor.git
cd openvpn-windows-xor\src\openvpn
Get-ChildItem ..\..\tunnelblick-patches\*.diff | Sort-Object Name | ForEach-Object {
    git apply --ignore-whitespace -v $_.FullName
}
cd ..\..\windows-msi
.\build-and-package.ps1 -arch amd64
```

The patches must be applied to `src/openvpn` before `build-and-package.ps1`
runs; that is the only difference from an upstream build.

## Maintenance

OpenVPN and its dependencies are git submodules pinned to exact commits under
`src/`. The patch set is maintained against the pinned `src/openvpn` commit, so
moving that pin is what breaks it.
[`tunnelblick-patches/README.md`](tunnelblick-patches/README.md) explains what
each patch does, how the patches differ from Tunnelblick's originals, and how to
rebase them.

The `patch-check` CI job applies the patches, builds the patched OpenVPN on
Linux and runs its unit tests, so a submodule bump that breaks the patch set
fails in a couple of minutes instead of at the end of a full MSI build.

To pull in upstream changes:

```sh
git remote add ovpn-build https://github.com/OpenVPN/openvpn-build.git
git fetch ovpn-build master
git merge ovpn-build/master
```

Expect conflicts in `.github/workflows/build.yaml` (keep upstream's `msvc` job,
re-add the patch step and the `patch-check` job) and in
`windows-msi/version.m4`, where the publisher, the `-xor` package version suffix
and the fork's own MSI upgrade codes must survive the merge. Re-verify the
patches afterwards - a merge also moves the submodule pins.

## Licensing

This repository is distributed under the GNU General Public License version 2 -
see [`LICENSE`](LICENSE). That covers the build scripts inherited from
openvpn-build, the patches (Tunnelblick and OpenVPN are both GPLv2), and the
changes made here.

The packages produced by the build additionally bundle third-party components
under their own licenses - OpenSSL, tap-windows6, ovpn-dco-win, Easy-RSA,
OpenVPN-GUI and the Microsoft Visual C++ runtime among them. See
[`windows-msi/doc/bundled-licenses.txt`](windows-msi/doc/bundled-licenses.txt).

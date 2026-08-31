# Tunnelblick XOR ("scramble") patches

This directory holds the only reason this fork of
[OpenVPN/openvpn-build](https://github.com/OpenVPN/openvpn-build) exists: the
Tunnelblick XOR obfuscation patch, rebased onto the OpenVPN commit that the
`src/openvpn` submodule pins.

Both CI jobs in [`../.github/workflows/build.yaml`](../.github/workflows/build.yaml)
apply every `*.diff` in this directory, in filename order, with
`git apply --ignore-whitespace`, before anything is built.

## What each patch does

| Patch | Files | Contents |
| --- | --- | --- |
| `02-…-a` | `forward.c` | passes the `scramble` parameters into the link read/write calls |
| `03-…-b` | `options.c` | the `scramble` directive, its defaults, its environment variables and its `--verb 4` display |
| `04-…-c` | `options.h` | `xormethod` / `xormask` / `xormasklen` in `struct connection_entry` |
| `05-…-d` | `socket.c` | `buffer_mask()`, `buffer_xorptrpos()`, `buffer_reverse()` |
| `06-…-e` | `socket.h` | applies those transforms in `link_socket_read()` / `link_socket_write()` |
| `07-openvpn-xor-disable-dco` | `dco.c` | **not from Tunnelblick** - makes `scramble` disable data channel offload |

Configuration syntax (see <https://tunnelblick.net/cOpenvpn_xorpatch.html>):

```
scramble xormask <mask>   # xormethod 1
scramble xorptrpos        # xormethod 2
scramble reverse          # xormethod 3
scramble obfuscate <mask> # xormethod 4
```

Client and server must use the identical `scramble` line; a mismatch looks like a
peer that never completes the TLS handshake.

## Why patch 07 exists

With data channel offload (DCO, `ovpn-dco-win`, enabled by default on Windows
since OpenVPN 2.6) the data channel is handled by the kernel driver and never
passes through `link_socket_read()` / `link_socket_write()`. Only the control
channel would be obfuscated, which breaks the connection against an
xor-patched server. Patch 07 therefore makes `--scramble` turn DCO off, exactly
the way `--fragment` and `--http-proxy` already do, and logs:

```
Note: --scramble disables data channel offload.
```

Tunnelblick does not need this patch because DCO does not exist on macOS.

## Provenance and local changes

Patches a-e come from Tunnelblick's
[`third_party/sources/openvpn/openvpn-2.7.6/patches`](https://github.com/Tunnelblick/Tunnelblick/tree/main/third_party/sources/openvpn/openvpn-2.7.6/patches).
They are **not** all byte-identical copies. Tunnelblick's patch files retain
some OpenVPN 2.6.x context even in its 2.7.6 directory, so patch 03 is rebased
onto the pinned 2.7.6 tag where connection environment handling changed.
Additionally, `strlen()` results are cast to `int` and `*b ^ i+1` is written
  `*b ^ ((i + 1) & 0xff)`, so the patch compiles warning-free. Neither change
  alters behaviour - `+` already bound tighter than `^`, and the result was
  truncated to `uint8_t` by the assignment anyway.

Tunnelblick's `10-route-gateway-dhcp.diff` is macOS-specific and is not used here.

## Rebasing the patches

The patches only need attention when the `src/openvpn` submodule is bumped. The
`patch-check` CI job catches breakage, and reproducing it locally is cheap:

```sh
git submodule update --init src/openvpn
cd src/openvpn
for p in ../../tunnelblick-patches/*.diff; do
    git apply --ignore-whitespace --check -v "$p" || echo "FAILS: $p"
done
```

Then apply what still applies, hand-edit the rejected hunks into the tree, and
regenerate the affected patch from the checkout, for example:

```sh
git diff -- src/openvpn/socket.h > ../../tunnelblick-patches/06-tunnelblick-openvpn_xorpatch-e.diff
```

Keep one patch per topic, keep the file-to-patch mapping in the table above, and
keep the files LF-only (`.gitattributes` enforces `*.diff eol=lf`; CRLF makes
`git apply` fail).

Before pushing a rebase, run the same checks CI does - build the patched tree,
run OpenVPN's unit tests, and confirm that a `scramble`d tunnel actually comes
up between two patched instances.

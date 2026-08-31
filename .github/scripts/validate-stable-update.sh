#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
openvpn_dir="$repo_root/src/openvpn"

cd "$openvpn_dir"
for patch in "$repo_root"/tunnelblick-patches/*.diff; do
    echo "Applying $(basename "$patch")"
    git apply --ignore-whitespace -v "$patch"
done

autoreconf -ivf
./configure --disable-lzo
make -j"$(nproc)" 2>&1 | tee /tmp/openvpn-stable-build.log

if grep -iE 'warning' /tmp/openvpn-stable-build.log \
    | grep -E 'socket\.(c|h)|forward\.c|options(_show)?\.c|dco\.c'; then
    echo "FAIL: patched files produce compiler warnings"
    exit 1
fi

make -C tests/unit_tests check

printf 'user\npass\n' > /tmp/openvpn-stable-creds
chmod 600 /tmp/openvpn-stable-creds
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout /tmp/openvpn-stable-ca.key -out /tmp/openvpn-stable-ca.crt \
    -days 1 -subj '/CN=OpenVPN stable update test' >/dev/null 2>&1
chmod 600 /tmp/openvpn-stable-ca.key

for method in "xormask KEY" "xorptrpos" "reverse" "obfuscate KEY"; do
    read -r -a scramble_args <<< "$method"
    output=$(timeout 10 ./src/openvpn/openvpn --dev tun --client --remote 127.0.0.1 \
        --auth-user-pass /tmp/openvpn-stable-creds --ca /tmp/openvpn-stable-ca.crt \
        --scramble "${scramble_args[@]}" 2>&1 || true)
    if grep -qi "Options error" <<< "$output"; then
        echo "FAIL: scramble $method rejected"
        tail -3 <<< "$output"
        exit 1
    fi
    echo "ok: scramble $method"
done

output=$(timeout 10 ./src/openvpn/openvpn --verb 4 --dev tun --client --remote 127.0.0.1 \
    --auth-user-pass /tmp/openvpn-stable-creds --ca /tmp/openvpn-stable-ca.crt \
    --scramble xormask KEY 2>&1 || true)
grep -q -- "--scramble disables data channel offload" <<< "$output" \
    || { echo "FAIL: --scramble did not disable DCO"; exit 1; }
echo "ok: --scramble disables DCO"

dnl ============================================================
dnl Downloadables
dnl ============================================================

dnl TAP-Windows binaries
dnl renovate: datasource=github-releases depName=OpenVPN/tap-windows6
define([PRODUCT_TAP_WIN_VERSION],           [9.27.0])
dnl Note: Not handled by renovate
define([PRODUCT_TAP_WIN_INSTALLER_VERSION], [I0])
define([PRODUCT_TAP_WIN_COMPONENT_ID],      [tap0901])
define([PRODUCT_TAP_WIN_NAME],              [TAP-Windows])
define([PRODUCT_TAP_WIN_SHA256_i386],       [6df6ec3b16118d34b676bd5e59a5ce9f00ba38d107df16e658d2a571c94400a1])
define([PRODUCT_TAP_WIN_SHA256_amd64],      [0f52d8e2b22a0b827b0d5f1e23077dc53f2b41b67839737c39503dc20c435063])
define([PRODUCT_TAP_WIN_SHA256_arm64],      [245407ff0fac01d9095ef54a3a849c030eaf22e028bfd593574c78a4b5ac3699])

dnl ovpn-dco binaries
dnl renovate: datasource=github-releases depName=OpenVPN/ovpn-dco-win
define([PRODUCT_OVPN_DCO_VERSION],     [2.8.6])
define([PRODUCT_OVPN_DCO_SHA256_x86],   [99f9d029c6ea49003b88917bdea5be9b2635985b1d16975fa73b3e748eeaffe3])
define([PRODUCT_OVPN_DCO_SHA256_amd64], [8add48ff3ed38f34f5259b4e9d365c899fd60edcf81750a5690fb5126621f614])
define([PRODUCT_OVPN_DCO_SHA256_arm64], [68aa9a0ac06b34b87d43ed6f16b74c39ebc48cf57970774c6b8650c21c16e8de])

dnl OpenVPNServ2.exe binary
dnl renovate: datasource=github-releases depName=OpenVPN/openvpnserv2 versioning=loose
define([OVPNSERV2_VERSION], [2.0.1.0])
define([OVPNSERV2_SHA256], [9bd841de7ca24b70793a271ee3df98c29a7274331af740d4317edfe4678dfd79])

dnl Easy-RSA binaries:
dnl URL to .zip file containing "easy-rsa-[EASYRSA_VERSION]" folder with Easy-RSA.
dnl The OpenSSL binaries, which come with Easy-RSA, are not used by Openvpn-build.
dnl The only binaries which Openvpn-build uses from Easy-RSA, are the *nix style
dnl (32bit only) binaries for Windows, from easy-rsa/distro/windows/bin.
dnl Further details: easy-rsa/distro/windows/Licensing/mksh-Win32.txt
dnl renovate: datasource=github-releases depName=OpenVPN/easy-rsa
define([EASYRSA_VERSION], [3.2.6])
define([EASYRSA_SHA256], [1629b6f1cd4b866d311910b35a570493f8d52e5cb031f93776c199a14ca4c96d])

dnl ============================================================
dnl MSI Provisioning
dnl ============================================================

dnl Define the product name and publisher.
define([PRODUCT_NAME],      [OpenVPN])
define([PRODUCT_PUBLISHER], [openvpn-windows-xor (unofficial build)])

dnl The package version as displayed by UI and used in filenames (no spaces, please).
define([PACKAGE_VERSION], [2.7.7-I001-xor])

dnl The MSI product version in the form of n[.n[.n]] (numbers only).
dnl The third field is 100*openvpn bugfix release + MSI build number.
dnl So for the 2nd MSI build for OpenVPN 2.6.3 use 2.6.302
define([PRODUCT_VERSION], [2.7.701])

dnl The MSI product code MUST change on each product release.
define([PRODUCT_CODE], [{955B6891-CD11-4E69-8A2B-8C0C7DCB1B65}])

dnl The MSI upgrade codes MUST persist for all versions of the same product line.
dnl These are deliberately NOT the upstream OpenVPN, Inc. upgrade codes: this is an
dnl unofficial build, and reusing the official codes would make these packages
dnl silently upgrade (or be upgraded by) official OpenVPN installations.
define([UPGRADE_CODE_x86],   [{095A7F10-A48E-4AFA-A73E-9521D9992D94}])
define([UPGRADE_CODE_amd64], [{F4221C42-93CD-4EF7-BEC9-05B6B5C0E341}])
define([UPGRADE_CODE_arm64], [{FAA007E4-1F8D-4AF2-9AEA-B558B72FB266}])

dnl OpenVPN configration file extension (e.g. conf, ovpn...)
define([CONFIG_EXTENSION], [ovpn])

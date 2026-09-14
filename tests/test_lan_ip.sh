#!/usr/bin/env bash
# `planetai reticulum` on an Arch node printed "host  (or ) port 4242" — the one line that tells you where to
# point Sideband, naming nowhere. lan_ip() read `hostname -I`, which is net-tools; Arch's inetutils hostname
# rejects -I outright. Runs the real lan_ip() lifted out of bin/planetai against both hostname flavours, with
# `ip` and `hostname` stubbed on PATH, so the test is offline and runs the same on macOS and Linux.
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0
d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT

# What iproute2 actually answered on the Omarchy node, 14 September 2026.
printf '%s\n' '#!/bin/sh' \
  'echo "1.0.0.0 via 192.168.4.1 dev wlp3s0 src 192.168.4.254 uid 1000"' \
  'echo "    cache "' > "$d/ip"

# Arch: inetutils hostname has no -I and says so on stderr, exit 1.
printf '%s\n' '#!/bin/sh' \
  'case "$1" in -I) echo "hostname: invalid option -- '"'"'I'"'"'" >&2; exit 1;; esac' \
  'echo omarchy' > "$d/hostname-arch"
# Debian: net-tools hostname answers with every address, space separated.
printf '%s\n' '#!/bin/sh' \
  'case "$1" in -I) echo "10.0.0.7 172.17.0.1 ";; *) echo deb;; esac' > "$d/hostname-deb"

# lan_ip() alone, out of the real file: its definition to the closing brace. Never a retyped copy.
sed -n '/^lan_ip() {/,/^}$/p' bin/planetai > "$d/lan_ip.sh"
grep -q 'route get' "$d/lan_ip.sh" || { echo "  FAIL could not lift lan_ip() out of bin/planetai"; exit 1; }

# uname is stubbed too: the Linux branch must be exercised on the Mac this usually runs on.
run() {   # run <hostname stub> [--no-ip]
  local b="$d/b"; rm -rf "$b"; mkdir -p "$b"
  cp "$1" "$b/hostname"; chmod +x "$b/hostname"
  # "no iproute2" has to be a stub that fails, not an absent file: the function still needs sed, awk and grep
  # from /usr/bin, and on a Linux box `ip` is reachable there too — so leaving it out of $b removed nothing,
  # and both fallback cases quietly read the CI runner's real address instead of the stub's.
  if [[ "${2:-}" == "--no-ip" ]]; then
    printf '%s\n' '#!/bin/sh' 'echo "sh: ip: command not found" >&2; exit 127' > "$b/ip"
  else
    cp "$d/ip" "$b/ip"
  fi
  chmod +x "$b/ip"
  printf '%s\n' '#!/bin/sh' 'echo Linux' > "$b/uname"; chmod +x "$b/uname"
  PATH="$b:/usr/bin:/bin" bash -c '. "$1"; lan_ip' _ "$d/lan_ip.sh" 2>/dev/null
}

echo "lan_ip: the node has to be able to say where it is"
chk() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1 (got: '$3')"; fails=$((fails+1)); fi; }

a="$(run "$d/hostname-arch")"
chk "Arch (inetutils hostname, no -I) still finds the address" '[[ "$a" == "192.168.4.254" ]]' "$a"
b="$(run "$d/hostname-deb")"
chk "Debian reads the route too, not the old -I list"          '[[ "$b" == "192.168.4.254" ]]' "$b"
c="$(run "$d/hostname-deb" --no-ip)"
chk "and with no iproute2 at all it falls back to -I"          '[[ "$c" == "10.0.0.7" ]]' "$c"
e="$(run "$d/hostname-arch" --no-ip)"
chk "neither available: empty, so callers print their placeholder" '[[ -z "$e" ]]' "$e"

# The Sideband line is what the blank was visible in: it must never print a bare "(or )".
sed -n '/^cmd_reticulum() {/,/^}$/p' bin/planetai > "$d/ret.sh"
chk "the Sideband line guards an unset MESH_NAME" \
  '! grep -q "(or \$(envget MESH_NAME))" "$d/ret.sh"' "$(grep -c 'or \$(envget' "$d/ret.sh")"

[[ $fails -eq 0 ]] && echo "  lan_ip answers on both hostname flavours" || echo "  $fails failed"
exit $(( fails > 0 ))

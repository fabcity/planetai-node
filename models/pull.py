"""python pull.py <name>: fetch one catalogue model at its pinned revision and check its weights.

Run on purpose, with the network on (`planetai models pull`); the serving container never downloads.
Exit 1, with what was downloaded removed, on an unknown name or a model.safetensors that is not the pinned file.
`--have <name>` exits 0 when that model's weights are on this volume; `--remove <name>` deletes only that model's folder.
"""
import json
import sys
from pathlib import Path

import core

FILES = ["config.json", "model.safetensors"]     # all either pipeline reads; the rest of the repository stays there


def main(name):
    cat = json.load(open(core.CATALOGUE))
    entry = core.pinned(name, cat)
    if entry is None:
        print(f"unknown model {name}; the catalogue has: {', '.join(cat)}", file=sys.stderr)
        return 1
    from huggingface_hub import snapshot_download
    snap = Path(snapshot_download(name, revision=entry["revision"], allow_patterns=FILES))
    err = core.verify(name, snap, cat)
    if err:
        print(err, file=sys.stderr)
        return 1
    print(f"{name} at {entry['revision']}: sha256 ok")
    return 0


def other(flag, name):
    cat = json.load(open(core.CATALOGUE))
    if flag == "--have":
        return 0 if core.have(name, cat) else 1
    err = core.remove(name, cat)
    if err:
        print(err, file=sys.stderr)
        return 1
    print(f"{name}: weights removed")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(a[0]) if len(a) == 1 else other(*a) if len(a) == 2 and a[0] in ("--have", "--remove") else 1)

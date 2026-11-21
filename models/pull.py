"""python pull.py <name>: fetch one catalogue model at its pinned revision and check its weights.

Run on purpose, with the network on (`planetai models pull`); the serving container never downloads.
Exit 1, with what was downloaded removed, on an unknown name or a model.safetensors that is not the pinned file.
"""
import json
import sys
from pathlib import Path

import core


def main(name):
    cat = json.load(open(core.CATALOGUE))
    entry = core.pinned(name, cat)
    if entry is None:
        print(f"unknown model {name}; the catalogue has: {', '.join(cat)}", file=sys.stderr)
        return 1
    from huggingface_hub import snapshot_download
    snap = Path(snapshot_download(name, revision=entry["revision"]))
    err = core.verify(name, snap, cat)
    if err:
        print(err, file=sys.stderr)
        return 1
    print(f"{name} at {entry['revision']}: sha256 ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else 1)

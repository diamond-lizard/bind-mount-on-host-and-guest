#!/usr/bin/env python3
"""Managed by bind-mounts.yml (ansible). Helper: ensure ONE guest bind mount.

Idempotent. Refuses to touch any mount it did not create.
Identity check: a bind mount shares the device and inode of its source, so the
helper compares stat(dev, ino) of the target against the share source. (The
guest mount table reports source as 'none' for these binds, so source paths
cannot be compared.)

Usage: guest-mount-one.py <target> <share-source> <uid> <gid> <readonly>
Exit codes: 0 = already mounted or mounted now; 3 = foreign mount (never touched).
"""
import os
import subprocess
import sys


def is_mountpoint(path):
    probe = subprocess.run(
        ["findmnt", "-rn", "-o", "TARGET", "-M", path],
        capture_output=True, text=True,
    )
    return probe.returncode == 0 and probe.stdout.strip() == path


def stat_id(path):
    st = os.stat(path)
    return f"{st.st_dev}:{st.st_ino}"


def main():
    if len(sys.argv) != 6:
        print("usage: guest-mount-one.py <target> <share> <uid> <gid> <readonly>", file=sys.stderr)
        return 2
    target, share, owner_uid, owner_gid, readonly = sys.argv[1:6]

    if is_mountpoint(target):
        if stat_id(target) == stat_id(share):
            print(f"ok: {target} already mounted from {share}")
            return 0
        print(f"FOREIGN: {target} is a mountpoint whose content differs from {share}", file=sys.stderr)
        print("FOREIGN: this helper never touches mounts it did not create; unmount it manually", file=sys.stderr)
        return 3

    existed = os.path.isdir(target)
    os.makedirs(target, exist_ok=True)
    if not existed:
        os.chown(target, int(owner_uid), int(owner_gid))
    subprocess.run(["mount", "--bind", share, target], check=True)
    if readonly == "true":
        subprocess.run(["mount", "-o", "remount,ro,bind", target], check=True)
    print(f"mounted: {target} from {share}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

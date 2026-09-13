#!/usr/bin/env python3
"""Managed by bind-mounts.yml (ansible). Helper: verify ONE guest mount.

Identity check compares device and inode of the target against the expected
share source (bind mounts share stat identity with their source).

Usage: guest-verify-one.py bind <target> <expected-share-source>
       guest-verify-one.py direct <target>
Exit codes: 0 = verified; 1 = not mounted or wrong source.
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
    if len(sys.argv) not in (3, 4):
        print("usage: guest-verify-one.py bind <target> <expected-source> | direct <target>", file=sys.stderr)
        return 2
    mode, target = sys.argv[1], sys.argv[2]
    expected = sys.argv[3] if len(sys.argv) > 3 else None

    if not is_mountpoint(target):
        print(f"verify FAIL (guest): {target} is not mounted", file=sys.stderr)
        return 1
    if mode == "bind":
        share = sys.argv[3]
        if stat_id(target) != stat_id(share):
            print(f"verify FAIL (guest): {target} does not match {share} (device:inode differ)", file=sys.stderr)
            return 1
    print(f"verify ok (guest): {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Managed by bind-mounts.yml (ansible). Helper: add, replace, or remove ONLY
the managed block in a user's .bash_profile. Every other line is preserved;
edits are atomic and keep the original owner and mode. The managed block uses
the standard ansible.builtin.blockinfile markers.

Usage: profile-manage.py apply|remove <profile-path> <uid> <gid>
Exit codes: 0 = success; 2 = refused (unbalanced markers or bad usage).
"""
import os
import sys
import tempfile

START = "# BEGIN ANSIBLE MANAGED BLOCK"
END = "# END ANSIBLE MANAGED BLOCK"
BLOCK_LINES = [
    START,
    "if [ -x /usr/local/sbin/bind-mount-on-guest.sh ]; then",
    "    sudo -n /usr/local/sbin/bind-mount-on-guest.sh",
    "fi",
    END,
]


def main():
    if len(sys.argv) != 5:
        print("usage: profile-manage.py apply|remove <profile-path> <uid> <gid>", file=sys.stderr)
        return 2
    mode, profile = sys.argv[1], sys.argv[2]
    owner_uid, owner_gid = int(sys.argv[3]), int(sys.argv[4])
    if mode not in ("apply", "remove"):
        print(f"error: unknown mode {mode!r} (use apply or remove)", file=sys.stderr)
        return 2

    if os.path.exists(profile):
        with open(profile, encoding="utf-8") as f:
            lines = f.read().splitlines()
        starts = [i for i, line in enumerate(lines) if line == START]
        ends = [i for i, line in enumerate(lines) if line == END]
        if len(starts) > 1 or len(ends) > 1 or len(starts) != len(ends):
            print(f"error: unbalanced managed markers in {profile}; refusing to edit", file=sys.stderr)
            return 2
        existed = True
    else:
        lines, starts, ends = None, [], []
        existed = False

    if mode == "remove":
        if not starts:
            print(f"no managed block in {profile}; nothing to remove")
            return 0
        new_lines = lines[: starts[0]] + lines[ends[0] + 1:]
        message = f"removed managed block from {profile}"
    elif starts:
        if lines[starts[0]: ends[0] + 1] == BLOCK_LINES:
            print(f"unchanged managed block in {profile}")
            return 0
        new_lines = lines[: starts[0]] + BLOCK_LINES + lines[ends[0] + 1:]
        message = f"updated managed block in {profile}"
    elif not existed:
        new_lines = list(BLOCK_LINES)
        message = f"created {profile} with the managed block"
    else:
        legacy = [
            i for i, line in enumerate(lines)
            if line.startswith("if [ -x ") and "bind-mount-on-guest.sh" in line
        ]
        if not legacy:
            new_lines = lines + [""] + BLOCK_LINES
            message = f"appended managed block to {profile}"
        else:
            first = legacy[0]
            last = next(
                (j for j in range(first + 1, min(first + 5, len(lines)))
                 if lines[j].rstrip() == "fi"),
                None,
            )
            if last is None:
                print(f"error: legacy bind-mount block in {profile} has no closing 'fi' within 4 lines", file=sys.stderr)
                return 2
            new_lines = lines[:first] + BLOCK_LINES + lines[last + 1:]
            message = f"replaced the legacy bind-mount block in {profile}"

    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(os.path.abspath(profile)) or ".",
        prefix=".profile-manage.",
    )
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    if existed:
        st = os.stat(profile)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.chown(tmp, st.st_uid, st.st_gid)
    else:
        os.chmod(tmp, 0o644)
        os.chown(tmp, owner_uid, owner_gid)
    os.replace(tmp, profile)
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())

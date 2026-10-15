"""Shared helper for the ``app/history.js`` node test harnesses.

``app/history.js`` imports the sibling pure modules ``ambient.js`` and
``i18n.js`` for the backup/restore normalisers. The per-test node harnesses copy
``history.js`` to a temporary ``.mjs`` file, so they must copy those siblings
too and mark the temporary directory as an ES module directory.
"""

import os
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "app")

HISTORY_DEPENDENCIES = ("ambient.js", "i18n.js")


def copy_history_dependencies(target_dir):
    """Copy ``app/history.js``'s sibling modules into ``target_dir`` and write a
    ``package.json`` so the copied ``.js`` files are treated as ES modules."""
    for name in HISTORY_DEPENDENCIES:
        shutil.copy(os.path.join(APP_DIR, name), os.path.join(target_dir, name))
    with open(os.path.join(target_dir, "package.json"), "w", encoding="utf-8") as handle:
        handle.write('{"type": "module"}\n')

#!/usr/bin/env python3
"""
bump_version.py — makes browsers load your latest CSS, JS, and pixel art.

    python3 tools/bump_version.py

Browsers keep copies of files like css/theme.css and assets/hero-scene.svg for
a while, so after you push a change some visitors (including you) may still see
the old version. Every link to those files ends in "?v=<version>". This script
sets that version to the current date and time in every page and the
stylesheet, so browsers treat them as new files.

Run it after changing anything in css/, js/, or assets/, then commit and push.
"""

import datetime
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# quoted links to these files get a ?v= tag (src="...", href="...", url("..."));
# page links like soilnode.html and mentions in comments are left alone
VERSIONED = re.compile(r'(?<=["\'])((?:\.\./)?(?:css|js|assets)/[\w.-]+\.(?:css|js|svg))(\?v=[\w-]+)?')


def main():
    version = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    files = glob.glob(os.path.join(ROOT, "*.html")) + [os.path.join(ROOT, "css", "theme.css")]
    for path in files:
        with open(path) as f:
            text = f.read()
        updated = VERSIONED.sub(lambda m: f"{m.group(1)}?v={version}", text)
        if updated != text:
            with open(path, "w") as f:
                f.write(updated)
            print(f"updated {os.path.relpath(path, ROOT)}")
    print(f"version is now {version}")


if __name__ == "__main__":
    main()

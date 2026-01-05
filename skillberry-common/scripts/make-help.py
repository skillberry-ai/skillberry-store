# Small utility for pretty-printing the Makefile targets organized by sections, with de-duplication in sections - 
# different files with same section labels have all their targets together
import re, sys
from collections import OrderedDict

sec_re = re.compile(r'^##@\s*(.*)\s*$')
tgt_re = re.compile(r'^([A-Za-z0-9_-]+):.*##\s*(.*)\s*$')

sections = OrderedDict()
seen = set()
section = "Other"
sections.setdefault(section, [])

for path in sys.argv[1:]:
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                m = sec_re.match(line)
                if m:
                    section = m.group(1).strip() or "Other"
                    sections.setdefault(section, [])
                    continue
                m = tgt_re.match(line)
                if m:
                    tgt, doc = m.group(1), m.group(2).strip()
                    key = (section, tgt)
                    if key not in seen:
                        sections[section].append((tgt, doc))
                        seen.add(key)
    except FileNotFoundError:
        pass

CYAN, BOLD, RESET = "\033[36m", "\033[1m", "\033[0m"
print("\nUsage:\n  make {}<target>{}\n".format(CYAN, RESET))
for sec, items in sections.items():
    if not items:
        continue
    print(f"{BOLD}{sec}{RESET}")
    for tgt, doc in items:
        print(f"  {CYAN}{tgt:<20}{RESET} {doc}")
    print()

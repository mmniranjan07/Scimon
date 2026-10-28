"""Regenerate scimon_db_data.py from assets/scimon_database.json (run after editing the JSON)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
db = json.load(open(os.path.join(ROOT, "assets", "scimon_database.json"), encoding="utf-8"))
with open(os.path.join(ROOT, "scimon_db_data.py"), "w", encoding="utf-8") as f:
    f.write('"""Generated from assets/scimon_database.json by tools/gen_db_module.py -- do not edit."""\nDB = ')
    f.write(repr(db))
print("scimon_db_data.py regenerated")

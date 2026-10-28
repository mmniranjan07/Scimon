"""Deprecated source module -- the generated species tables are no longer used.

The scimon_database.json package (assets/scimon_database.json, mirrored in scimon_db_data.py) is the
authoritative catalog since the wild-encounters integration.  The 100 procedurally generated entries this
module used to provide (and the CRC-seeded evolution chains they fed in data.py) have been superseded by the
audited database: all 268 source-registered forms keep their ids, dex numbers, stats and evolution levels
inside the database, and the 59 added first forms come from the approved art (proposed_new_art_stage).

Kept as an import-safe stub so any stray import keeps working.  Nothing in the game reads from here."""
SPECIES_TABLE = []


def expanded_species():
    """Legacy hook: no longer generates species.  See assets/scimon_database.json."""
    return []

#!/usr/bin/env python3
"""
Migration Chain Auditor
Analyzes Alembic migration files to detect broken chains, orphaned migrations, and other issues.
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class MigrationAuditor:
    """Audit Alembic migration files for integrity issues"""

    def __init__(self, versions_dir: str):
        self.versions_dir = Path(versions_dir)
        self.migrations: Dict[str, Dict] = {}
        self.chains: List[List[str]] = []
        self.issues: List[str] = []

    def parse_migration_file(self, filepath: Path) -> Optional[Dict]:
        """Extract revision metadata from migration file"""
        try:
            with open(filepath, "r") as f:
                content = f.read()

            # Handle both old style (revision = "...") and new style with type hints (revision: str = "...")
            rev_match = re.search(r"revision\s*(?::\s*\w+\s*)?=\s*['\"]([^'\"]+)['\"]", content)
            down_match = re.search(
                r"down_revision\s*(?::\s*[^=]+)?\s*=\s*(?:['\"]([^'\"]+)['\"]|None)", content
            )

            if not rev_match:
                return None

            revision = rev_match.group(1)
            down_revision = down_match.group(1) if down_match and down_match.group(1) else None

            # Extract description from docstring or filename
            desc_match = re.search(r'"""([^"]+)"""', content)
            description = desc_match.group(1).strip() if desc_match else filepath.stem

            return {
                "filename": filepath.name,
                "revision": revision,
                "down_revision": down_revision,
                "description": description,
            }
        except Exception as e:
            self.issues.append(f"❌ Failed to parse {filepath.name}: {e}")
            return None

    def load_migrations(self):
        """Load all migration files"""
        for filepath in sorted(self.versions_dir.glob("*.py")):
            if filepath.name == "__init__.py":
                continue

            migration = self.parse_migration_file(filepath)
            if migration:
                rev = migration["revision"]
                if rev in self.migrations:
                    self.issues.append(
                        f"❌ DUPLICATE REVISION: {rev} in both "
                        f"{self.migrations[rev]['filename']} and {migration['filename']}"
                    )
                self.migrations[rev] = migration

    def build_chains(self):
        """Build migration chains from root to head"""
        # Find all roots (no down_revision)
        roots = [rev for rev, mig in self.migrations.items() if mig["down_revision"] is None]

        if len(roots) > 1:
            self.issues.append(
                f"⚠️  MULTIPLE ROOTS: Found {len(roots)} root migrations (expected 1)"
            )
            for root in roots:
                self.issues.append(f"   - {root}: {self.migrations[root]['filename']}")

        # Build each chain
        for root in roots:
            chain = self._build_chain_from(root)
            self.chains.append(chain)

    def _build_chain_from(self, start_rev: str) -> List[str]:
        """Build chain starting from a revision"""
        chain = [start_rev]
        current = start_rev

        # Find next revision
        while True:
            next_rev = self._find_next_revision(current)
            if not next_rev:
                break
            chain.append(next_rev)
            current = next_rev

        return chain

    def _find_next_revision(self, rev: str) -> Optional[str]:
        """Find revision that depends on given revision"""
        for candidate_rev, mig in self.migrations.items():
            if mig["down_revision"] == rev:
                return candidate_rev
        return None

    def find_broken_references(self):
        """Find migrations referencing non-existent revisions"""
        for rev, mig in self.migrations.items():
            down_rev = mig["down_revision"]
            if down_rev and down_rev not in self.migrations:
                self.issues.append(
                    f"❌ BROKEN REFERENCE: {mig['filename']} "
                    f"references non-existent revision '{down_rev}'"
                )

    def find_orphaned_migrations(self):
        """Find migrations not in any chain from root"""
        all_in_chains = set()
        for chain in self.chains:
            all_in_chains.update(chain)

        orphaned = set(self.migrations.keys()) - all_in_chains
        if orphaned:
            self.issues.append(
                f"⚠️  ORPHANED MIGRATIONS: {len(orphaned)} migration(s) not connected to main chain"
            )
            for rev in orphaned:
                mig = self.migrations[rev]
                self.issues.append(
                    f"   - {rev}: {mig['filename']} (down_revision: {mig['down_revision']})"
                )

    def print_report(self):
        """Print audit report"""
        print("=" * 80)
        print("MIGRATION CHAIN AUDIT REPORT")
        print("=" * 80)
        print()

        print(f"📊 Total Migrations: {len(self.migrations)}")
        print(f"📈 Number of Chains: {len(self.chains)}")
        print()

        # Print chains
        for i, chain in enumerate(self.chains, 1):
            print(f"Chain {i} ({len(chain)} migrations):")
            for j, rev in enumerate(chain):
                mig = self.migrations[rev]
                prefix = "└─" if j == len(chain) - 1 else "├─"
                head_marker = " (HEAD)" if j == len(chain) - 1 else ""
                print(f"  {prefix} {rev[:12]:<12} | {mig['filename']}{head_marker}")
            print()

        # Print issues
        if self.issues:
            print("=" * 80)
            print(f"⚠️  ISSUES FOUND: {len(self.issues)}")
            print("=" * 80)
            for issue in self.issues:
                print(issue)
            print()
            return 1
        else:
            print("✅ No issues found! Migration chain is clean.")
            print()
            return 0

    def run(self) -> int:
        """Run full audit"""
        self.load_migrations()
        self.build_chains()
        self.find_broken_references()
        self.find_orphaned_migrations()
        return self.print_report()


def main():
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    versions_dir = backend_dir / "alembic" / "versions"

    if not versions_dir.exists():
        print(f"❌ Migrations directory not found: {versions_dir}")
        return 1

    auditor = MigrationAuditor(str(versions_dir))
    return auditor.run()


if __name__ == "__main__":
    sys.exit(main())

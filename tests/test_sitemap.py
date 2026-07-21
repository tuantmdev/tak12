import datetime as dt
import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "sitemap.xml"
CONTENT_CONTRACT = ROOT / "sitemap-content.json"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def canonical_page_path(location, root=ROOT):
    parsed = urlparse(location)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "tak-12.com"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Not a canonical site URL: {location}")
    if parsed.path == "/":
        return root / "index.html"
    if not re.fullmatch(r"/[a-z0-9-]+/", parsed.path):
        raise ValueError(f"Canonical URL must contain exactly one safe slug: {location}")
    return root / parsed.path.strip("/") / "index.html"


def validate_historical_coupling(current, previous):
    if previous is None:
        return
    for location in set(current) & set(previous):
        digest_changed = current[location]["sha256"] != previous[location]["sha256"]
        lastmod_changed = current[location]["lastmod"] != previous[location]["lastmod"]
        if digest_changed != lastmod_changed:
            raise AssertionError(
                f"{location}: sha256 and lastmod must change together relative to the baseline"
            )


def read_contract_at_revision(revision, run_git=subprocess.run):
    common = {"cwd": ROOT, "capture_output": True, "text": True, "check": False}
    revision_check = run_git(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"], **common
    )
    if revision_check.returncode != 0:
        detail = revision_check.stderr.strip() or "revision is unavailable"
        raise RuntimeError(f"Cannot inspect sitemap contract at {revision}: {detail}")

    tree_check = run_git(
        ["git", "ls-tree", "--name-only", revision, "--", "sitemap-content.json"],
        **common,
    )
    if tree_check.returncode != 0:
        detail = tree_check.stderr.strip() or "git ls-tree failed"
        raise RuntimeError(f"Cannot inspect sitemap contract at {revision}: {detail}")
    if not tree_check.stdout.strip():
        return None

    result = run_git(
        ["git", "show", f"{revision}:sitemap-content.json"], **common
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git show failed"
        raise RuntimeError(f"Cannot inspect sitemap contract at {revision}: {detail}")
    return result.stdout


def resolve_baseline_revision():
    result = subprocess.run(
        ["git", "merge-base", "origin/main", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision):
        detail = result.stderr.strip() or "git merge-base returned no commit"
        raise RuntimeError(f"Cannot resolve sitemap contract baseline: {detail}")
    return revision


def load_baseline_contract(
    resolve_revision=resolve_baseline_revision,
    read_revision=read_contract_at_revision,
):
    content = read_revision(resolve_revision())
    return json.loads(content) if content is not None else None


class SitemapTests(unittest.TestCase):
    def sitemap_entries(self):
        document = ElementTree.parse(SITEMAP)
        entries = {}
        for node in document.getroot().findall("sm:url", NS):
            location = node.findtext("sm:loc", namespaces=NS)
            lastmod = node.findtext("sm:lastmod", namespaces=NS)
            self.assertNotIn(location, entries, f"Duplicate sitemap URL: {location}")
            entries[location] = lastmod
        return entries

    def test_sitemap_has_unique_canonical_urls_and_valid_lastmod_dates(self):
        entries = self.sitemap_entries()
        self.assertEqual(9, len(entries))
        for location, lastmod in entries.items():
            with self.subTest(location=location):
                parsed = urlparse(location)
                self.assertEqual("https", parsed.scheme)
                self.assertEqual("tak-12.com", parsed.netloc)
                self.assertFalse(parsed.query)
                self.assertFalse(parsed.fragment)
                self.assertEqual(parsed.path, "/" if parsed.path == "/" else f"/{parsed.path.strip('/')}/")
                self.assertEqual(lastmod, dt.date.fromisoformat(lastmod).isoformat())

        self.assertEqual(
            "2026-07-16",
            entries["https://tak-12.com/tak12-cambridge-ket-pet-flyers/"],
        )
        self.assertEqual(
            "2026-07-17",
            entries["https://tak-12.com/tak12-co-tot-khong/"],
        )

    def test_canonical_url_deterministically_selects_only_its_index_page(self):
        site_root = Path("/site")
        self.assertEqual(
            site_root / "index.html",
            canonical_page_path("https://tak-12.com/", site_root),
        )
        self.assertEqual(
            site_root / "lesson" / "index.html",
            canonical_page_path("https://tak-12.com/lesson/", site_root),
        )
        for location in (
            "https://tak-12.com/lesson/other/",
            "https://tak-12.com/../secret/",
            "https://other.example/lesson/",
        ):
            with self.subTest(location=location):
                with self.assertRaises(ValueError):
                    canonical_page_path(location, site_root)

    def test_content_contract_has_no_arbitrary_source_path(self):
        contract = json.loads(CONTENT_CONTRACT.read_text(encoding="utf-8"))
        for location, metadata in contract.items():
            with self.subTest(location=location):
                self.assertEqual({"sha256", "lastmod"}, set(metadata))

    def test_history_rejects_hash_only_or_lastmod_only_contract_changes(self):
        previous = {
            "https://tak-12.com/": {"sha256": "old-hash", "lastmod": "2026-07-12"}
        }
        hash_only = {
            "https://tak-12.com/": {"sha256": "new-hash", "lastmod": "2026-07-12"}
        }
        lastmod_only = {
            "https://tak-12.com/": {"sha256": "old-hash", "lastmod": "2026-07-13"}
        }
        for current in (hash_only, lastmod_only):
            with self.subTest(current=current):
                with self.assertRaises(AssertionError):
                    validate_historical_coupling(current, previous)

    def test_history_allows_coupled_changes_and_initial_bootstrap(self):
        previous = {
            "https://tak-12.com/": {"sha256": "old-hash", "lastmod": "2026-07-12"}
        }
        current = {
            "https://tak-12.com/": {"sha256": "new-hash", "lastmod": "2026-07-13"}
        }
        validate_historical_coupling(current, previous)
        validate_historical_coupling(current, None)

    def test_baseline_uses_the_resolved_branch_point_only(self):
        expected = {
            "https://tak-12.com/": {"sha256": "old-hash", "lastmod": "2026-07-12"}
        }
        requested = []

        def read_revision(revision):
            requested.append(revision)
            return json.dumps(expected)

        self.assertEqual(
            expected,
            load_baseline_contract(
                resolve_revision=lambda: "branch-point-sha",
                read_revision=read_revision,
            ),
        )
        self.assertEqual(["branch-point-sha"], requested)

    def test_contract_reader_fails_closed_when_git_cannot_read_revision(self):
        def failing_git(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=128, stdout="", stderr="bad revision"
            )

        with self.assertRaisesRegex(RuntimeError, "Cannot inspect sitemap contract"):
            read_contract_at_revision("missing-sha", run_git=failing_git)

    def test_content_fingerprints_require_a_reviewed_lastmod_contract(self):
        entries = self.sitemap_entries()
        self.assertTrue(CONTENT_CONTRACT.is_file(), "Missing sitemap content contract")
        contract = json.loads(CONTENT_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(set(entries), set(contract))
        validate_historical_coupling(contract, load_baseline_contract())

        for location, metadata in contract.items():
            with self.subTest(location=location):
                page = canonical_page_path(location)
                self.assertTrue(page.is_file())
                digest = hashlib.sha256(page.read_bytes()).hexdigest()
                self.assertEqual(
                    metadata["sha256"],
                    digest,
                    "Page content changed: review the change, then update both its fingerprint and lastmod",
                )
                self.assertEqual(metadata["lastmod"], entries[location])


if __name__ == "__main__":
    unittest.main()

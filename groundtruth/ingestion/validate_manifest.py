#!/usr/bin/env python3

"""
Groundtruth Kubernetes Manifest Validator
------------------------------------------

Validates kubernetes_v0.1.yaml before ingestion.

Usage:
    python validate_manifest.py manifest/kubernetes_v0.1.yaml

Exit codes:
    0 = validation successful
    1 = validation failed
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import yaml


# ============================================================
# Expected corpus configuration
# ============================================================

EXPECTED_DOCUMENT_COUNT = 61

ALLOWED_DOMAINS = {
    "cluster_architecture",
    "workloads",
    "services_networking",
    "storage",
    "configuration",
    "security_policies",
    "scheduling_resource_management",
}

ALLOWED_HOSTS = {
    "kubernetes.io",
    "www.kubernetes.io",
}

EXPECTED_DOMAIN_DISTRIBUTION = {
    "cluster_architecture": 7,
    "workloads": 15,
    "services_networking": 10,
    "storage": 8,
    "configuration": 5,
    "security_policies": 9,
    "scheduling_resource_management": 7,
}

REQUIRED_FIELDS = {
    "id",
    "domain",
    "title",
    "url",
    "rationale",
}

ID_PATTERN = re.compile(
    r"^[a-z0-9]+-[0-9]{3}$"
)

ID_DOMAIN_PREFIXES = {
    "arch": "cluster_architecture",
    "work": "workloads",
    "net": "services_networking",
    "stor": "storage",
    "conf": "configuration",
    "sec": "security_policies",
    "sched": "scheduling_resource_management",
}

MIN_RATIONALE_LENGTH = 20
MAX_RATIONALE_LENGTH = 500
MAX_TITLE_LENGTH = 300


# ============================================================
# Validation exception
# ============================================================

class ManifestValidationError(Exception):
    """Raised when the manifest contains fatal validation errors."""


# ============================================================
# Error collector
# ============================================================

class ValidationErrors:
    """
    Collects all fatal errors so that the validator can report
    the complete set of problems in one run.
    """

    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def raise_if_any(self) -> None:
        if not self.errors:
            return

        lines = [
            "",
            "=" * 70,
            "MANIFEST VALIDATION FAILED",
            "=" * 70,
            f"Fatal errors: {len(self.errors)}",
            "",
        ]

        for index, error in enumerate(self.errors, start=1):
            lines.append(f"{index}. {error}")

        lines.extend(
            [
                "",
                "=" * 70,
            ]
        )

        raise ManifestValidationError("\n".join(lines))


# ============================================================
# YAML loading
# ============================================================

def load_manifest(path: Path) -> dict:
    """Load and parse the YAML manifest."""

    if not path.exists():
        raise ManifestValidationError(
            f"Manifest file does not exist: {path}"
        )

    if not path.is_file():
        raise ManifestValidationError(
            f"Manifest path is not a file: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

    except yaml.YAMLError as exc:
        raise ManifestValidationError(
            f"Invalid YAML syntax: {exc}"
        ) from exc

    if data is None:
        raise ManifestValidationError(
            "Manifest is empty."
        )

    if not isinstance(data, dict):
        raise ManifestValidationError(
            "Manifest root must be a YAML mapping/object."
        )

    return data


# ============================================================
# Top-level structure validation
# ============================================================

def validate_top_level(
    manifest: dict,
    errors: ValidationErrors,
) -> None:
    """Validate the top-level manifest structure."""

    required_sections = {
        "schema_version",
        "corpus",
        "documents",
        "validation",
    }

    missing = required_sections - set(manifest.keys())

    for field in sorted(missing):
        errors.add(
            f"Missing required top-level field: '{field}'."
        )

    documents = manifest.get("documents")

    if documents is None:
        return

    if not isinstance(documents, list):
        errors.add(
            "The 'documents' field must be a YAML list."
        )


# ============================================================
# Corpus metadata validation
# ============================================================

def validate_corpus_metadata(
    manifest: dict,
    errors: ValidationErrors,
) -> None:
    """Validate corpus-level metadata."""

    corpus = manifest.get("corpus")

    if corpus is None:
        return

    if not isinstance(corpus, dict):
        errors.add(
            "The 'corpus' field must be a YAML mapping/object."
        )
        return

    required_fields = {
        "id",
        "version",
        "name",
        "publisher",
        "language",
        "expected_document_count",
        "allowed_domains",
        "allowed_hosts",
    }

    missing = required_fields - set(corpus.keys())

    for field in sorted(missing):
        errors.add(
            f"Missing corpus field: 'corpus.{field}'."
        )

    expected_count = corpus.get("expected_document_count")

    if expected_count != EXPECTED_DOCUMENT_COUNT:
        errors.add(
            "Corpus expected_document_count is "
            f"{expected_count!r}; expected "
            f"{EXPECTED_DOCUMENT_COUNT}."
        )

    manifest_domains = corpus.get("allowed_domains")

    if isinstance(manifest_domains, list):
        if set(manifest_domains) != ALLOWED_DOMAINS:
            errors.add(
                "Corpus allowed_domains does not match the "
                "expected domain set."
            )

    manifest_hosts = corpus.get("allowed_hosts")

    if isinstance(manifest_hosts, list):
        if set(manifest_hosts) != ALLOWED_HOSTS:
            errors.add(
                "Corpus allowed_hosts does not match the "
                "expected Kubernetes host set."
            )


# ============================================================
# Document count validation
# ============================================================

def validate_document_count(
    documents: list,
    errors: ValidationErrors,
) -> None:
    """Ensure exactly 61 documents exist."""

    actual = len(documents)

    if actual != EXPECTED_DOCUMENT_COUNT:
        errors.add(
            "Incorrect document count: "
            f"found {actual}, expected "
            f"{EXPECTED_DOCUMENT_COUNT}."
        )


# ============================================================
# Individual document validation
# ============================================================

def validate_document_fields(
    document: object,
    index: int,
    errors: ValidationErrors,
) -> None:
    """Validate fields belonging to one document."""

    location = f"documents[{index}]"

    if not isinstance(document, dict):
        errors.add(
            f"{location} must be a YAML mapping/object."
        )
        return

    missing = REQUIRED_FIELDS - set(document.keys())

    for field in sorted(missing):
        errors.add(
            f"{location} is missing required field '{field}'."
        )

    # Stop field-level validation if required fields are absent.
    if missing:
        return

    document_id = document["id"]
    domain = document["domain"]
    title = document["title"]
    url = document["url"]
    rationale = document["rationale"]

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    if not isinstance(document_id, str):
        errors.add(
            f"{location}.id must be a string."
        )
    elif not ID_PATTERN.fullmatch(document_id):
        errors.add(
            f"{location}.id '{document_id}' has an invalid "
            "format. Expected e.g. 'net-002'."
        )

    # --------------------------------------------------------
    # Domain
    # --------------------------------------------------------

    if not isinstance(domain, str):
        errors.add(
            f"{location}.domain must be a string."
        )
    elif domain not in ALLOWED_DOMAINS:
        errors.add(
            f"{location}.domain '{domain}' is not an "
            "approved corpus domain."
        )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if not isinstance(title, str):
        errors.add(
            f"{location}.title must be a string."
        )
    else:
        if not title.strip():
            errors.add(
                f"{location}.title cannot be empty."
            )

        if len(title) > MAX_TITLE_LENGTH:
            errors.add(
                f"{location}.title exceeds "
                f"{MAX_TITLE_LENGTH} characters."
            )

    # --------------------------------------------------------
    # Rationale
    # --------------------------------------------------------

    if not isinstance(rationale, str):
        errors.add(
            f"{location}.rationale must be a string."
        )
    else:
        rationale_length = len(rationale.strip())

        if rationale_length < MIN_RATIONALE_LENGTH:
            errors.add(
                f"{location}.rationale is too short "
                f"({rationale_length} characters; minimum "
                f"{MIN_RATIONALE_LENGTH})."
            )

        if rationale_length > MAX_RATIONALE_LENGTH:
            errors.add(
                f"{location}.rationale exceeds "
                f"{MAX_RATIONALE_LENGTH} characters."
            )

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    validate_url(
        url=url,
        location=location,
        errors=errors,
    )

    # --------------------------------------------------------
    # ID prefix ↔ domain consistency
    # --------------------------------------------------------

    if isinstance(document_id, str) and isinstance(domain, str):
        validate_id_domain_mapping(
            document_id=document_id,
            domain=domain,
            location=location,
            errors=errors,
        )


# ============================================================
# URL validation
# ============================================================

def validate_url(
    url: object,
    location: str,
    errors: ValidationErrors,
) -> None:
    """Validate a manifest URL."""

    if not isinstance(url, str):
        errors.add(
            f"{location}.url must be a string."
        )
        return

    if not url.strip():
        errors.add(
            f"{location}.url cannot be empty."
        )
        return

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        errors.add(
            f"{location}.url '{url}' could not be parsed: {exc}"
        )
        return

    # Scheme
    if parsed.scheme != "https":
        errors.add(
            f"{location}.url must use HTTPS: '{url}'."
        )

    # Host
    hostname = parsed.hostname

    if hostname is None:
        errors.add(
            f"{location}.url has no hostname: '{url}'."
        )
    elif hostname.lower() not in ALLOWED_HOSTS:
        errors.add(
            f"{location}.url uses unapproved host "
            f"'{hostname}'. Allowed hosts: "
            f"{sorted(ALLOWED_HOSTS)}."
        )

    # Query parameters
    if parsed.query:
        errors.add(
            f"{location}.url must not contain query "
            f"parameters: '{url}'."
        )

    # Fragment
    if parsed.fragment:
        errors.add(
            f"{location}.url must not contain a fragment: "
            f"'{url}'."
        )

    # Username/password in URL
    if parsed.username is not None or parsed.password is not None:
        errors.add(
            f"{location}.url must not contain credentials: "
            f"'{url}'."
        )

    # Require a meaningful path
    if not parsed.path or parsed.path == "/":
        errors.add(
            f"{location}.url must contain a documentation "
            f"path: '{url}'."
        )


# ============================================================
# ID/domain validation
# ============================================================

def validate_id_domain_mapping(
    document_id: str,
    domain: str,
    location: str,
    errors: ValidationErrors,
) -> None:
    """
    Verify that the document ID prefix corresponds to its domain.

    Examples:
        net-002  -> services_networking
        work-004 -> workloads
    """

    prefix = document_id.split("-", 1)[0]

    expected_domain = ID_DOMAIN_PREFIXES.get(prefix)

    if expected_domain is None:
        errors.add(
            f"{location}.id '{document_id}' uses an "
            f"unrecognised ID prefix '{prefix}'."
        )
        return

    if domain != expected_domain:
        errors.add(
            f"{location} has ID/domain mismatch: "
            f"'{document_id}' implies domain "
            f"'{expected_domain}', but document declares "
            f"'{domain}'."
        )


# ============================================================
# Duplicate validation
# ============================================================

def validate_duplicates(
    documents: list,
    errors: ValidationErrors,
) -> None:
    """Check IDs, URLs and titles for duplicates."""

    ids: list[str] = []
    urls: list[str] = []
    titles: list[str] = []

    for document in documents:
        if not isinstance(document, dict):
            continue

        document_id = document.get("id")
        url = document.get("url")
        title = document.get("title")

        if isinstance(document_id, str):
            ids.append(document_id)

        if isinstance(url, str):
            urls.append(url)

        if isinstance(title, str):
            titles.append(title)

    # --------------------------------------------------------
    # Duplicate IDs
    # --------------------------------------------------------

    duplicate_ids = find_duplicates(ids)

    for value in duplicate_ids:
        errors.add(
            f"Duplicate document ID: '{value}'."
        )

    # --------------------------------------------------------
    # Duplicate URLs
    # --------------------------------------------------------

    duplicate_urls = find_duplicates(urls)

    for value in duplicate_urls:
        errors.add(
            f"Duplicate document URL: '{value}'."
        )

    # --------------------------------------------------------
    # Duplicate titles
    # --------------------------------------------------------

    duplicate_titles = find_duplicates(titles)

    for value in duplicate_titles:
        errors.add(
            f"Duplicate document title: '{value}'."
        )


def find_duplicates(values: list[str]) -> list[str]:
    """Return values occurring more than once."""

    counts = Counter(values)

    return sorted(
        value
        for value, count in counts.items()
        if count > 1
    )


# ============================================================
# Domain distribution validation
# ============================================================

def validate_domain_distribution(
    documents: list,
    errors: ValidationErrors,
) -> None:
    """Ensure the 61 documents have the expected distribution."""

    actual_counts = Counter()

    for document in documents:
        if not isinstance(document, dict):
            continue

        domain = document.get("domain")

        if isinstance(domain, str):
            actual_counts[domain] += 1

    for domain in sorted(ALLOWED_DOMAINS):

        actual = actual_counts.get(domain, 0)
        expected = EXPECTED_DOMAIN_DISTRIBUTION[domain]

        if actual != expected:
            errors.add(
                f"Incorrect document count for domain "
                f"'{domain}': found {actual}, "
                f"expected {expected}."
            )

    # Detect unexpected domains too.
    unexpected = set(actual_counts) - ALLOWED_DOMAINS

    for domain in sorted(unexpected):
        errors.add(
            f"Unexpected domain '{domain}' appears in "
            "the manifest."
        )


# ============================================================
# Manifest-level validation
# ============================================================

def validate_manifest(
    manifest: dict,
) -> None:
    """Run all manifest validation checks."""

    errors = ValidationErrors()

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    validate_top_level(
        manifest=manifest,
        errors=errors,
    )

    # --------------------------------------------------------
    # Corpus metadata
    # --------------------------------------------------------

    validate_corpus_metadata(
        manifest=manifest,
        errors=errors,
    )

    documents = manifest.get("documents")

    if not isinstance(documents, list):
        errors.raise_if_any()
        return

    # --------------------------------------------------------
    # Document count
    # --------------------------------------------------------

    validate_document_count(
        documents=documents,
        errors=errors,
    )

    # --------------------------------------------------------
    # Individual documents
    # --------------------------------------------------------

    for index, document in enumerate(documents):
        validate_document_fields(
            document=document,
            index=index,
            errors=errors,
        )

    # --------------------------------------------------------
    # Duplicate checks
    # --------------------------------------------------------

    validate_duplicates(
        documents=documents,
        errors=errors,
    )

    # --------------------------------------------------------
    # Domain distribution
    # --------------------------------------------------------

    validate_domain_distribution(
        documents=documents,
        errors=errors,
    )

    # --------------------------------------------------------
    # Raise all fatal errors together
    # --------------------------------------------------------

    errors.raise_if_any()


# ============================================================
# Success summary
# ============================================================

def print_success_summary(
    manifest: dict,
) -> None:
    """Print a concise validation summary."""

    documents = manifest["documents"]

    domain_counts = Counter(
        document["domain"]
        for document in documents
    )

    print("")
    print("=" * 70)
    print("MANIFEST VALIDATION PASSED")
    print("=" * 70)
    print(f"Corpus:       {manifest['corpus']['id']}")
    print(f"Version:      {manifest['corpus']['version']}")
    print(f"Documents:    {len(documents)}")
    print("")

    print("Domain distribution:")

    for domain in sorted(domain_counts):
        print(
            f"  {domain:<40} "
            f"{domain_counts[domain]:>2}"
        )

    print("")
    print("IDs:          unique")
    print("URLs:         unique")
    print("Titles:       unique")
    print("Hosts:        approved")
    print("HTTPS:        valid")
    print("Distribution: valid")
    print("=" * 70)
    print("")


# ============================================================
# CLI
# ============================================================

def main() -> int:
    """CLI entry point."""

    if len(sys.argv) != 2:
        print(
            "Usage: python validate_manifest.py "
            "<manifest.yaml>",
            file=sys.stderr,
        )
        return 1

    manifest_path = Path(sys.argv[1])

    try:
        manifest = load_manifest(manifest_path)

        validate_manifest(manifest)

        print_success_summary(manifest)

        return 0

    except ManifestValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    except Exception as exc:
        print(
            "",
            "UNEXPECTED VALIDATOR ERROR",
            "=" * 70,
            f"{type(exc).__name__}: {exc}",
            "",
            sep="\n",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

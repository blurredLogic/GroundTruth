from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml
from requests import Response, Session
from requests.exceptions import (
    ConnectionError,
    RequestException,
    Timeout,
)

from .validate_manifest import ManifestValidationError, validate_manifest


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_RAW_DIR = Path("data/raw/documents")
DEFAULT_METADATA_PATH = Path("data/raw/fetch_metadata.jsonl")
DEFAULT_REPORT_PATH = Path("reports/fetch_report.json")

DEFAULT_RATE_LIMIT_SECONDS = 1.0
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB

RETRYABLE_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}

EXPECTED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
}

USER_AGENT = (
    "GroundTruth-Kubernetes-Corpus/0.1 "
    "(retrieval-evaluation research project; respectful crawler)"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FetchError(RuntimeError):
    """Raised when a document cannot be fetched safely."""


class ContentValidationError(FetchError):
    """Raised when the returned content is not suitable for ingestion."""


class ExistingFileConflictError(FetchError):
    """
    Raised when an existing raw document differs from the newly fetched
    document and overwrite has not been explicitly allowed.
    """


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class FetchMetadata:
    document_id: str
    domain: str
    title: str

    requested_url: str
    final_url: str | None

    status: str
    http_status: int | None
    content_type: str | None

    byte_count: int | None
    sha256: str | None

    raw_path: str | None

    attempts: int
    redirect_count: int
    redirect_chain: list[dict[str, Any]]

    retrieved_at: str | None
    duration_seconds: float

    etag: str | None
    last_modified: str | None
    cache_control: str | None

    existing_file_status: str | None

    error: str | None


@dataclass
class FetchOutcome:
    content: bytes
    final_url: str
    http_status: int
    content_type: str
    attempts: int
    redirect_chain: list[dict[str, Any]]
    response_headers: dict[str, str]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def utc_now() -> str:
    """
    Return the current UTC time in ISO-8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    """
    Calculate a SHA-256 digest for raw bytes.
    """
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """
    Calculate a SHA-256 digest for a file without loading it all into memory.
    """
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """
    Write bytes atomically.

    The temporary file is written in the same directory and then renamed
    over the destination.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temp_path.open("wb") as file:
            file.write(content)
            file.flush()

        temp_path.replace(path)

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def atomic_write_text(path: Path, content: str) -> None:
    """
    Atomically write UTF-8 text.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def normalize_host(host: str | None) -> str:
    if not host:
        return ""

    return host.lower().rstrip(".")


def get_content_type(response: Response) -> str:
    """
    Return content type without charset.

    Example:
        text/html; charset=utf-8
    becomes:
        text/html
    """
    raw = response.headers.get("Content-Type", "")
    return raw.split(";", 1)[0].strip().lower()


def parse_retry_after(response: Response) -> float | None:
    """
    Parse Retry-After.

    Supports both:
        Retry-After: 5

    and HTTP date form.
    """
    value = response.headers.get("Retry-After")

    if not value:
        return None

    value = value.strip()

    try:
        seconds = float(value)
        return max(seconds, 0.0)
    except ValueError:
        pass

    try:
        retry_time = parsedate_to_datetime(value)

        if retry_time.tzinfo is None:
            retry_time = retry_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        return max((retry_time - now).total_seconds(), 0.0)

    except (TypeError, ValueError):
        return None


def build_redirect_chain(response: Response) -> list[dict[str, Any]]:
    """
    Preserve all redirects for provenance/auditing.
    """
    chain: list[dict[str, Any]] = []

    for item in response.history:
        chain.append(
            {
                "status_code": item.status_code,
                "url": item.url,
                "location": item.headers.get("Location"),
            }
        )

    return chain


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """
    Simple per-process rate limiter.

    Ensures at least `minimum_interval` seconds between HTTP request starts.
    """

    def __init__(self, minimum_interval: float) -> None:
        self.minimum_interval = max(0.0, minimum_interval)
        self.last_request_time: float | None = None

    def wait(self) -> None:
        if self.last_request_time is None:
            self.last_request_time = time.monotonic()
            return

        elapsed = time.monotonic() - self.last_request_time

        remaining = self.minimum_interval - elapsed

        if remaining > 0:
            time.sleep(remaining)

        self.last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# Manifest handling
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a YAML mapping.")

    return data


def get_allowed_hosts(manifest: dict[str, Any]) -> set[str]:
    corpus = manifest.get("corpus", {})

    configured_hosts = corpus.get(
        "allowed_hosts",
        ["kubernetes.io", "www.kubernetes.io"],
    )

    return {
        normalize_host(host)
        for host in configured_hosts
        if isinstance(host, str)
    }


# ---------------------------------------------------------------------------
# HTTP session
# ---------------------------------------------------------------------------


def create_session() -> Session:
    """
    Create a requests session.

    Retries are implemented manually below so that:
      - every retry is visible
      - every retry obeys rate limiting
      - Retry-After can be respected
      - retry counts can be stored in metadata
    """
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en",
            "Connection": "keep-alive",
        }
    )

    return session


# ---------------------------------------------------------------------------
# Response validation
# ---------------------------------------------------------------------------


def validate_final_url(
    final_url: str,
    allowed_hosts: set[str],
) -> None:
    parsed = urlparse(final_url)

    if parsed.scheme.lower() != "https":
        raise ContentValidationError(
            f"Redirected to non-HTTPS URL: {final_url}"
        )

    host = normalize_host(parsed.hostname)

    if host not in allowed_hosts:
        raise ContentValidationError(
            "Redirected to an unapproved host: "
            f"{host!r}. Allowed hosts: {sorted(allowed_hosts)}"
        )


def validate_content_type(response: Response) -> str:
    content_type = get_content_type(response)

    if content_type not in EXPECTED_CONTENT_TYPES:
        raise ContentValidationError(
            "Unexpected Content-Type "
            f"{response.headers.get('Content-Type')!r} "
            f"for {response.url}"
        )

    return content_type


def read_response_content(
    response: Response,
    max_bytes: int,
) -> bytes:
    """
    Read the response incrementally and enforce a maximum response size.
    """

    declared_size = response.headers.get("Content-Length")

    if declared_size:
        try:
            declared_size_int = int(declared_size)

            if declared_size_int > max_bytes:
                raise ContentValidationError(
                    f"Response declares {declared_size_int:,} bytes, "
                    f"exceeding limit of {max_bytes:,} bytes."
                )
        except ValueError:
            pass

    chunks: list[bytes] = []
    total = 0

    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue

        total += len(chunk)

        if total > max_bytes:
            raise ContentValidationError(
                f"Downloaded response exceeded maximum size of "
                f"{max_bytes:,} bytes."
            )

        chunks.append(chunk)

    content = b"".join(chunks)

    if not content:
        raise ContentValidationError(
            f"Empty response body returned by {response.url}"
        )

    return content


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def fetch_document(
    session: Session,
    rate_limiter: RateLimiter,
    url: str,
    allowed_hosts: set[str],
    connect_timeout: int,
    read_timeout: int,
    max_retries: int,
    backoff_base: float,
    max_response_bytes: int,
) -> FetchOutcome:
    """
    Fetch one document.

    max_retries=3 means:
        initial attempt + up to 3 retries
        = maximum 4 attempts
    """

    total_attempts = max_retries + 1
    last_error: Exception | None = None

    for attempt_index in range(total_attempts):
        attempt_number = attempt_index + 1

        rate_limiter.wait()

        response: Response | None = None

        try:
            response = session.get(
                url,
                timeout=(connect_timeout, read_timeout),
                allow_redirects=True,
                stream=True,
            )

            status = response.status_code

            # ---------------------------------------------------------------
            # Retryable HTTP status
            # ---------------------------------------------------------------

            if status in RETRYABLE_STATUS_CODES:

                if attempt_number >= total_attempts:
                    raise FetchError(
                        f"HTTP {status} after {attempt_number} attempts."
                    )

                retry_after = parse_retry_after(response)

                response.close()

                exponential_backoff = (
                    backoff_base * (2 ** attempt_index)
                )

                delay = max(
                    retry_after or 0.0,
                    exponential_backoff,
                )

                print(
                    f"    retry {attempt_number}/{max_retries}: "
                    f"HTTP {status}; waiting {delay:.1f}s"
                )

                time.sleep(delay)
                continue

            # ---------------------------------------------------------------
            # Any other HTTP error is fatal
            # ---------------------------------------------------------------

            if status < 200 or status >= 300:
                raise FetchError(
                    f"HTTP {status} returned by {response.url}"
                )

            # ---------------------------------------------------------------
            # Validate redirect destination
            # ---------------------------------------------------------------

            validate_final_url(
                response.url,
                allowed_hosts,
            )

            # ---------------------------------------------------------------
            # Validate content type
            # ---------------------------------------------------------------

            content_type = validate_content_type(response)

            # ---------------------------------------------------------------
            # Read body safely
            # ---------------------------------------------------------------

            content = read_response_content(
                response,
                max_response_bytes,
            )

            redirect_chain = build_redirect_chain(response)

            headers = {
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get(
                    "Last-Modified", ""
                ),
                "cache_control": response.headers.get(
                    "Cache-Control", ""
                ),
            }

            return FetchOutcome(
                content=content,
                final_url=response.url,
                http_status=response.status_code,
                content_type=content_type,
                attempts=attempt_number,
                redirect_chain=redirect_chain,
                response_headers=headers,
            )

        except (
            Timeout,
            ConnectionError,
        ) as exc:
            last_error = exc

            if attempt_number >= total_attempts:
                break

            delay = backoff_base * (2 ** attempt_index)

            print(
                f"    retry {attempt_number}/{max_retries}: "
                f"{type(exc).__name__}; "
                f"waiting {delay:.1f}s"
            )

            time.sleep(delay)

        except RequestException as exc:
            # Other requests errors are not automatically retryable.
            raise FetchError(
                f"Request failed: {exc}"
            ) from exc

        finally:
            if response is not None:
                response.close()

    raise FetchError(
        f"Network request failed after {total_attempts} attempts: "
        f"{last_error}"
    )


# ---------------------------------------------------------------------------
# Raw storage
# ---------------------------------------------------------------------------


def store_raw_document(
    document_id: str,
    content: bytes,
    raw_dir: Path,
    overwrite_changed: bool,
) -> tuple[Path, str, str]:
    """
    Save the raw HTML document.

    Returns:
        path
        SHA-256
        existing file status

    existing file status is one of:
        new
        unchanged
        overwritten
    """

    raw_dir.mkdir(parents=True, exist_ok=True)

    destination = raw_dir / f"{document_id}.html"

    new_hash = sha256_bytes(content)

    if destination.exists():
        existing_hash = sha256_file(destination)

        if existing_hash == new_hash:
            return destination, new_hash, "unchanged"

        if not overwrite_changed:
            raise ExistingFileConflictError(
                f"{destination} already exists but its SHA-256 differs.\n"
                f"Existing: {existing_hash}\n"
                f"Fetched:  {new_hash}\n\n"
                "The source content appears to have changed. "
                "Refusing to silently replace the corpus snapshot.\n"
                "Use --overwrite-changed only if you intentionally want "
                "to update the raw corpus."
            )

        atomic_write_bytes(destination, content)

        return destination, new_hash, "overwritten"

    atomic_write_bytes(destination, content)

    return destination, new_hash, "new"


# ---------------------------------------------------------------------------
# Metadata and reports
# ---------------------------------------------------------------------------


def write_metadata_jsonl(
    metadata_records: list[FetchMetadata],
    path: Path,
) -> None:
    lines = []

    for record in metadata_records:
        lines.append(
            json.dumps(
                asdict(record),
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    content = "\n".join(lines)

    if content:
        content += "\n"

    atomic_write_text(path, content)


def write_fetch_report(
    *,
    report_path: Path,
    manifest_path: Path,
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    selected_document_count: int,
    metadata_records: list[FetchMetadata],
) -> None:

    successful = [
        record
        for record in metadata_records
        if record.status == "success"
    ]

    failed = [
        record
        for record in metadata_records
        if record.status == "failed"
    ]

    new_files = sum(
        record.existing_file_status == "new"
        for record in successful
    )

    unchanged_files = sum(
        record.existing_file_status == "unchanged"
        for record in successful
    )

    overwritten_files = sum(
        record.existing_file_status == "overwritten"
        for record in successful
    )

    report = {
        "schema_version": "0.1",
        "stage": "fetch",
        "manifest": str(manifest_path),
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": round(duration_seconds, 3),
        "status": "SUCCESS" if not failed else "FAILED",
        "documents_requested": selected_document_count,
        "successful": len(successful),
        "failed": len(failed),
        "raw_files": {
            "new": new_files,
            "unchanged": unchanged_files,
            "overwritten": overwritten_files,
        },
        "failed_documents": [
            {
                "document_id": record.document_id,
                "url": record.requested_url,
                "error": record.error,
            }
            for record in failed
        ],
    }

    atomic_write_text(
        report_path,
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


# ---------------------------------------------------------------------------
# Console display
# ---------------------------------------------------------------------------


def format_size(byte_count: int) -> str:
    if byte_count >= 1024 * 1024:
        return f"{byte_count / (1024 * 1024):.1f} MB"

    if byte_count >= 1024:
        return f"{byte_count / 1024:.0f} KB"

    return f"{byte_count} B"


def print_summary(
    records: list[FetchMetadata],
    metadata_path: Path,
    report_path: Path,
) -> None:
    successful = [
        record
        for record in records
        if record.status == "success"
    ]

    failed = [
        record
        for record in records
        if record.status == "failed"
    ]

    new_files = sum(
        record.existing_file_status == "new"
        for record in successful
    )

    unchanged_files = sum(
        record.existing_file_status == "unchanged"
        for record in successful
    )

    overwritten_files = sum(
        record.existing_file_status == "overwritten"
        for record in successful
    )

    print()
    print("-" * 64)
    print(f"Documents requested: {len(records)}")
    print(f"Successful:          {len(successful)}")
    print(f"Failed:              {len(failed)}")
    print(f"New raw files:       {new_files}")
    print(f"Unchanged files:     {unchanged_files}")
    print(f"Overwritten files:   {overwritten_files}")
    print(f"Metadata:            {metadata_path}")
    print(f"Report:              {report_path}")

    if failed:
        print("Status:              FAILED")
    else:
        print("Status:              SUCCESS")

    print("-" * 64)


# ---------------------------------------------------------------------------
# Main ingestion routine
# ---------------------------------------------------------------------------


def run_fetch(
    *,
    manifest_path: Path,
    raw_dir: Path,
    metadata_path: Path,
    report_path: Path,
    rate_limit_seconds: float,
    connect_timeout: int,
    read_timeout: int,
    max_retries: int,
    backoff_base: float,
    max_response_bytes: int,
    overwrite_changed: bool,
    continue_on_error: bool,
    document_id: str | None,
    limit: int | None,
) -> int:

    # -----------------------------------------------------------------------
    # Step 1: Validate manifest before performing network operations
    # -----------------------------------------------------------------------

    print(f"Validating manifest: {manifest_path}")

    try:
        # Load YAML into a Python dictionary first.
        manifest = load_manifest(manifest_path)

        # validate_manifest() expects the loaded manifest dictionary,
        # not the Path object.
        validate_manifest(manifest)

    except ManifestValidationError as exc:
        print()
        print("Manifest validation failed.")
        print(exc)
        return 1

    except (OSError, ValueError, yaml.YAMLError) as exc:
        print()
        print("Failed to load manifest.")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print("Manifest validation: PASSED")
    print()

    documents = manifest["documents"]

    allowed_hosts = get_allowed_hosts(manifest)

    # -----------------------------------------------------------------------
    # Optional development filters
    # -----------------------------------------------------------------------

    if document_id is not None:
        documents = [
            document
            for document in documents
            if document["id"] == document_id
        ]

        if not documents:
            print(
                f"ERROR: document ID {document_id!r} "
                "was not found in the manifest."
            )
            return 1

    if limit is not None:
        documents = documents[:limit]

    if not documents:
        print("ERROR: no documents selected for fetching.")
        return 1

    # -----------------------------------------------------------------------
    # Prepare fetch infrastructure
    # -----------------------------------------------------------------------

    session = create_session()

    rate_limiter = RateLimiter(
        minimum_interval=rate_limit_seconds
    )

    metadata_records: list[FetchMetadata] = []

    started_at = utc_now()
    run_started = time.monotonic()

    total = len(documents)

    try:
        for index, document in enumerate(documents, start=1):

            doc_id = document["id"]
            domain = document["domain"]
            title = document["title"]
            url = document["url"]

            print(
                f"[{index:03d}/{total:03d}] "
                f"{doc_id:<12} "
                f"{url}"
            )

            document_started = time.monotonic()

            try:
                outcome = fetch_document(
                    session=session,
                    rate_limiter=rate_limiter,
                    url=url,
                    allowed_hosts=allowed_hosts,
                    connect_timeout=connect_timeout,
                    read_timeout=read_timeout,
                    max_retries=max_retries,
                    backoff_base=backoff_base,
                    max_response_bytes=max_response_bytes,
                )

                raw_path, digest, file_status = store_raw_document(
                    document_id=doc_id,
                    content=outcome.content,
                    raw_dir=raw_dir,
                    overwrite_changed=overwrite_changed,
                )

                elapsed = time.monotonic() - document_started

                record = FetchMetadata(
                    document_id=doc_id,
                    domain=domain,
                    title=title,

                    requested_url=url,
                    final_url=outcome.final_url,

                    status="success",
                    http_status=outcome.http_status,
                    content_type=outcome.content_type,

                    byte_count=len(outcome.content),
                    sha256=f"sha256:{digest}",

                    raw_path=str(raw_path),

                    attempts=outcome.attempts,
                    redirect_count=len(
                        outcome.redirect_chain
                    ),
                    redirect_chain=outcome.redirect_chain,

                    retrieved_at=utc_now(),
                    duration_seconds=round(elapsed, 3),

                    etag=(
                        outcome.response_headers.get("etag")
                        or None
                    ),
                    last_modified=(
                        outcome.response_headers.get(
                            "last_modified"
                        )
                        or None
                    ),
                    cache_control=(
                        outcome.response_headers.get(
                            "cache_control"
                        )
                        or None
                    ),

                    existing_file_status=file_status,

                    error=None,
                )

                metadata_records.append(record)

                print(
                    f"    {outcome.http_status}  "
                    f"{format_size(len(outcome.content)):<10} "
                    f"{file_status:<11} "
                    f"sha256:{digest[:12]}...  OK"
                )

            except Exception as exc:
                elapsed = time.monotonic() - document_started

                record = FetchMetadata(
                    document_id=doc_id,
                    domain=domain,
                    title=title,

                    requested_url=url,
                    final_url=None,

                    status="failed",
                    http_status=None,
                    content_type=None,

                    byte_count=None,
                    sha256=None,

                    raw_path=None,

                    attempts=0,
                    redirect_count=0,
                    redirect_chain=[],

                    retrieved_at=None,
                    duration_seconds=round(elapsed, 3),

                    etag=None,
                    last_modified=None,
                    cache_control=None,

                    existing_file_status=None,

                    error=f"{type(exc).__name__}: {exc}",
                )

                metadata_records.append(record)

                print(
                    f"    FAILED: "
                    f"{type(exc).__name__}: {exc}"
                )

                if not continue_on_error:
                    print()
                    print(
                        "Stopping because fail-fast mode is enabled."
                    )
                    break

    finally:
        session.close()

    # -----------------------------------------------------------------------
    # Persist metadata/report even if the fetch stage failed.
    #
    # This is useful for diagnosing exactly which request failed.
    # -----------------------------------------------------------------------

    write_metadata_jsonl(
        metadata_records,
        metadata_path,
    )

    completed_at = utc_now()
    run_duration = time.monotonic() - run_started

    write_fetch_report(
        report_path=report_path,
        manifest_path=manifest_path,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=run_duration,
        selected_document_count=len(documents),
        metadata_records=metadata_records,
    )

    print_summary(
        metadata_records,
        metadata_path,
        report_path,
    )

    failed = any(
        record.status == "failed"
        for record in metadata_records
    )

    incomplete = len(metadata_records) != len(documents)

    if failed or incomplete:
        return 1

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch and archive raw HTML documents declared in the "
            "GroundTruth corpus manifest."
        )
    )

    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to the YAML corpus manifest.",
    )

    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help=(
            "Directory for archived raw HTML. "
            f"Default: {DEFAULT_RAW_DIR}"
        ),
    )

    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help=(
            "JSONL fetch metadata output. "
            f"Default: {DEFAULT_METADATA_PATH}"
        ),
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=(
            "Fetch report JSON path. "
            f"Default: {DEFAULT_REPORT_PATH}"
        ),
    )

    parser.add_argument(
        "--rate-limit",
        type=float,
        default=DEFAULT_RATE_LIMIT_SECONDS,
        help=(
            "Minimum seconds between HTTP requests. "
            f"Default: {DEFAULT_RATE_LIMIT_SECONDS}"
        ),
    )

    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=DEFAULT_CONNECT_TIMEOUT,
        help=(
            "Connection timeout in seconds. "
            f"Default: {DEFAULT_CONNECT_TIMEOUT}"
        ),
    )

    parser.add_argument(
        "--read-timeout",
        type=int,
        default=DEFAULT_READ_TIMEOUT,
        help=(
            "Read timeout in seconds. "
            f"Default: {DEFAULT_READ_TIMEOUT}"
        ),
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=(
            "Number of retries after the initial attempt. "
            f"Default: {DEFAULT_MAX_RETRIES}"
        ),
    )

    parser.add_argument(
        "--backoff-base",
        type=float,
        default=DEFAULT_BACKOFF_BASE,
        help=(
            "Base seconds for exponential retry backoff. "
            f"Default: {DEFAULT_BACKOFF_BASE}"
        ),
    )

    parser.add_argument(
        "--max-response-mb",
        type=float,
        default=10.0,
        help="Maximum allowed size for one document. Default: 10 MB.",
    )

    parser.add_argument(
        "--overwrite-changed",
        action="store_true",
        help=(
            "Allow an existing raw HTML file to be replaced when "
            "the newly fetched content has a different SHA-256."
        ),
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help=(
            "Continue fetching later documents after a document fails. "
            "Default behaviour is fail-fast."
        ),
    )

    parser.add_argument(
        "--document-id",
        type=str,
        default=None,
        help=(
            "Fetch only one manifest document. Useful during development. "
            "Example: --document-id net-002"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Fetch only the first N selected documents. "
            "Useful for development/testing."
        ),
    )

    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.rate_limit < 0:
        parser.error("--rate-limit must be >= 0")

    if args.max_retries < 0:
        parser.error("--max-retries must be >= 0")

    if args.backoff_base < 0:
        parser.error("--backoff-base must be >= 0")

    if args.max_response_mb <= 0:
        parser.error("--max-response-mb must be > 0")

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than 0")

    max_response_bytes = int(
        args.max_response_mb * 1024 * 1024
    )

    return run_fetch(
        manifest_path=args.manifest,
        raw_dir=args.raw_dir,
        metadata_path=args.metadata_output,
        report_path=args.report_output,
        rate_limit_seconds=args.rate_limit,
        connect_timeout=args.connect_timeout,
        read_timeout=args.read_timeout,
        max_retries=args.max_retries,
        backoff_base=args.backoff_base,
        max_response_bytes=max_response_bytes,
        overwrite_changed=args.overwrite_changed,
        continue_on_error=args.continue_on_error,
        document_id=args.document_id,
        limit=args.limit,
    )


if __name__ == "__main__":
    sys.exit(main())

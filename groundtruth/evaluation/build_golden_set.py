from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: numpy\n"
        "Install it with:\n"
        "  python -m pip install numpy"
    ) from exc


# =============================================================================
# Configuration
# =============================================================================

BUILDER_VERSION = "0.1.0"

DEFAULT_CHUNKS_PATH = Path("data/index/chunks_indexable.jsonl")
DEFAULT_SEED_PATH = Path("data/evaluation/golden_questions.jsonl")
DEFAULT_EMBEDDINGS_PATH = Path("data/index/dense/embeddings.npy")
DEFAULT_METADATA_PATH = Path("data/index/dense/metadata.jsonl")

DEFAULT_OUTPUT_PATH = Path(
    "data/evaluation/golden_labeling_candidates.jsonl"
)
DEFAULT_PLAN_PATH = Path(
    "data/evaluation/golden_plan.json"
)
DEFAULT_REPORT_PATH = Path(
    "reports/golden_set_build_report.json"
)

TOTAL_QUESTIONS = 100

CATEGORY_TARGETS = {
    "direct_factual": 20,
    "comparison": 15,
    "scenario_application": 20,
    "multi_hop": 20,
    "troubleshooting": 15,
    "negative_near_miss": 10,
}

DIFFICULTY_TARGETS = {
    "easy": 25,
    "medium": 45,
    "hard": 30,
}

SPLIT_TARGETS = {
    "dev": 60,
    "test": 40,
}

# Final 100-question category x difficulty matrix.
CATEGORY_DIFFICULTY_TARGETS = {
    "direct_factual": {
        "easy": 12,
        "medium": 8,
        "hard": 0,
    },
    "comparison": {
        "easy": 2,
        "medium": 8,
        "hard": 5,
    },
    "scenario_application": {
        "easy": 4,
        "medium": 10,
        "hard": 6,
    },
    "multi_hop": {
        "easy": 2,
        "medium": 8,
        "hard": 10,
    },
    "troubleshooting": {
        "easy": 2,
        "medium": 7,
        "hard": 6,
    },
    "negative_near_miss": {
        "easy": 3,
        "medium": 4,
        "hard": 3,
    },
}

# Final 100-question category x split matrix.
CATEGORY_SPLIT_TARGETS = {
    "direct_factual": {
        "dev": 12,
        "test": 8,
    },
    "comparison": {
        "dev": 9,
        "test": 6,
    },
    "scenario_application": {
        "dev": 12,
        "test": 8,
    },
    "multi_hop": {
        "dev": 12,
        "test": 8,
    },
    "troubleshooting": {
        "dev": 9,
        "test": 6,
    },
    "negative_near_miss": {
        "dev": 6,
        "test": 4,
    },
}

VALID_CATEGORIES = set(CATEGORY_TARGETS)
VALID_DIFFICULTIES = set(DIFFICULTY_TARGETS)
VALID_SPLITS = set(SPLIT_TARGETS)

QUESTION_ID_RE = re.compile(
    r"^k8s-(?P<number>[0-9]{3})$"
)

WORD_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_-]*"
)

AUTHORING_GUIDANCE = {
    "direct_factual": (
        "Write a single-hop factual question whose answer is explicitly "
        "stated in the anchor context. Prefer definitions, purposes, "
        "constraints, or concrete behavior. The primary answer-bearing "
        "chunk should normally receive grade 3."
    ),
    "comparison": (
        "Write a question that requires distinguishing or comparing two "
        "Kubernetes concepts represented by the anchor and a related "
        "candidate. The question should require both concepts, not merely "
        "mention them."
    ),
    "scenario_application": (
        "Write a realistic operator/developer scenario where the user must "
        "apply the documented behavior in the anchor context. Avoid copying "
        "the heading verbatim into the question."
    ),
    "multi_hop": (
        "Write a question that needs evidence from at least two chunks or "
        "sections. Use the anchor plus one or more related candidates and "
        "label every genuinely answer-bearing chunk."
    ),
    "troubleshooting": (
        "Write a symptom/cause/remedy question grounded in the anchor and "
        "related context. The question should sound like a real Kubernetes "
        "debugging task rather than a definition."
    ),
    "negative_near_miss": (
        "Write an intentionally unanswerable or near-miss question that is "
        "topically close to the supplied context but not actually supported "
        "by this corpus. Keep answerable=false and do not invent positive "
        "relevance judgments."
    ),
}


# =============================================================================
# Exceptions / basic IO
# =============================================================================


class GoldenSetBuildError(RuntimeError):
    """Raised when the labeling-plan build cannot be completed safely."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def atomic_write_text(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    try:
        temporary.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def load_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        raise GoldenSetBuildError(
            f"File does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, raw_line in enumerate(
            file,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GoldenSetBuildError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise GoldenSetBuildError(
                    f"{path}:{line_number}: each JSONL record must be "
                    "an object."
                )

            records.append(value)

    if not records:
        raise GoldenSetBuildError(
            f"No records found in {path}"
        )

    return records


def canonical_json_line(
    value: dict[str, Any],
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


# =============================================================================
# Seed validation / target accounting
# =============================================================================


def validate_targets() -> None:
    if sum(CATEGORY_TARGETS.values()) != TOTAL_QUESTIONS:
        raise GoldenSetBuildError(
            "CATEGORY_TARGETS do not sum to 100."
        )

    if sum(DIFFICULTY_TARGETS.values()) != TOTAL_QUESTIONS:
        raise GoldenSetBuildError(
            "DIFFICULTY_TARGETS do not sum to 100."
        )

    if sum(SPLIT_TARGETS.values()) != TOTAL_QUESTIONS:
        raise GoldenSetBuildError(
            "SPLIT_TARGETS do not sum to 100."
        )

    for category, difficulty_counts in (
        CATEGORY_DIFFICULTY_TARGETS.items()
    ):
        if (
            sum(difficulty_counts.values())
            != CATEGORY_TARGETS[category]
        ):
            raise GoldenSetBuildError(
                f"Difficulty matrix row for {category} "
                "does not equal category target."
            )

    difficulty_columns = Counter()

    for difficulty_counts in (
        CATEGORY_DIFFICULTY_TARGETS.values()
    ):
        difficulty_columns.update(
            difficulty_counts
        )

    if dict(difficulty_columns) != DIFFICULTY_TARGETS:
        raise GoldenSetBuildError(
            "CATEGORY_DIFFICULTY_TARGETS columns do not match "
            "DIFFICULTY_TARGETS."
        )

    for category, split_counts in (
        CATEGORY_SPLIT_TARGETS.items()
    ):
        if (
            sum(split_counts.values())
            != CATEGORY_TARGETS[category]
        ):
            raise GoldenSetBuildError(
                f"Split matrix row for {category} does not "
                "equal category target."
            )

    split_columns = Counter()

    for split_counts in (
        CATEGORY_SPLIT_TARGETS.values()
    ):
        split_columns.update(
            split_counts
        )

    if dict(split_columns) != SPLIT_TARGETS:
        raise GoldenSetBuildError(
            "CATEGORY_SPLIT_TARGETS columns do not match SPLIT_TARGETS."
        )


def validate_seed_question(
    question: dict[str, Any],
) -> None:
    required = {
        "question_id",
        "question",
        "category",
        "difficulty",
        "split",
        "answerable",
        "relevance_judgments",
    }

    missing = required - set(question)

    if missing:
        raise GoldenSetBuildError(
            "Seed question missing fields: "
            + ", ".join(sorted(missing))
        )

    question_id = str(
        question["question_id"]
    )

    if QUESTION_ID_RE.fullmatch(question_id) is None:
        raise GoldenSetBuildError(
            f"Invalid seed question_id: {question_id!r}"
        )

    if question["category"] not in VALID_CATEGORIES:
        raise GoldenSetBuildError(
            f"{question_id}: invalid category."
        )

    if question["difficulty"] not in VALID_DIFFICULTIES:
        raise GoldenSetBuildError(
            f"{question_id}: invalid difficulty."
        )

    if question["split"] not in VALID_SPLITS:
        raise GoldenSetBuildError(
            f"{question_id}: invalid split."
        )

    if not isinstance(
        question["answerable"],
        bool,
    ):
        raise GoldenSetBuildError(
            f"{question_id}: answerable must be boolean."
        )

    judgments = question[
        "relevance_judgments"
    ]

    if not isinstance(judgments, list):
        raise GoldenSetBuildError(
            f"{question_id}: relevance_judgments must be a list."
        )


def validate_seed_set(
    seeds: list[dict[str, Any]],
) -> None:
    seen_ids: set[str] = set()

    for seed in seeds:
        validate_seed_question(seed)

        question_id = str(
            seed["question_id"]
        )

        if question_id in seen_ids:
            raise GoldenSetBuildError(
                f"Duplicate seed question_id: {question_id}"
            )

        seen_ids.add(question_id)

    if len(seeds) > TOTAL_QUESTIONS:
        raise GoldenSetBuildError(
            "Seed set is already larger than 100 questions."
        )


def seed_counts(
    seeds: list[dict[str, Any]],
) -> dict[str, Any]:
    category = Counter()
    difficulty = Counter()
    split = Counter()
    category_difficulty: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)
    category_split: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)

    for seed in seeds:
        c = str(seed["category"])
        d = str(seed["difficulty"])
        s = str(seed["split"])

        category[c] += 1
        difficulty[d] += 1
        split[s] += 1
        category_difficulty[c][d] += 1
        category_split[c][s] += 1

    return {
        "category": category,
        "difficulty": difficulty,
        "split": split,
        "category_difficulty": (
            category_difficulty
        ),
        "category_split": category_split,
    }


def ensure_seed_does_not_exceed_targets(
    counts: dict[str, Any],
) -> None:
    for category, count in counts[
        "category"
    ].items():
        if count > CATEGORY_TARGETS[category]:
            raise GoldenSetBuildError(
                f"Seeds exceed category target for {category}."
            )

    for difficulty, count in counts[
        "difficulty"
    ].items():
        if count > DIFFICULTY_TARGETS[difficulty]:
            raise GoldenSetBuildError(
                f"Seeds exceed difficulty target for {difficulty}."
            )

    for split, count in counts[
        "split"
    ].items():
        if count > SPLIT_TARGETS[split]:
            raise GoldenSetBuildError(
                f"Seeds exceed split target for {split}."
            )

    for category in VALID_CATEGORIES:
        for difficulty in VALID_DIFFICULTIES:
            actual = counts[
                "category_difficulty"
            ][category][difficulty]

            allowed = CATEGORY_DIFFICULTY_TARGETS[
                category
            ][difficulty]

            if actual > allowed:
                raise GoldenSetBuildError(
                    f"Seeds exceed target for "
                    f"{category}/{difficulty}."
                )

        for split in VALID_SPLITS:
            actual = counts[
                "category_split"
            ][category][split]

            allowed = CATEGORY_SPLIT_TARGETS[
                category
            ][split]

            if actual > allowed:
                raise GoldenSetBuildError(
                    f"Seeds exceed target for {category}/{split}."
                )


# =============================================================================
# Slot construction
# =============================================================================


def remaining_category_difficulty_slots(
    counts: dict[str, Any],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}

    difficulty_order = [
        "easy",
        "medium",
        "hard",
    ]

    for category in CATEGORY_TARGETS:
        values: list[str] = []

        for difficulty in difficulty_order:
            target = CATEGORY_DIFFICULTY_TARGETS[
                category
            ][difficulty]

            used = counts[
                "category_difficulty"
            ][category][difficulty]

            remainder = target - used

            values.extend(
                [difficulty] * remainder
            )

        result[category] = values

    return result


def remaining_category_split_slots(
    counts: dict[str, Any],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}

    split_order = [
        "dev",
        "test",
    ]

    for category in CATEGORY_TARGETS:
        values: list[str] = []

        for split in split_order:
            target = CATEGORY_SPLIT_TARGETS[
                category
            ][split]

            used = counts[
                "category_split"
            ][category][split]

            remainder = target - used

            values.extend(
                [split] * remainder
            )

        result[category] = values

    return result


def next_question_numbers(
    seeds: list[dict[str, Any]],
    count: int,
) -> list[int]:
    used_numbers = {
        int(
            QUESTION_ID_RE.fullmatch(
                str(seed["question_id"])
            ).group("number")
        )
        for seed in seeds
    }

    numbers: list[int] = []

    for number in range(
        1,
        TOTAL_QUESTIONS + 1,
    ):
        if number in used_numbers:
            continue

        numbers.append(number)

        if len(numbers) == count:
            break

    if len(numbers) != count:
        raise GoldenSetBuildError(
            "Could not allocate enough question IDs."
        )

    return numbers


def interleave_category_specs(
    category_to_specs: dict[
        str,
        list[tuple[str, str]],
    ],
) -> list[
    tuple[str, str, str]
]:
    """
    Round-robin categories so adjacent labeling slots are not dominated
    by one question type.
    """
    categories = list(
        CATEGORY_TARGETS.keys()
    )

    positions = {
        category: 0
        for category in categories
    }

    total = sum(
        len(values)
        for values in category_to_specs.values()
    )

    output: list[
        tuple[str, str, str]
    ] = []

    while len(output) < total:
        progressed = False

        for category in categories:
            position = positions[
                category
            ]

            values = category_to_specs[
                category
            ]

            if position >= len(values):
                continue

            difficulty, split = values[
                position
            ]

            output.append(
                (
                    category,
                    difficulty,
                    split,
                )
            )

            positions[category] += 1
            progressed = True

        if not progressed:
            break

    return output


def make_remaining_slot_specs(
    seeds: list[dict[str, Any]],
) -> list[dict[str, str]]:
    counts = seed_counts(
        seeds
    )

    difficulty_slots = (
        remaining_category_difficulty_slots(
            counts
        )
    )

    split_slots = (
        remaining_category_split_slots(
            counts
        )
    )

    category_specs: dict[
        str,
        list[tuple[str, str]],
    ] = {}

    for category in CATEGORY_TARGETS:
        difficulties = difficulty_slots[
            category
        ]

        splits = split_slots[
            category
        ]

        if len(difficulties) != len(splits):
            raise GoldenSetBuildError(
                f"Residual target mismatch for {category}."
            )

        # Rotate split assignment relative to difficulty assignment to avoid
        # putting all easy questions in dev and all hard questions in test.
        if splits:
            rotate = len(splits) // 3
            splits = (
                splits[rotate:]
                + splits[:rotate]
            )

        category_specs[category] = list(
            zip(
                difficulties,
                splits,
            )
        )

    combined = interleave_category_specs(
        category_specs
    )

    remaining_count = (
        TOTAL_QUESTIONS
        - len(seeds)
    )

    if len(combined) != remaining_count:
        raise GoldenSetBuildError(
            "Residual slot count does not match required benchmark size."
        )

    numbers = next_question_numbers(
        seeds,
        remaining_count,
    )

    return [
        {
            "question_id": (
                f"k8s-{number:03d}"
            ),
            "category": category,
            "difficulty": difficulty,
            "split": split,
        }
        for number, (
            category,
            difficulty,
            split,
        ) in zip(numbers, combined)
    ]


# =============================================================================
# Chunk / dense-index loading
# =============================================================================


def validate_chunk(
    chunk: dict[str, Any],
) -> None:
    required = {
        "chunk_id",
        "document_id",
        "section_id",
        "domain",
        "section_title",
        "heading_path",
        "chunk_index",
        "text",
        "retrieval_text",
        "token_count",
        "source_url",
        "content_sha256",
    }

    missing = required - set(chunk)

    if missing:
        raise GoldenSetBuildError(
            "Indexable chunk missing fields: "
            + ", ".join(sorted(missing))
        )

    if not isinstance(
        chunk["heading_path"],
        list,
    ):
        raise GoldenSetBuildError(
            f"{chunk['chunk_id']}: heading_path must be a list."
        )


def load_and_validate_chunks(
    path: Path,
) -> list[dict[str, Any]]:
    chunks = load_jsonl(
        path
    )

    seen_ids: set[str] = set()

    for chunk in chunks:
        validate_chunk(chunk)

        chunk_id = str(
            chunk["chunk_id"]
        )

        if chunk_id in seen_ids:
            raise GoldenSetBuildError(
                f"Duplicate chunk ID in indexable corpus: {chunk_id}"
            )

        seen_ids.add(
            chunk_id
        )

    return chunks


def load_dense_artifacts(
    *,
    embeddings_path: Path,
    metadata_path: Path,
    chunks_by_id: dict[str, dict[str, Any]],
) -> tuple[
    np.ndarray,
    list[dict[str, Any]],
    dict[str, int],
]:
    if not embeddings_path.exists():
        raise GoldenSetBuildError(
            f"Dense embeddings not found: {embeddings_path}"
        )

    embeddings = np.load(
        embeddings_path,
        allow_pickle=False,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    metadata = load_jsonl(
        metadata_path
    )

    if embeddings.ndim != 2:
        raise GoldenSetBuildError(
            "Dense embedding artifact must be a 2D matrix."
        )

    if embeddings.shape[0] != len(metadata):
        raise GoldenSetBuildError(
            "Dense embeddings and metadata have different row counts."
        )

    chunk_to_row: dict[str, int] = {}

    for expected_row, record in enumerate(
        metadata
    ):
        if record.get("row_index") != expected_row:
            raise GoldenSetBuildError(
                "Dense metadata row_index is not contiguous."
            )

        chunk_id = str(
            record.get(
                "chunk_id",
                "",
            )
        )

        if chunk_id not in chunks_by_id:
            raise GoldenSetBuildError(
                f"Dense metadata references unknown chunk: {chunk_id}"
            )

        chunk_to_row[
            chunk_id
        ] = expected_row

    if set(chunk_to_row) != set(
        chunks_by_id
    ):
        raise GoldenSetBuildError(
            "Dense metadata chunk IDs do not exactly match "
            "chunks_indexable.jsonl."
        )

    return (
        embeddings,
        metadata,
        chunk_to_row,
    )


# =============================================================================
# Candidate-selection helpers
# =============================================================================


def chunk_quality_score(
    chunk: dict[str, Any],
) -> tuple[int, int, str]:
    """
    Deterministic preference:
      1. prefer chunks with at least 64 tokens
      2. prefer chunks closer to ~180 tokens
      3. stable chunk_id tie-break
    """
    token_count = int(
        chunk["token_count"]
    )

    too_short_penalty = (
        1
        if token_count < 64
        else 0
    )

    distance = abs(
        token_count - 180
    )

    return (
        too_short_penalty,
        distance,
        str(chunk["chunk_id"]),
    )


def clean_heading_path(
    chunk: dict[str, Any],
) -> list[str]:
    return [
        " ".join(
            str(item).split()
        )
        for item in chunk[
            "heading_path"
        ]
        if str(item).strip()
    ]


def context_record(
    chunk: dict[str, Any],
    *,
    similarity_to_anchor: float | None,
) -> dict[str, Any]:
    return {
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "section_id": chunk["section_id"],
        "domain": chunk["domain"],
        "section_title": chunk["section_title"],
        "heading_path": clean_heading_path(
            chunk
        ),
        "token_count": chunk["token_count"],
        "source_url": chunk["source_url"],
        "content_sha256": chunk[
            "content_sha256"
        ],
        "similarity_to_anchor": (
            round(
                similarity_to_anchor,
                6,
            )
            if similarity_to_anchor is not None
            else None
        ),
        "text": chunk["text"],
    }


def seed_positive_chunk_ids(
    seeds: list[dict[str, Any]],
) -> set[str]:
    result: set[str] = set()

    for seed in seeds:
        for judgment in seed[
            "relevance_judgments"
        ]:
            if (
                isinstance(
                    judgment,
                    dict,
                )
                and int(
                    judgment.get(
                        "grade",
                        0,
                    )
                )
                > 0
            ):
                chunk_id = judgment.get(
                    "chunk_id"
                )

                if isinstance(
                    chunk_id,
                    str,
                ):
                    result.add(
                        chunk_id
                    )

    return result


def choose_balanced_domain(
    *,
    domain_queues: dict[
        str,
        list[dict[str, Any]],
    ],
    domain_positions: dict[str, int],
    assigned_counts: Counter[str],
) -> str:
    available = [
        domain
        for domain, queue in domain_queues.items()
        if domain_positions[domain] < len(queue)
    ]

    if not available:
        raise GoldenSetBuildError(
            "Ran out of unique anchor chunks."
        )

    # Equalize benchmark coverage across domains first; alphabetical order
    # makes ties deterministic.
    return min(
        available,
        key=lambda domain: (
            assigned_counts[domain],
            domain,
        ),
    )


def choose_anchor(
    *,
    domain_queues: dict[
        str,
        list[dict[str, Any]],
    ],
    domain_positions: dict[str, int],
    assigned_counts: Counter[str],
) -> dict[str, Any]:
    domain = choose_balanced_domain(
        domain_queues=domain_queues,
        domain_positions=domain_positions,
        assigned_counts=assigned_counts,
    )

    position = domain_positions[
        domain
    ]

    chunk = domain_queues[
        domain
    ][position]

    domain_positions[
        domain
    ] += 1

    assigned_counts[
        domain
    ] += 1

    return chunk


def dense_neighbors(
    *,
    anchor: dict[str, Any],
    embeddings: np.ndarray,
    chunks: list[dict[str, Any]],
    chunk_to_row: dict[str, int],
    limit: int,
) -> list[
    tuple[dict[str, Any], float]
]:
    anchor_id = str(
        anchor["chunk_id"]
    )

    anchor_row = chunk_to_row[
        anchor_id
    ]

    anchor_vector = embeddings[
        anchor_row
    ]

    scores = embeddings @ anchor_vector

    order = np.argsort(
        -scores,
        kind="stable",
    )

    result: list[
        tuple[
            dict[str, Any],
            float,
        ]
    ] = []

    for row_value in order:
        row = int(
            row_value
        )

        candidate = chunks[
            row
        ]

        if candidate[
            "chunk_id"
        ] == anchor_id:
            continue

        if candidate[
            "section_id"
        ] == anchor[
            "section_id"
        ]:
            continue

        result.append(
            (
                candidate,
                float(
                    scores[row]
                ),
            )
        )

        if len(result) >= limit:
            break

    return result


def select_related_candidates(
    *,
    anchor: dict[str, Any],
    category: str,
    neighbors: list[
        tuple[
            dict[str, Any],
            float,
        ]
    ],
) -> list[
    tuple[
        dict[str, Any],
        float,
    ]
]:
    """
    Related contexts are suggestions only, never automatic gold labels.
    """
    desired = (
        4
        if category
        in {
            "comparison",
            "multi_hop",
            "troubleshooting",
            "negative_near_miss",
        }
        else 3
    )

    same_domain = [
        pair
        for pair in neighbors
        if pair[0]["domain"]
        == anchor["domain"]
    ]

    different_document = [
        pair
        for pair in same_domain
        if pair[0]["document_id"]
        != anchor["document_id"]
    ]

    cross_domain = [
        pair
        for pair in neighbors
        if pair[0]["domain"]
        != anchor["domain"]
    ]

    ordered: list[
        tuple[
            dict[str, Any],
            float,
        ]
    ] = []

    def add_pairs(
        pairs: list[
            tuple[
                dict[str, Any],
                float,
            ]
        ]
    ) -> None:
        seen = {
            str(item[0]["chunk_id"])
            for item in ordered
        }

        for pair in pairs:
            chunk_id = str(
                pair[0]["chunk_id"]
            )

            if chunk_id in seen:
                continue

            ordered.append(
                pair
            )

            seen.add(
                chunk_id
            )

            if len(ordered) >= desired:
                return

    if category == "comparison":
        add_pairs(
            different_document
        )
        add_pairs(
            same_domain
        )
        add_pairs(
            cross_domain
        )

    elif category == "multi_hop":
        add_pairs(
            different_document
        )
        add_pairs(
            cross_domain
        )
        add_pairs(
            same_domain
        )

    elif category == "negative_near_miss":
        add_pairs(
            same_domain
        )
        add_pairs(
            different_document
        )
        add_pairs(
            cross_domain
        )

    else:
        add_pairs(
            same_domain
        )
        add_pairs(
            different_document
        )
        add_pairs(
            cross_domain
        )

    return ordered[
        :desired
    ]


# =============================================================================
# Labeling-pack construction
# =============================================================================


def seed_pack_record(
    seed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "question_id": seed[
            "question_id"
        ],
        "status": "seed_complete",
        "target": {
            "category": seed[
                "category"
            ],
            "difficulty": seed[
                "difficulty"
            ],
            "split": seed[
                "split"
            ],
        },
        "question": seed[
            "question"
        ],
        "answerable": seed[
            "answerable"
        ],
        "relevance_judgments": seed[
            "relevance_judgments"
        ],
        "reference_answer": seed.get(
            "reference_answer"
        ),
        "source_document_ids": seed.get(
            "source_document_ids",
            [],
        ),
        "tags": seed.get(
            "tags",
            [],
        ),
        "notes": seed.get(
            "notes",
            "",
        ),
        "authoring_guidance": None,
        "anchor_context": None,
        "related_context_candidates": [],
        "labeling_warning": None,
    }


def draft_pack_record(
    *,
    slot: dict[str, str],
    anchor: dict[str, Any],
    related: list[
        tuple[
            dict[str, Any],
            float,
        ]
    ],
) -> dict[str, Any]:
    category = slot[
        "category"
    ]

    answerable = (
        category
        != "negative_near_miss"
    )

    return {
        "question_id": slot[
            "question_id"
        ],
        "status": "needs_labeling",
        "target": {
            "category": category,
            "difficulty": slot[
                "difficulty"
            ],
            "split": slot[
                "split"
            ],
        },

        # These fields are intentionally blank until a human labels them.
        "question": None,
        "answerable": answerable,
        "relevance_judgments": [],
        "reference_answer": None,
        "source_document_ids": [],
        "tags": [],
        "notes": "",

        "authoring_guidance": AUTHORING_GUIDANCE[
            category
        ],

        "anchor_context": context_record(
            anchor,
            similarity_to_anchor=None,
        ),

        "related_context_candidates": [
            context_record(
                chunk,
                similarity_to_anchor=score,
            )
            for chunk, score in related
        ],

        "labeling_warning": (
            "Anchor and related contexts are candidate authoring material "
            "only. They are NOT automatic relevance judgments. Read the "
            "contexts, write the question, and label only chunks that truly "
            "answer that question."
        ),
    }


def validate_final_plan_counts(
    pack: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(pack) != TOTAL_QUESTIONS:
        raise GoldenSetBuildError(
            f"Expected 100 plan records, got {len(pack)}."
        )

    ids = [
        str(record["question_id"])
        for record in pack
    ]

    if len(ids) != len(
        set(ids)
    ):
        raise GoldenSetBuildError(
            "Duplicate question IDs in final labeling pack."
        )

    category = Counter(
        str(record["target"]["category"])
        for record in pack
    )

    difficulty = Counter(
        str(record["target"]["difficulty"])
        for record in pack
    )

    split = Counter(
        str(record["target"]["split"])
        for record in pack
    )

    category_difficulty: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)

    category_split: dict[
        str,
        Counter[str],
    ] = defaultdict(Counter)

    for record in pack:
        target = record[
            "target"
        ]

        category_difficulty[
            str(target["category"])
        ][
            str(target["difficulty"])
        ] += 1

        category_split[
            str(target["category"])
        ][
            str(target["split"])
        ] += 1

    if dict(category) != CATEGORY_TARGETS:
        raise GoldenSetBuildError(
            "Final category counts do not match targets."
        )

    if dict(difficulty) != DIFFICULTY_TARGETS:
        raise GoldenSetBuildError(
            "Final difficulty counts do not match targets."
        )

    if dict(split) != SPLIT_TARGETS:
        raise GoldenSetBuildError(
            "Final split counts do not match targets."
        )

    for category_name in CATEGORY_TARGETS:
        if dict(
            category_difficulty[
                category_name
            ]
        ) != {
            key: value
            for key, value in (
                CATEGORY_DIFFICULTY_TARGETS[
                    category_name
                ].items()
            )
            if value > 0
        }:
            raise GoldenSetBuildError(
                f"Final difficulty matrix mismatch for {category_name}."
            )

        if dict(
            category_split[
                category_name
            ]
        ) != CATEGORY_SPLIT_TARGETS[
            category_name
        ]:
            raise GoldenSetBuildError(
                f"Final split matrix mismatch for {category_name}."
            )

    return {
        "category": dict(
            sorted(
                category.items()
            )
        ),
        "difficulty": dict(
            sorted(
                difficulty.items()
            )
        ),
        "split": dict(
            sorted(
                split.items()
            )
        ),
        "category_difficulty": {
            category_name: dict(
                sorted(
                    category_difficulty[
                        category_name
                    ].items()
                )
            )
            for category_name in CATEGORY_TARGETS
        },
        "category_split": {
            category_name: dict(
                sorted(
                    category_split[
                        category_name
                    ].items()
                )
            )
            for category_name in CATEGORY_TARGETS
        },
    }


# =============================================================================
# Output
# =============================================================================


def write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
) -> str:
    ordered = sorted(
        records,
        key=lambda record: int(
            QUESTION_ID_RE.fullmatch(
                str(
                    record[
                        "question_id"
                    ]
                )
            ).group("number")
        ),
    )

    content = "\n".join(
        canonical_json_line(
            record
        )
        for record in ordered
    )

    if content:
        content += "\n"

    atomic_write_text(
        path,
        content,
    )

    return (
        "sha256:"
        + hashlib.sha256(
            content.encode(
                "utf-8"
            )
        ).hexdigest()
    )


def build_plan_json(
    *,
    seeds: list[dict[str, Any]],
    final_counts: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    return {
        "builder_version": BUILDER_VERSION,
        "benchmark_size": TOTAL_QUESTIONS,
        "seed_questions": len(seeds),
        "questions_needing_labeling": (
            TOTAL_QUESTIONS
            - len(seeds)
        ),
        "targets": {
            "category": CATEGORY_TARGETS,
            "difficulty": DIFFICULTY_TARGETS,
            "split": SPLIT_TARGETS,
            "category_difficulty": (
                CATEGORY_DIFFICULTY_TARGETS
            ),
            "category_split": (
                CATEGORY_SPLIT_TARGETS
            ),
        },
        "validated_final_counts": final_counts,
        "labeling_pack": output_path.as_posix(),
        "workflow": [
            "Open each needs_labeling record.",
            "Read anchor_context and related_context_candidates.",
            "Write a natural question matching target category/difficulty.",
            "Assign relevance grades 0-3 only after reading the evidence.",
            "For multi-hop/comparison questions, label every answer-bearing chunk.",
            "For negative_near_miss questions, keep answerable=false and no positive judgments.",
            "Copy completed records into data/evaluation/golden_questions.jsonl.",
            "Run groundtruth.evaluation.evaluate_retrieval after validation.",
        ],
    }


def build_report(
    *,
    chunks_path: Path,
    seed_path: Path,
    embeddings_path: Path,
    metadata_path: Path,
    output_path: Path,
    output_sha256: str,
    plan_path: Path,
    pack: list[dict[str, Any]],
    final_counts: dict[str, Any],
) -> dict[str, Any]:
    draft_records = [
        record
        for record in pack
        if record["status"]
        == "needs_labeling"
    ]

    domain_counts = Counter(
        str(
            record[
                "anchor_context"
            ][
                "domain"
            ]
        )
        for record in draft_records
    )

    source_document_counts = Counter(
        str(
            record[
                "anchor_context"
            ][
                "document_id"
            ]
        )
        for record in draft_records
    )

    return {
        "builder_version": BUILDER_VERSION,
        "status": "SUCCESS",

        "inputs": {
            "chunks": chunks_path.as_posix(),
            "chunks_sha256": (
                "sha256:"
                + sha256_file(
                    chunks_path
                )
            ),
            "seed_questions": seed_path.as_posix(),
            "seed_questions_sha256": (
                "sha256:"
                + sha256_file(
                    seed_path
                )
            ),
            "embeddings": embeddings_path.as_posix(),
            "metadata": metadata_path.as_posix(),
        },

        "outputs": {
            "labeling_pack": output_path.as_posix(),
            "labeling_pack_sha256": output_sha256,
            "plan": plan_path.as_posix(),
        },

        "summary": {
            "total_question_slots": len(pack),
            "seed_complete": sum(
                record["status"]
                == "seed_complete"
                for record in pack
            ),
            "needs_labeling": len(
                draft_records
            ),
            "unique_anchor_chunks": len(
                {
                    str(
                        record[
                            "anchor_context"
                        ][
                            "chunk_id"
                        ]
                    )
                    for record in draft_records
                }
            ),
            "anchor_domain_count": len(
                domain_counts
            ),
            "anchor_document_count": len(
                source_document_counts
            ),
        },

        "validated_targets": final_counts,

        "anchor_distribution": {
            "by_domain": dict(
                sorted(
                    domain_counts.items()
                )
            ),
            "by_document": dict(
                sorted(
                    source_document_counts.items()
                )
            ),
        },

        "safety": {
            "automatic_questions_generated": False,
            "automatic_gold_judgments_generated": False,
            "candidate_contexts_are_gold": False,
            "purpose": (
                "Create a balanced, corpus-grounded human-labeling pack "
                "for the remaining benchmark questions."
            ),
        },
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_build(
    *,
    chunks_path: Path,
    seed_path: Path,
    embeddings_path: Path,
    metadata_path: Path,
    output_path: Path,
    plan_path: Path,
    report_path: Path,
) -> int:
    validate_targets()

    print(
        f"Loading indexable chunks: {chunks_path}"
    )

    chunks = load_and_validate_chunks(
        chunks_path
    )

    chunks_by_id = {
        str(chunk["chunk_id"]): chunk
        for chunk in chunks
    }

    print(
        f"Loaded {len(chunks):,} indexable chunks."
    )

    print(
        f"Loading seed questions: {seed_path}"
    )

    seeds = load_jsonl(
        seed_path
    )

    validate_seed_set(
        seeds
    )

    counts = seed_counts(
        seeds
    )

    ensure_seed_does_not_exceed_targets(
        counts
    )

    print(
        f"Loaded {len(seeds)} validated seed questions."
    )

    print(
        "Loading dense artifacts for related-context suggestions..."
    )

    (
        embeddings,
        metadata,
        chunk_to_row,
    ) = load_dense_artifacts(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
        chunks_by_id=chunks_by_id,
    )

    # Reorder chunks so chunk list row N exactly corresponds to embedding row N.
    chunks = [
        chunks_by_id[
            str(record["chunk_id"])
        ]
        for record in metadata
    ]

    used_seed_chunks = seed_positive_chunk_ids(
        seeds
    )

    candidate_anchors = [
        chunk
        for chunk in chunks
        if str(
            chunk["chunk_id"]
        )
        not in used_seed_chunks
    ]

    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for chunk in candidate_anchors:
        grouped[
            str(chunk["domain"])
        ].append(chunk)

    domain_queues: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for domain, domain_chunks in grouped.items():
        domain_queues[
            domain
        ] = sorted(
            domain_chunks,
            key=chunk_quality_score,
        )

    if not domain_queues:
        raise GoldenSetBuildError(
            "No anchor candidates remain after excluding seed-positive chunks."
        )

    slot_specs = make_remaining_slot_specs(
        seeds
    )

    domain_positions = {
        domain: 0
        for domain in domain_queues
    }

    assigned_domain_counts: Counter[
        str
    ] = Counter()

    draft_records: list[
        dict[str, Any]
    ] = []

    print(
        f"Building {len(slot_specs)} labeling slots..."
    )

    for index, slot in enumerate(
        slot_specs,
        start=1,
    ):
        anchor = choose_anchor(
            domain_queues=domain_queues,
            domain_positions=domain_positions,
            assigned_counts=assigned_domain_counts,
        )

        neighbors = dense_neighbors(
            anchor=anchor,
            embeddings=embeddings,
            chunks=chunks,
            chunk_to_row=chunk_to_row,
            limit=30,
        )

        related = select_related_candidates(
            anchor=anchor,
            category=slot["category"],
            neighbors=neighbors,
        )

        draft_records.append(
            draft_pack_record(
                slot=slot,
                anchor=anchor,
                related=related,
            )
        )

        print(
            f"[{index:03d}/{len(slot_specs):03d}] "
            f"{slot['question_id']}  "
            f"{slot['category']:<20} "
            f"{slot['difficulty']:<6} "
            f"{slot['split']:<4} "
            f"anchor={anchor['chunk_id']}"
        )

    pack = [
        seed_pack_record(
            seed
        )
        for seed in seeds
    ] + draft_records

    final_counts = validate_final_plan_counts(
        pack
    )

    output_sha256 = write_jsonl(
        output_path,
        pack,
    )

    plan = build_plan_json(
        seeds=seeds,
        final_counts=final_counts,
        output_path=output_path,
    )

    atomic_write_text(
        plan_path,
        json.dumps(
            plan,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    report = build_report(
        chunks_path=chunks_path,
        seed_path=seed_path,
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
        output_path=output_path,
        output_sha256=output_sha256,
        plan_path=plan_path,
        pack=pack,
        final_counts=final_counts,
    )

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

    print()
    print("-" * 78)
    print("GroundTruth Golden-Set Labeling Pack")
    print("-" * 78)
    print(
        f"Seed complete:        "
        f"{report['summary']['seed_complete']}"
    )
    print(
        f"Needs labeling:       "
        f"{report['summary']['needs_labeling']}"
    )
    print(
        f"Total planned:        "
        f"{report['summary']['total_question_slots']}"
    )
    print(
        f"Anchor domains:       "
        f"{report['summary']['anchor_domain_count']}"
    )
    print(
        f"Anchor documents:     "
        f"{report['summary']['anchor_document_count']}"
    )
    print(
        f"Labeling pack:        "
        f"{output_path}"
    )
    print(
        f"Plan:                 "
        f"{plan_path}"
    )
    print(
        f"Report:               "
        f"{report_path}"
    )
    print("Status:               SUCCESS")
    print("-" * 78)

    return 0


# =============================================================================
# CLI
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic 100-question GroundTruth labeling plan "
            "from the retrieval-ready Kubernetes corpus. The script "
            "preserves existing seed questions and supplies real anchor/"
            "related chunks for human authoring; it does not fabricate "
            "gold relevance judgments."
        )
    )

    parser.add_argument(
        "--chunks",
        type=Path,
        default=DEFAULT_CHUNKS_PATH,
        help=(
            "Indexable chunks JSONL. "
            f"Default: {DEFAULT_CHUNKS_PATH}"
        ),
    )

    parser.add_argument(
        "--seed",
        type=Path,
        default=DEFAULT_SEED_PATH,
        help=(
            "Existing golden seed questions JSONL. "
            f"Default: {DEFAULT_SEED_PATH}"
        ),
    )

    parser.add_argument(
        "--embeddings",
        type=Path,
        default=DEFAULT_EMBEDDINGS_PATH,
        help=(
            "Dense embedding matrix. "
            f"Default: {DEFAULT_EMBEDDINGS_PATH}"
        ),
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help=(
            "Dense metadata JSONL. "
            f"Default: {DEFAULT_METADATA_PATH}"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=(
            "Human-labeling candidate JSONL. "
            f"Default: {DEFAULT_OUTPUT_PATH}"
        ),
    )

    parser.add_argument(
        "--plan-output",
        type=Path,
        default=DEFAULT_PLAN_PATH,
        help=(
            "Benchmark plan JSON. "
            f"Default: {DEFAULT_PLAN_PATH}"
        ),
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=(
            "Build report JSON. "
            f"Default: {DEFAULT_REPORT_PATH}"
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return run_build(
            chunks_path=args.chunks,
            seed_path=args.seed,
            embeddings_path=args.embeddings,
            metadata_path=args.metadata,
            output_path=args.output,
            plan_path=args.plan_output,
            report_path=args.report_output,
        )
    except GoldenSetBuildError as exc:
        print()
        print(
            f"Golden-set build failed: {exc}"
        )
        return 1
    except KeyboardInterrupt:
        print()
        print(
            "Golden-set build interrupted."
        )
        return 130
    except Exception as exc:
        print()
        print(
            "Golden-set build failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

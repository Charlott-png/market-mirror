"""Reproducible synthetic teaching data and validation before splitting."""

from collections import Counter, defaultdict
from decimal import Decimal
from datetime import date
import hashlib
import json
import random
import re

from app.forms import parse_price
from app.models.product import CATEGORIES, CONDITIONS

VOCABULARY = {
    "electronics": ("keyboard mouse speaker monitor camera router tablet charger headphones microphone projector calculator", "electronic digital circuit battery cable device"),
    "home_garden": ("lamp chair planter cushion vase rug wateringcan shelf mirror curtain stool basket", "house garden furniture room decoration home"),
    "clothing": ("jacket shirt trousers scarf coat sweater dress boots sandals gloves skirt hat", "fabric wearable garment fashion cotton clothing"),
    "books_media": ("novel textbook dictionary atlas comic biography poetry cookbook magazine audiobook encyclopedia journal", "reading pages literature author printed book"),
    "sports_outdoors": ("basketball football racket tent lantern helmet skateboard dumbbell backpack kayak compass skates", "outdoor exercise fitness sport camping training"),
    "toys_games": ("puzzle chess doll blocks marbles kite dominoes teddy robot puppet yo-yo trainset", "play toy children family game fun"),
    "other": ("yarn ribbon beads canvas glue paper stencil clay markers brush thread wax", "craft hobby handmade supplies creative material"),
}


def synthetic_rows():
    """168 intentionally simple examples. These are NOT measured market prices."""
    rows = []
    conditions = list(CONDITIONS)
    for category_number, (category, (nouns, description)) in enumerate(VOCABULARY.items()):
        for group, noun in enumerate(nouns.split()):
            for variant in range(2):
                condition = conditions[(group + variant) % len(conditions)]
                price = Decimal(12 + category_number * 8 + group * 3 + variant * 2)
                rows.append(dict(product_id=f"synthetic-{category}-{group}-{variant}",
                    duplicate_group=f"{category}-{noun}", title=f"Useful {noun}",
                    description=f"{noun.capitalize()} for {description}. Fictional example for classroom practice.",
                    category=category, condition=condition, currency="USD", price=f"{price:.2f}",
                    source="project-authored-synthetic-v1", licence="Project-authored teaching examples",
                    collected_at="2026-10-25", synthetic=True))
    return rows


def fingerprint(rows):
    encoded = json.dumps(rows, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def normalized_text(row):
    return " ".join(re.findall(r"[a-z]+", (row["title"] + " " + row["description"]).lower()))


def prepare_dataset(rows):
    clean, rejected = [], []
    ids, text_groups, group_labels = set(), {}, {}
    title_groups = defaultdict(list)
    for row_number, original in enumerate(rows):
        row = dict(original)
        try:
            required = ("product_id", "duplicate_group", "title", "description", "category", "condition", "currency", "price", "source", "licence", "collected_at")
            if set(row) - set(required) - {"synthetic"}:
                raise ValueError("unexpected_field")
            if any(not isinstance(row.get(key), str) for key in required):
                raise ValueError("invalid_field_type")
            if any(not str(row.get(key, "")).strip() for key in required):
                raise ValueError("missing_field_or_provenance")
            date.fromisoformat(row['collected_at'])
            if row["product_id"] in ids:
                raise ValueError("duplicate_id")
            if row["category"] not in CATEGORIES or row["condition"] not in CONDITIONS or row["currency"] != "USD":
                raise ValueError("invalid_choice")
            if not 3 <= len(row["title"].strip()) <= 120 or not 10 <= len(row["description"].strip()) <= 5000:
                raise ValueError("invalid_text_length")
            row["price"] = str(parse_price(str(row["price"])))
            if row.get("synthetic") not in (True, False, "true", "false", "True", "False"):
                raise ValueError("missing_synthetic_flag")
            row["synthetic"] = row["synthetic"] in (True, "true", "True")
            key = normalized_text(row)
            if key in text_groups and text_groups[key] != row["duplicate_group"]:
                raise ValueError("duplicate_text_crosses_groups")
            # Conservative near-duplicate rule: identical normalized title and
            # at least 90% shared description tokens. Suspected copies must be
            # assigned the same group by the data curator before training.
            title_key = " ".join(re.findall(r"\w+", row['title'].lower()))
            tokens = set(re.findall(r"\w+", row['description'].lower()))
            for previous_tokens, previous_group in title_groups[title_key]:
                overlap = len(tokens & previous_tokens) / max(1, len(tokens | previous_tokens))
                if overlap >= .90 and previous_group != row['duplicate_group']:
                    raise ValueError('near_duplicate_crosses_groups')
            if row["duplicate_group"] in group_labels and group_labels[row["duplicate_group"]] != row["category"]:
                raise ValueError("conflicting_group_labels")
            ids.add(row["product_id"])
            text_groups[key] = row["duplicate_group"]
            group_labels[row["duplicate_group"]] = row["category"]
            title_groups[title_key].append((tokens, row['duplicate_group']))
            clean.append(row)
        except (ValueError, TypeError, ArithmeticError) as error:
            rejected.append({"row": row_number, "reason": str(error)})
    clean.sort(key=lambda row: row["product_id"])
    groups = defaultdict(list)
    for group, category in group_labels.items():
        groups[category].append(group)
    if any(len(groups[category]) < 5 for category in CATEGORIES):
        raise ValueError("Need at least five independent groups in each approved category.")
    membership = {}
    rng = random.Random(42)
    for category in sorted(CATEGORIES):
        keys = sorted(groups[category])
        rng.shuffle(keys)
        training_end = max(1, int(len(keys) * .6))
        validation_end = min(len(keys) - 1, training_end + max(1, int(len(keys) * .2)))
        for index, key in enumerate(keys):
            membership[key] = "train" if index < training_end else "validation" if index < validation_end else "test"
    result = {split: [row for row in clean if membership[row["duplicate_group"]] == split]
              for split in ("train", "validation", "test")}
    result.update(dataset_sha256=fingerprint(clean), rejected_count=len(rejected), rejected=rejected,
                  synthetic=all(row["synthetic"] for row in clean), random_seed=42,
                  class_counts=dict(Counter(row["category"] for row in clean)))
    return result

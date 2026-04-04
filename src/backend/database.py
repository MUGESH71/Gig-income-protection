"""
src/backend/database.py
------------------------
JSON-file-based persistence layer for GigShield.

Provides simple read/write helpers for:
  - data/users.json
  - data/policies.json
  - data/claims.json

In production these would be replaced by a proper RDBMS / NoSQL store.
"""

import json
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Resolve data directory relative to this file regardless of working dir
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent          # src/backend/
_DATA_DIR = _HERE.parent.parent / "data"         # project_root/data/

USERS_FILE   = _DATA_DIR / "users.json"
POLICIES_FILE = _DATA_DIR / "policies.json"
CLAIMS_FILE  = _DATA_DIR / "claims.json"


def _load(filepath: Path) -> list:
    """Load a JSON array from disk; return [] if missing/corrupt."""
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save(filepath: Path, data: list) -> None:
    """Persist a list as a pretty-printed JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

def get_all_users() -> list:
    return _load(USERS_FILE)


def get_user(user_id: str) -> Optional[dict]:
    return next((u for u in get_all_users() if u["user_id"] == user_id), None)


def get_user_by_name(name: str) -> Optional[dict]:
    return next(
        (u for u in get_all_users() if u["name"].lower() == name.lower()), None
    )


def save_user(user: dict) -> None:
    users = get_all_users()
    # Update existing or append
    idx = next((i for i, u in enumerate(users) if u["user_id"] == user["user_id"]), None)
    if idx is not None:
        users[idx] = user
    else:
        users.append(user)
    _save(USERS_FILE, users)


# ---------------------------------------------------------------------------
# Policy operations
# ---------------------------------------------------------------------------

def get_all_policies() -> list:
    return _load(POLICIES_FILE)


def get_policy(policy_id: str) -> Optional[dict]:
    return next((p for p in get_all_policies() if p["policy_id"] == policy_id), None)


def get_policy_by_user(user_id: str) -> Optional[dict]:
    return next((p for p in get_all_policies() if p["user_id"] == user_id), None)


def save_policy(policy: dict) -> None:
    policies = get_all_policies()
    idx = next(
        (i for i, p in enumerate(policies) if p["policy_id"] == policy["policy_id"]),
        None,
    )
    if idx is not None:
        policies[idx] = policy
    else:
        policies.append(policy)
    _save(POLICIES_FILE, policies)


# ---------------------------------------------------------------------------
# Claim operations
# ---------------------------------------------------------------------------

def get_all_claims() -> list:
    return _load(CLAIMS_FILE)


def get_claims_by_user(user_id: str) -> list:
    return [c for c in get_all_claims() if c["user_id"] == user_id]


def save_claim(claim: dict) -> None:
    claims = get_all_claims()
    idx = next(
        (i for i, c in enumerate(claims) if c["claim_id"] == claim["claim_id"]), None
    )
    if idx is not None:
        claims[idx] = claim
    else:
        claims.append(claim)
    _save(CLAIMS_FILE, claims)


def generate_id(prefix: str, collection: list, id_field: str) -> str:
    """
    Generate the next sequential ID (e.g. USR006, POL006, CLM004).
    """
    existing = [item[id_field] for item in collection if id_field in item]
    nums = []
    for eid in existing:
        try:
            nums.append(int(eid.replace(prefix, "")))
        except ValueError:
            pass
    next_num = max(nums, default=0) + 1
    return f"{prefix}{next_num:03d}"
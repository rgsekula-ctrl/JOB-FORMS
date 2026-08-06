"""
Ryan OS - Asset Registry (Phase 2)
==================================

The authoritative directory of operational resources. An agent asks this module
"where is the thing I need?" *before* searching the filesystem, Drive, or the
web.

The important behavior is what happens on a miss. A registry that returns
nothing invites the agent to go hunting and pick whatever it finds, which is
exactly how three versions of a template end up in circulation. So `resolve()`
never returns a bare None - it returns a `Resolution` that either points at an
authoritative asset or states explicitly that this is a gap and must be flagged.

Standard library only, same as the decision engine.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

__all__ = [
    "Asset",
    "Resolution",
    "AssetRegistry",
    "AUTHORITATIVE",
    "CANDIDATE",
    "DEPRECATED",
    "GAP",
]

REGISTRY_VERSION = "1.0.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(_HERE, "registry.json")
SCHEMA_PATH = os.path.join(_HERE, "schema", "asset.schema.json")

AUTHORITATIVE = "authoritative"
CANDIDATE = "candidate"
DEPRECATED = "deprecated"
GAP = "gap"

# Resolution outcomes.
FOUND = "FOUND"                      # an authoritative asset matched
FOUND_CANDIDATE = "FOUND_CANDIDATE"  # matched, but not blessed yet
FOUND_DEPRECATED = "FOUND_DEPRECATED"  # matched a retired asset; follow replaced_by
GAP_FLAGGED = "GAP_FLAGGED"          # registry knows this should exist and does not
NOT_REGISTERED = "NOT_REGISTERED"    # registry has never heard of it

# Minimum "strong" relevance before an asset counts as a match at all.
# 4 = one category-token hit, the weakest signal we still trust.
_MIN_STRONG_SCORE = 4

_STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are",
    "where", "what", "which", "our", "my", "we", "i", "do", "does", "use", "used",
    "need", "find", "get", "current", "latest", "version", "file", "document",
}


@dataclass
class Asset:
    asset_id: str
    name: str
    category: str
    status: str
    what_it_is: str
    where_it_is: Dict[str, str]
    owner: str
    use_when: str
    do_not_use_when: str = ""
    replaces: List[str] = field(default_factory=list)
    replaced_by: str = ""
    keywords: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    gap_recommendation: str = ""
    last_verified: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Asset":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def location(self) -> str:
        w = self.where_it_is or {}
        kind, path = w.get("kind", "unknown"), w.get("path", "")
        return f"{kind}: {path}" if path else kind

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Resolution:
    """The answer to 'where is the authoritative X?'"""

    outcome: str
    query: str
    asset: Optional[Asset] = None
    alternatives: List[Asset] = field(default_factory=list)
    message: str = ""
    action_required: str = ""

    @property
    def usable(self) -> bool:
        return self.outcome in (FOUND, FOUND_CANDIDATE)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["usable"] = self.usable
        return d


def _tokens(text: str) -> List[str]:
    words = re.split(r"[^a-z0-9]+", (text or "").lower())
    return [w for w in words if w and w not in _STOPWORDS and len(w) > 1]


class AssetRegistry:
    def __init__(self, assets: Optional[List[Asset]] = None, meta: Optional[Dict[str, Any]] = None):
        self.assets = assets or []
        self.meta = meta or {}

    # -- loading ----------------------------------------------------------

    @classmethod
    def load(cls, path: str = REGISTRY_PATH) -> "AssetRegistry":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assets = [Asset.from_dict(a) for a in data.get("assets", [])]
        meta = {k: v for k, v in data.items() if k != "assets"}
        return cls(assets, meta)

    # -- basic access -----------------------------------------------------

    def get(self, asset_id: str) -> Optional[Asset]:
        for a in self.assets:
            if a.asset_id == asset_id:
                return a
        return None

    def by_category(self, category: str) -> List[Asset]:
        return [a for a in self.assets if a.category == category]

    def by_status(self, status: str) -> List[Asset]:
        return [a for a in self.assets if a.status == status]

    def gaps(self) -> List[Asset]:
        return self.by_status(GAP)

    def categories(self) -> List[str]:
        return sorted({a.category for a in self.assets})

    # -- search -----------------------------------------------------------

    def search(self, query: str, include_gaps: bool = True) -> List[Asset]:
        """Rank assets against a free-text query.

        Weighting reflects how lookups actually go wrong: an exact id or name
        hit is almost always right, a keyword hit is usually right, and a hit
        buried in prose is weak evidence.
        """
        q = (query or "").strip().lower()
        if not q:
            return []

        qt = set(_tokens(q))
        scored: List[tuple] = []

        for a in self.assets:
            if not include_gaps and a.status == GAP:
                continue

            # "Strong" evidence is a hit on identity: the id, the name, a
            # declared keyword, or the category. Prose is deliberately NOT
            # strong - a query matching one incidental word in a description
            # must never be enough to declare an asset authoritative. Returning
            # a confident wrong answer is worse than returning nothing, because
            # the caller stops looking.
            strong = 0
            if q == a.asset_id.lower() or q == a.name.lower():
                strong += 100

            strong += 12 * len(qt & set(_tokens(a.name)))
            strong += 8 * len(qt & set(_tokens(a.asset_id)))

            for kw in a.keywords:
                kw_l = kw.lower()
                if kw_l == q:
                    strong += 30
                elif kw_l in q or q in kw_l:
                    strong += 14
                else:
                    strong += 5 * len(qt & set(_tokens(kw)))

            strong += 4 * len(qt & set(_tokens(a.category)))

            if strong < _MIN_STRONG_SCORE:
                continue

            score = strong + len(qt & set(_tokens(f"{a.what_it_is} {a.use_when}")))

            # Nudge authoritative above retired versions at equal relevance.
            if a.status == AUTHORITATIVE:
                score += 3
            elif a.status == DEPRECATED:
                score -= 2

            scored.append((score, a))

        scored.sort(key=lambda t: (-t[0], t[1].asset_id))
        return [a for _, a in scored]

    # -- the discovery rule ------------------------------------------------

    def resolve(self, query: str) -> Resolution:
        """Answer 'where is the authoritative X?' - never with a bare miss.

        This is the function that enforces the Resource Discovery Rule. Every
        outcome tells the caller what to do next, including the two miss cases.
        """
        matches = self.search(query)

        if not matches:
            return Resolution(
                outcome=NOT_REGISTERED,
                query=query,
                message=(
                    f"No registered asset matches '{query}'. Ryan OS is not the authority "
                    "for this resource yet."
                ),
                action_required=(
                    "Do NOT search elsewhere and use whatever turns up. Tell Ryan the "
                    "registry has no entry for this, say what you needed it for, and "
                    "recommend adding it to ryan-os/asset-registry/registry.json."
                ),
            )

        best = matches[0]
        rest = matches[1:4]

        if best.status == AUTHORITATIVE:
            return Resolution(
                outcome=FOUND, query=query, asset=best, alternatives=rest,
                message=f"{best.name} - {best.location}",
                action_required="Use it.",
            )

        if best.status == GAP:
            return Resolution(
                outcome=GAP_FLAGGED, query=query, asset=best, alternatives=rest,
                message=(
                    f"'{best.name}' is a KNOWN GAP. Ryan OS knows this resource should exist "
                    "but has no authoritative version on file."
                ),
                action_required=(
                    "Do NOT substitute another version. Flag the gap to Ryan with this "
                    f"recommendation: {best.gap_recommendation}"
                ),
            )

        if best.status == DEPRECATED:
            successor = self.get(best.replaced_by) if best.replaced_by else None
            if successor:
                return Resolution(
                    outcome=FOUND, query=query, asset=successor, alternatives=[best] + rest,
                    message=(
                        f"'{best.name}' is deprecated. The current version is "
                        f"{successor.name} - {successor.location}"
                    ),
                    action_required="Use the successor. Do not use the deprecated asset for new work.",
                )
            return Resolution(
                outcome=FOUND_DEPRECATED, query=query, asset=best, alternatives=rest,
                message=f"'{best.name}' is deprecated and no successor is registered.",
                action_required="Flag this to Ryan - a deprecated asset with no replacement is a gap.",
            )

        return Resolution(
            outcome=FOUND_CANDIDATE, query=query, asset=best, alternatives=rest,
            message=(
                f"{best.name} - {best.location}. Status is CANDIDATE: it exists but has not "
                "been declared authoritative."
            ),
            action_required=(
                "Usable, but say so when you use it, and ask Ryan to confirm whether it "
                "should be marked authoritative."
            ),
        )

    # -- integrity ---------------------------------------------------------

    def validate(self) -> List[str]:
        """Structural checks. Returns a list of problems, empty when clean."""
        errors: List[str] = []

        try:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
                schema = json.load(fh)
        except OSError:
            schema = {}

        props = schema.get("properties", {})
        required = schema.get("required", [])
        ids = set()

        for a in self.assets:
            d = a.to_dict()
            where = f"{a.asset_id or '<no id>'}"

            if a.asset_id in ids:
                errors.append(f"{where}: duplicate asset_id")
            ids.add(a.asset_id)

            if not re.match(r"^[a-z0-9-]+$", a.asset_id or ""):
                errors.append(f"{where}: asset_id must be lowercase slug")

            for key in required:
                if not d.get(key):
                    errors.append(f"{where}: missing required field '{key}'")

            for key, spec in props.items():
                if key in d and "enum" in spec and d[key] and d[key] not in spec["enum"]:
                    errors.append(f"{where}: {key} '{d[key]}' not in {spec['enum']}")

            kind = (a.where_it_is or {}).get("kind", "")
            if a.status == GAP:
                if not a.gap_recommendation:
                    errors.append(f"{where}: status 'gap' requires gap_recommendation")
            elif kind == "unknown":
                errors.append(f"{where}: location kind is 'unknown' but status is not 'gap'")
            elif not (a.where_it_is or {}).get("path") and not (a.where_it_is or {}).get("detail"):
                errors.append(f"{where}: no path or detail - nobody can find it")

            if a.status == DEPRECATED and not a.replaced_by:
                errors.append(f"{where}: deprecated assets should name a replaced_by (or be deleted)")

        # Referential integrity - a dangling pointer is worse than no pointer.
        for a in self.assets:
            for ref in a.related:
                if ref not in ids:
                    errors.append(f"{a.asset_id}: related '{ref}' is not a registered asset")
            if a.replaced_by and a.replaced_by not in ids:
                errors.append(f"{a.asset_id}: replaced_by '{a.replaced_by}' is not a registered asset")
            for ref in a.replaces:
                if ref not in ids and "-" in ref and " " not in ref:
                    errors.append(f"{a.asset_id}: replaces '{ref}' looks like an asset_id but is not registered")

        return errors

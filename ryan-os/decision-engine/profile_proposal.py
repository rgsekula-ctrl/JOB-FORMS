"""
Ryan OS - Builder Profile Proposal Engine (Phase 2)
===================================================

When no Builder Profile exists, the Orchestrator must not ask "what should we
do?". It presents a governed recommendation that Ryan can approve, convert into
a Builder Profile, or override.

This module produces that recommendation:

  * a ranked set of classification candidates, each with confidence and the
    actual reasoning that produced the ranking,
  * recommended equipment, gross margin, pricing profile, and standard options
    for each candidate,
  * a fully pre-populated Builder Profile ready to write to disk, so approving
    it costs Ryan a keystroke rather than a form.

Layering: this imports from `engine`, never the reverse. The decision engine
stays dependency-free and unaware of proposals; the CLI and the web form compose
the two.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import engine
from engine import HIGH, LOW, MEDIUM, find_keywords, load_defaults

__all__ = [
    "ClassificationCandidate",
    "ProfileProposal",
    "propose_profile",
    "render_proposal",
    "build_profile",
    "slugify",
]

PROPOSAL_VERSION = "1.0.0"


# --------------------------------------------------------------------------
# Data types
# --------------------------------------------------------------------------

@dataclass
class ClassificationCandidate:
    key: str
    label: str
    score: int
    confidence: str
    reasoning: List[str] = field(default_factory=list)

    builder_type: str = ""
    customer_type: str = ""

    equipment: Dict[str, str] = field(default_factory=dict)
    gross_margin: float = 0.0
    gross_margin_display: str = ""
    pricing_profile_key: str = ""
    pricing_profile_label: str = ""
    pricing_profile_basis: str = ""
    labor: str = ""
    burdens: str = ""
    options: List[str] = field(default_factory=list)


@dataclass
class ProfileProposal:
    builder_display: str
    domain: str
    profile_exists: bool
    existing_profile_id: Optional[str]
    primary: Optional[ClassificationCandidate]
    alternates: List[ClassificationCandidate] = field(default_factory=list)
    prefilled_profile: Dict[str, Any] = field(default_factory=dict)
    prefill_notes: List[str] = field(default_factory=list)
    needs_confirmation: List[str] = field(default_factory=list)
    proposal_version: str = PROPOSAL_VERSION

    @property
    def candidates(self) -> List[ClassificationCandidate]:
        return ([self.primary] if self.primary else []) + list(self.alternates)

    def candidate(self, key: str) -> Optional[ClassificationCandidate]:
        for c in self.candidates:
            if c.key == key:
                return c
        return None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

_SLUG_STOPWORDS = {"the", "a", "an", "of", "and"}


def slugify(name: str, existing: Optional[List[str]] = None) -> str:
    """Stable, readable builder_id. Deduped against existing ids."""
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    parts = [p for p in s.split("-") if p and p not in _SLUG_STOPWORDS]
    slug = "-".join(parts) or "unnamed-builder"

    existing = existing or []
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}-{n}" in existing:
        n += 1
    return f"{slug}-{n}"


def _domain_of(email: str) -> str:
    if email and "@" in email:
        return email.split("@", 1)[1].strip().lower()
    return ""


def _guess_contact_name(intake: Dict[str, Any]) -> str:
    """Best-effort contact name. Always flagged for confirmation."""
    stated = (intake.get("contact_name") or "").strip()
    if stated:
        return stated

    local = (intake.get("from_email") or "").split("@", 1)[0]
    local = re.sub(r"[0-9]+", "", local)
    parts = [p for p in re.split(r"[._\-]+", local) if p]
    if not parts:
        return ""
    return " ".join(p.capitalize() for p in parts)


def _acronym(name: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z]+", name or "") if len(w) > 1]
    if len(words) < 2:
        return ""
    return "".join(w[0].upper() for w in words)


def _pct(value: float) -> str:
    return f"{round(value * 100):g}%"


# --------------------------------------------------------------------------
# Classification scoring
# --------------------------------------------------------------------------

def _score_candidates(intake: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Score every classification candidate and record why.

    The reasoning strings are the product here as much as the scores are -
    Ryan approves a recommendation faster when he can see what drove it.
    """
    cfg = defaults["profile_proposal"]
    bc = defaults["builder_classification"]

    body = " ".join(str(intake.get(k, "")) for k in ("email_subject", "email_body"))
    domain = _domain_of(intake.get("from_email", ""))
    sqft = intake.get("conditioned_sqft")
    declared_customer_type = intake.get("customer_type") or "builder"

    scores = {c["key"]: 0 for c in cfg["classification_candidates"]}
    why: Dict[str, List[str]] = {k: [] for k in scores}

    # --- homeowner signals ---
    if declared_customer_type == "homeowner_direct":
        scores["homeowner"] += 5
        why["homeowner"].append("Intake explicitly marks this as a homeowner / direct customer.")

    if domain and domain in cfg["personal_email_domains"]:
        scores["homeowner"] += 3
        why["homeowner"].append(f"Sender is on a personal email domain ({domain}).")
        for k in ("new_custom", "new_production", "existing_missing_profile"):
            why[k].append(f"Counter-signal: personal email domain ({domain}), not a company domain.")
    elif domain:
        for k in ("new_custom", "new_production", "existing_missing_profile"):
            scores[k] += 1
        why["new_custom"].append(f"Sender is on a company domain ({domain}).")
        why["new_production"].append(f"Sender is on a company domain ({domain}).")
        why["existing_missing_profile"].append(f"Sender is on a company domain ({domain}).")

    homeowner_words = find_keywords(body, ["our new home", "our home", "my house", "my home", "we are building", "our house"])
    if homeowner_words:
        scores["homeowner"] += 2
        why["homeowner"].append(f"First-person homeowner language: {', '.join(homeowner_words)}.")

    # --- existing relationship signals ---
    rel = find_keywords(body, cfg["existing_relationship_signals"])
    if rel:
        scores["existing_missing_profile"] += 3
        why["existing_missing_profile"].append(
            f"Email implies an established relationship: {', '.join(rel)}. "
            "We may have worked with them before without a profile on file."
        )

    # --- production vs custom signals ---
    prod_hits = find_keywords(body, bc["production_signals"])
    cust_hits = find_keywords(body, bc["custom_signals"])

    if prod_hits:
        scores["new_production"] += len(prod_hits)
        why["new_production"].append(f"Production language: {', '.join(prod_hits)}.")
    if cust_hits:
        scores["new_custom"] += len(cust_hits)
        why["new_custom"].append(f"Custom language: {', '.join(cust_hits)}.")

    if isinstance(sqft, (int, float)) and sqft > 0:
        if sqft >= bc["sqft_custom_threshold"]:
            scores["new_custom"] += 1
            why["new_custom"].append(f"{int(sqft):,} sqft is at or above the {bc['sqft_custom_threshold']:,} sqft custom threshold.")
        elif sqft <= bc["sqft_production_threshold"]:
            scores["new_production"] += 1
            why["new_production"].append(f"{int(sqft):,} sqft is at or below the {bc['sqft_production_threshold']:,} sqft production threshold.")

    for key in scores:
        if not why[key]:
            why[key].append("No signals in this request point here.")

    return {k: {"score": scores[k], "reasoning": why[k]} for k in scores}


def _confidence_for(key: str, scored: Dict[str, Dict[str, Any]], defaults: Dict[str, Any]) -> str:
    """Confidence reflects separation from the runner-up, not raw score.

    A candidate scoring 4 against a 3 is a coin flip; a 4 against a 0 is not.
    """
    mine = scored[key]["score"]
    others = sorted((v["score"] for k, v in scored.items() if k != key), reverse=True)
    runner_up = others[0] if others else 0

    if mine <= 0:
        return LOW
    gap = mine - runner_up
    if mine >= 3 and gap >= 3:
        return HIGH
    if gap >= 2:
        return MEDIUM
    if gap >= 1:
        return MEDIUM if mine >= 3 else LOW
    return LOW


# --------------------------------------------------------------------------
# Building candidates
# --------------------------------------------------------------------------

def _headline_reason(reasoning: List[str]) -> str:
    """The most informative line, for the one-line alternate summary.

    The company-domain line applies to three of the four candidates, so it says
    almost nothing about why *this* one ranked where it did.
    """
    for r in reasoning:
        if not r.startswith(("Sender is on a company domain", "Counter-signal", "No signals")):
            return r
    return reasoning[0] if reasoning else ""


def _build_candidate(
    spec: Dict[str, Any],
    scored: Dict[str, Dict[str, Any]],
    defaults: Dict[str, Any],
    project_kind: str = "uncertain",
) -> ClassificationCandidate:
    key = spec["key"]
    pp = defaults["pricing_profiles"][spec["pricing_profile"]]
    margin = defaults["gross_margin"][pp["margin_key"]]

    equipment_key = spec["equipment_default"]
    builder_type = spec["builder_type"]

    # "Existing builder, profile missing" says nothing about production vs
    # custom, so take that from the same signals the decision engine uses
    # rather than hardcoding custom. Uncertain still falls to the governed
    # custom default.
    if key == "existing_missing_profile":
        if project_kind == "production":
            equipment_key = "production_default"
            builder_type = "production"
        else:
            equipment_key = "custom_default"
            builder_type = "custom"

    equipment = defaults["equipment"][equipment_key]

    return ClassificationCandidate(
        key=key,
        label=spec["label"],
        score=scored[key]["score"],
        confidence=_confidence_for(key, scored, defaults),
        reasoning=list(scored[key]["reasoning"]),
        builder_type=builder_type,
        customer_type=spec["customer_type"],
        equipment={k: v for k, v in equipment.items() if isinstance(v, str)},
        gross_margin=margin,
        gross_margin_display=_pct(margin),
        pricing_profile_key=spec["pricing_profile"],
        pricing_profile_label=pp["label"],
        pricing_profile_basis=pp["use_when"],
        labor=pp["labor"],
        burdens=pp["burdens"],
        options=[o["label"] for o in defaults["always_include"]],
    )


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def propose_profile(
    intake: Dict[str, Any],
    library: Optional[engine.BuilderLibrary] = None,
    defaults: Optional[Dict[str, Any]] = None,
) -> ProfileProposal:
    """Produce a governed Builder Profile recommendation for an intake."""
    defaults = defaults or load_defaults()
    library = library if library is not None else engine.BuilderLibrary.from_dir()
    cfg = defaults["profile_proposal"]

    builder_name = (intake.get("builder_name") or "").strip()
    domain = _domain_of(intake.get("from_email", ""))

    existing = library.match(builder_name, intake.get("from_email", ""))
    if existing:
        return ProfileProposal(
            builder_display=existing.get("display_name", builder_name),
            domain=domain,
            profile_exists=True,
            existing_profile_id=existing.get("builder_id"),
            primary=None,
        )

    scored = _score_candidates(intake, defaults)
    body = " ".join(str(intake.get(k, "")) for k in ("email_subject", "email_body"))
    project_kind = engine._classify_new_builder_project(intake, body, defaults)
    candidates = [
        _build_candidate(spec, scored, defaults, project_kind)
        for spec in cfg["classification_candidates"]
    ]

    order = cfg["tie_break_order"]
    candidates.sort(key=lambda c: (-c.score, order.index(c.key) if c.key in order else 99))

    primary, alternates = candidates[0], candidates[1:]

    proposal = ProfileProposal(
        builder_display=builder_name or "Unknown Builder",
        domain=domain,
        profile_exists=False,
        existing_profile_id=None,
        primary=primary,
        alternates=alternates,
    )
    proposal.prefilled_profile = build_profile(intake, primary, library, defaults)
    _annotate_prefill(proposal, intake, primary)
    return proposal


def build_profile(
    intake: Dict[str, Any],
    candidate: ClassificationCandidate,
    library: Optional[engine.BuilderLibrary] = None,
    defaults: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pre-populate a complete Builder Profile from what we already know.

    Everything derivable from the request is filled in. The goal is that
    approving a profile requires no typing - only correction.
    """
    defaults = defaults or load_defaults()
    library = library if library is not None else engine.BuilderLibrary.from_dir()
    overrides = overrides or {}

    builder_name = (intake.get("builder_name") or "").strip() or "Unknown Builder"
    domain = _domain_of(intake.get("from_email", ""))
    existing_ids = [p.get("builder_id", "") for p in library.profiles]

    aliases = [builder_name]
    acr = _acronym(builder_name)
    if acr:
        aliases.append(acr)
    if domain and domain not in defaults["profile_proposal"]["personal_email_domains"]:
        aliases.append(domain)

    contacts = []
    contact_name = _guess_contact_name(intake)
    if intake.get("from_email"):
        contacts.append({
            "name": contact_name,
            "role": intake.get("contact_role") or ("Homeowner" if candidate.customer_type == "homeowner_direct" else "Primary contact"),
            "email": intake.get("from_email", ""),
            "phone": intake.get("contact_phone") or "",
        })

    received = (intake.get("received_at") or "")[:10]

    profile: Dict[str, Any] = {
        "builder_id": slugify(builder_name, existing_ids),
        "display_name": builder_name,
        "status": "active",
        "builder_type": candidate.builder_type,
        "aliases": aliases,
        "contacts": contacts,
        "gross_margin": candidate.gross_margin,
        "requires_ryan_margin_approval": False,
        "equipment": dict(candidate.equipment),
        "system_count_rule": "",
        "jurisdiction": {
            "name": (intake.get("jurisdiction") or "").strip(),
            "permit_handled_by": "varies",
            "permit_allowance": "",
            "notes": "",
        },
        "manual_j_overrides": dict(intake.get("manual_j") or {}),
        "options": {"exclude": [], "exclude_reasons": {}, "additional": []},
        "standing_instructions": [],
        "attachments_expected": ["architectural plans"],
        "first_job_date": received,
        "last_reviewed": received,
        "notes": (
            f"Created from the {candidate.label} recommendation on the first request "
            f"({intake.get('project') or 'project unnamed'}). "
            f"Classification confidence: {candidate.confidence}. "
            "Equipment and margin are governed defaults, not confirmed with the builder - "
            "correct them after the first job."
        ),
    }

    # Drop the equipment block when it is only the governed default restated -
    # an empty block makes the engine fall through to the default, which keeps
    # one source of truth instead of a stale copy in every profile.
    if candidate.equipment == {
        k: v for k, v in defaults["equipment"][
            "custom_default" if candidate.builder_type in ("custom", "homeowner_direct") else "production_default"
        ].items() if isinstance(v, str)
    }:
        profile["equipment"] = {
            "system": "", "outdoor_unit": "", "indoor_unit": "", "staging": "",
            "notes": "Left blank deliberately: falls through to the governed "
                     f"{'custom' if candidate.builder_type in ('custom', 'homeowner_direct') else 'production'} default. "
                     "Fill this in only when this builder's package differs.",
        }

    profile.update(overrides)
    return profile


def _annotate_prefill(proposal: ProfileProposal, intake: Dict[str, Any], candidate: ClassificationCandidate) -> None:
    p = proposal.prefilled_profile

    proposal.prefill_notes.append(f"builder_id generated as '{p['builder_id']}'.")
    if p["aliases"]:
        proposal.prefill_notes.append(f"Aliases pre-filled: {', '.join(p['aliases'])}.")
    if p["contacts"]:
        proposal.prefill_notes.append(f"Contact captured from the sender address: {p['contacts'][0]['email']}.")
    proposal.prefill_notes.append(
        f"Gross margin set to {candidate.gross_margin_display} from the {candidate.pricing_profile_label} pricing profile."
    )
    if not p["equipment"].get("system"):
        proposal.prefill_notes.append(
            "Equipment left blank so it inherits the governed default rather than freezing a copy of it."
        )

    if p["contacts"] and p["contacts"][0]["name"]:
        proposal.needs_confirmation.append(
            f"Contact name '{p['contacts'][0]['name']}' was derived from the email address - confirm the spelling."
        )
    if not p["jurisdiction"]["name"]:
        proposal.needs_confirmation.append("Jurisdiction is unknown - permit assumptions stay LOW confidence until it is set.")
    if candidate.confidence != HIGH:
        article = "an" if candidate.label[:1].lower() in "aeiou" else "a"
        proposal.needs_confirmation.append(
            f"Classification is {candidate.confidence} confidence - confirm this is {article} {candidate.label.lower()}."
        )


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render_proposal(proposal: ProfileProposal, defaults: Optional[Dict[str, Any]] = None) -> str:
    """Plain-text recommendation block for Ryan.

    Reads as a decision to approve, not a form to fill in.
    """
    defaults = defaults or load_defaults()

    if proposal.profile_exists:
        return (
            f"Builder Profile Found: {proposal.builder_display} "
            f"({proposal.existing_profile_id})\nNo proposal needed - the profile governs this project."
        )

    L: List[str] = []
    p = proposal.primary
    L.append("BUILDER PROFILE NOT FOUND")
    L.append(f"Builder: {proposal.builder_display}" + (f"  ({proposal.domain})" if proposal.domain else ""))
    L.append("")

    L.append(f"RECOMMENDED CLASSIFICATION: {p.label}   [{p.confidence} confidence]")
    L.append("")
    L.append("Reasoning")
    for r in p.reasoning:
        L.append(f"  - {r}")
    L.append("")

    L.append("Recommended Settings")
    L.append(f"  Equipment:        {p.equipment.get('system', '')}")
    if p.equipment.get("indoor_unit"):
        L.append(f"                    Indoor: {p.equipment['indoor_unit']}")
    L.append(f"  Gross Margin:     {p.gross_margin_display}")
    L.append(f"  Pricing Profile:  {p.pricing_profile_label} - {p.pricing_profile_basis}")
    L.append(f"  Labor / Burdens:  {p.labor} / {p.burdens}")
    L.append(f"  Standard Options: all {len(p.options)} Ryan OS options")
    for o in p.options:
        L.append(f"                    - {o}")
    L.append("")

    L.append("Alternate Classifications")
    for alt in proposal.alternates:
        L.append(f"  {alt.label}  [{alt.confidence}]  margin {alt.gross_margin_display}, {alt.pricing_profile_label}")
        L.append(f"      {_headline_reason(alt.reasoning)}")
    L.append("")

    L.append("Pre-filled Builder Profile")
    for n in proposal.prefill_notes:
        L.append(f"  - {n}")
    if proposal.needs_confirmation:
        L.append("")
        L.append("  Confirm after approval:")
        for n in proposal.needs_confirmation:
            L.append(f"    - {n}")
    L.append("")

    L.append("Your options")
    L.append("  1. Approve for this project only  - use these settings now, create no profile.")
    L.append(f"  2. Create the Builder Profile     - saves profiles/{proposal.prefilled_profile['builder_id']}.json,")
    L.append("                                      and the next project from this builder is automatic.")
    L.append("  3. Override                       - pick an alternate classification, or change margin/equipment.")
    return "\n".join(L)

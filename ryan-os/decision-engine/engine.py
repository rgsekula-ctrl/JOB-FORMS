"""
Ryan OS - Bid Turnover Decision Engine
======================================

Turns an intake object (what an agent read out of an Outlook bid request) into a
governed turnover decision: equipment, margin, system count, options, permit
assumptions, a confidence table, an escalation verdict, and the internal
Load & Bid email text.

Design rules for this module:

  * Standard library only. It has to run under Codex, Claude Code, a cron job,
    the Flask app, or a bare `python3` with no install step.
  * Deterministic. Same intake in, same email out, every time, for every agent.
  * Speed first. The engine never refuses to produce an email. Even a hard
    escalation produces a complete draft - it just marks it HOLD so a human
    presses send.
  * Governed values live in defaults.json and the Builder Library, not in code.
    Code here is decision *logic*; data is data.

Human-readable contract: SPEC.md (same directory).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

__all__ = [
    "Assumption",
    "Escalation",
    "TurnoverDecision",
    "load_defaults",
    "BuilderLibrary",
    "decide",
    "render_email",
]

ENGINE_VERSION = "1.0.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
_RYAN_OS = os.path.dirname(_HERE)

DEFAULTS_PATH = os.path.join(_HERE, "defaults.json")
PROFILES_DIR = os.path.join(_RYAN_OS, "builder-library", "profiles")

# Outcomes, in increasing order of human involvement.
PROCEED = "PROCEED"
PROCEED_WITH_FLAG = "PROCEED_WITH_FLAG"
ESCALATE_TO_RYAN = "ESCALATE_TO_RYAN"

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"

# Source labels. Kept as constants so the confidence table reads the same
# no matter which agent or code path produced the row.
SRC_PROFILE = "Builder Profile"
SRC_EMAIL = "Builder email"
SRC_MECH = "Mechanical plans"
SRC_AI_PLANS = "AI plan review"
SRC_DEFAULT = "Ryan OS default"
SRC_UNCONFIRMED = "Not confirmed"


# --------------------------------------------------------------------------
# Data types
# --------------------------------------------------------------------------

@dataclass
class Assumption:
    """One governed decision, with where it came from and how sure we are."""

    field: str
    value: str
    confidence: str
    source: str
    note: str = ""

    @property
    def is_open_question(self) -> bool:
        return self.confidence == LOW


@dataclass
class Escalation:
    key: str
    reason: str
    blocking: bool = True


@dataclass
class TurnoverDecision:
    outcome: str
    builder_display: str
    builder_status: str          # existing_production | existing_custom | existing_semi_custom | new | homeowner_direct
    profile_id: Optional[str]
    project: str
    subject: str
    recipients: List[str]
    assumptions: List[Assumption] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    standing_instructions: List[str] = field(default_factory=list)
    known_unknowns: List[str] = field(default_factory=list)
    escalations: List[Escalation] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    missing_attachments: List[str] = field(default_factory=list)
    equipment_detail: Dict[str, str] = field(default_factory=dict)
    manual_j: Dict[str, List[str]] = field(default_factory=dict)
    project_classification: str = ""
    conditioned_sqft: Optional[int] = None
    stories: Optional[int] = None
    rush: bool = False
    deadline: str = ""
    engine_version: str = ENGINE_VERSION
    defaults_version: str = ""

    def get(self, field_name: str) -> Optional[Assumption]:
        for a in self.assumptions:
            if a.field == field_name:
                return a
        return None

    @property
    def blocked(self) -> bool:
        return self.outcome == ESCALATE_TO_RYAN

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Loading governed data
# --------------------------------------------------------------------------

def load_defaults(path: str = DEFAULTS_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class BuilderLibrary:
    """Loads builder profiles and matches an inbound email to one of them."""

    def __init__(self, profiles: Optional[List[Dict[str, Any]]] = None):
        self.profiles = profiles or []

    @classmethod
    def from_dir(cls, directory: str = PROFILES_DIR) -> "BuilderLibrary":
        profiles: List[Dict[str, Any]] = []
        if os.path.isdir(directory):
            for name in sorted(os.listdir(directory)):
                if not name.endswith(".json") or name.startswith("_"):
                    continue
                with open(os.path.join(directory, name), "r", encoding="utf-8") as fh:
                    profiles.append(json.load(fh))
        return cls(profiles)

    def match(self, builder_name: str = "", from_email: str = "") -> Optional[Dict[str, Any]]:
        """Match on email domain first (most reliable), then on name/alias.

        Domain beats name because superintendents type the builder name a
        dozen different ways but always send from the same domain.
        """
        domain = ""
        if from_email and "@" in from_email:
            domain = from_email.split("@", 1)[1].strip().lower()

        if domain:
            for p in self.profiles:
                for alias in p.get("aliases", []):
                    if alias.strip().lower() == domain:
                        return p

        needle = _normalize(builder_name)
        if not needle:
            return None

        for p in self.profiles:
            candidates = [p.get("display_name", ""), p.get("builder_id", "")]
            candidates += p.get("aliases", [])
            for cand in candidates:
                if _normalize(cand) == needle:
                    return p

        # Loose containment, longest alias first so "ABC Homes" beats "ABC".
        scored = []
        for p in self.profiles:
            for cand in [p.get("display_name", "")] + p.get("aliases", []):
                c = _normalize(cand)
                if len(c) >= 4 and (c in needle or needle in c):
                    scored.append((len(c), p))
        if scored:
            scored.sort(key=lambda t: t[0], reverse=True)
            return scored[0][1]
        return None


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\b(llc|inc|ltd|co|company|homes?|builders?|construction|custom)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


# --------------------------------------------------------------------------
# Text signal extraction (safety net - agents should fill intake["explicit"])
# --------------------------------------------------------------------------

_NUMBER_WORDS = {
    "one": 1, "single": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
}


def extract_system_count(text: str) -> Optional[int]:
    """Pull an explicit system count out of builder prose.

    Only matches statements that are unambiguously about system quantity.
    Returns None rather than guessing - guessing here would silently outrank
    the mechanical plans in the priority order.
    """
    if not text:
        return None
    t = text.lower()
    patterns = [
        r"\b(one|two|three|four|five|1|2|3|4|5)\s+(?:hvac\s+|ac\s+|a/c\s+)?(?:systems?|units?|zones\s+with\s+separate\s+systems?)\b",
        r"\b(?:needs?|wants?|use|install|run)\s+(one|two|three|four|five|1|2|3|4|5)\s+(?:hvac\s+)?(?:systems?|units?)\b",
        r"\b(single|1)[- ]system\b",
        r"\b(two|2)[- ]system\b",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            return _NUMBER_WORDS.get(m.group(1))
    return None


def find_keywords(text: str, keywords: List[str]) -> List[str]:
    if not text:
        return []
    t = text.lower()
    return [k for k in keywords if k.lower() in t]


def _pct(value: float) -> str:
    return f"{round(value * 100):g}%"


# --------------------------------------------------------------------------
# The decision engine
# --------------------------------------------------------------------------

def decide(
    intake: Dict[str, Any],
    library: Optional[BuilderLibrary] = None,
    defaults: Optional[Dict[str, Any]] = None,
) -> TurnoverDecision:
    """Apply the governed decision trees to one intake object."""

    defaults = defaults or load_defaults()
    library = library if library is not None else BuilderLibrary.from_dir()

    explicit = intake.get("explicit") or {}
    body = " ".join(str(x) for x in [intake.get("email_subject", ""), intake.get("email_body", "")])
    customer_type = intake.get("customer_type") or "builder"

    profile = None
    if customer_type != "homeowner_direct":
        profile = library.match(intake.get("builder_name", ""), intake.get("from_email", ""))

    builder_status = _classify_builder(profile, customer_type, intake, body, defaults)
    builder_display = (
        profile.get("display_name")
        if profile
        else (intake.get("builder_name") or "Unknown Builder").strip()
    )
    project = (intake.get("project") or "Project TBD").strip()

    decision = TurnoverDecision(
        outcome=PROCEED,
        builder_display=builder_display,
        builder_status=builder_status,
        profile_id=profile.get("builder_id") if profile else None,
        project=project,
        subject="",
        recipients=list(defaults["recipients"]["to"]),
        conditioned_sqft=intake.get("conditioned_sqft"),
        stories=intake.get("stories"),
        defaults_version=defaults.get("governed_defaults_version", ""),
    )

    _decide_equipment(decision, profile, builder_status, intake, explicit, body, defaults)
    _decide_margin(decision, profile, builder_status, explicit, defaults)
    _decide_system_count(decision, profile, intake, explicit, body, defaults)
    _decide_permit(decision, profile, intake, defaults)
    _decide_manual_j(decision, profile, intake, defaults)
    _decide_options(decision, profile, defaults)
    _decide_attachments(decision, profile, intake)
    _detect_rush(decision, intake, body, defaults)
    _check_escalations(decision, profile, builder_status, intake, explicit, body, defaults)

    decision.known_unknowns = _build_known_unknowns(decision)
    decision.outcome = _resolve_outcome(decision)
    decision.subject = _build_subject(decision, defaults)
    return decision


def _classify_builder(profile, customer_type, intake, body, defaults) -> str:
    if customer_type == "homeowner_direct":
        return "homeowner_direct"
    if profile:
        return {
            "production": "existing_production",
            "custom": "existing_custom",
            "semi-custom": "existing_semi_custom",
            "homeowner_direct": "homeowner_direct",
        }.get(profile.get("builder_type", "custom"), "existing_custom")
    return "new"


def _classify_new_builder_project(intake, body, defaults) -> str:
    """production | custom | uncertain - for builders with no profile."""
    cfg = defaults["builder_classification"]
    prod = len(find_keywords(body, cfg["production_signals"]))
    cust = len(find_keywords(body, cfg["custom_signals"]))

    sqft = intake.get("conditioned_sqft")
    if isinstance(sqft, (int, float)) and sqft > 0:
        if sqft >= cfg["sqft_custom_threshold"]:
            cust += 1
        elif sqft <= cfg["sqft_production_threshold"]:
            prod += 1

    if prod == 0 and cust == 0:
        return "uncertain"
    if prod == cust:
        return "uncertain"
    return "production" if prod > cust else "custom"


# ---- equipment ------------------------------------------------------------

def _decide_equipment(decision, profile, builder_status, intake, explicit, body, defaults) -> None:
    eq = defaults["equipment"]

    stated = (explicit.get("equipment") or "").strip()
    if stated:
        decision.assumptions.append(Assumption(
            "Equipment", stated, HIGH, SRC_EMAIL,
            "Builder specified the equipment in writing.",
        ))
        return

    if profile and (profile.get("equipment") or {}).get("system"):
        pe = profile["equipment"]
        decision.assumptions.append(Assumption(
            "Equipment", pe["system"], HIGH, SRC_PROFILE,
            pe.get("notes", ""),
        ))
        decision.equipment_detail = {k: v for k, v in pe.items() if isinstance(v, str)}
        return

    if builder_status == "existing_production":
        d = eq["production_default"]
        decision.assumptions.append(Assumption(
            "Equipment", d["system"], MEDIUM, SRC_DEFAULT,
            "Existing production builder with no standard configuration recorded. "
            "Confirm the package and add it to the Builder Profile.",
        ))
        decision.equipment_detail = dict(d)
        return

    if builder_status in ("existing_custom", "existing_semi_custom", "homeowner_direct"):
        d = eq["custom_default"]
        conf = MEDIUM if builder_status == "homeowner_direct" else HIGH
        decision.assumptions.append(Assumption(
            "Equipment", d["system"], conf, SRC_DEFAULT,
            "Ryan OS custom default.",
        ))
        decision.equipment_detail = dict(d)
        return

    # New builder - no profile. Classify the project, then apply the matching
    # default. If it cannot be classified, the custom default wins and the
    # assumption is flagged LOW so it lands under Known Unknowns.
    kind = _classify_new_builder_project(intake, body, defaults)
    decision.project_classification = kind

    if kind == "production":
        d = eq["production_default"]
        decision.assumptions.append(Assumption(
            "Equipment", d["system"], MEDIUM, SRC_DEFAULT,
            "New builder - request reads as a production project. "
            "Confirm the standard package and open a Builder Profile.",
        ))
    else:
        d = eq["custom_default"]
        if kind == "custom":
            decision.assumptions.append(Assumption(
                "Equipment", d["system"], MEDIUM, SRC_DEFAULT,
                "New builder - the request reads as a custom project.",
            ))
        else:
            decision.assumptions.append(Assumption(
                "Equipment", d["system"], LOW, SRC_DEFAULT,
                "New builder and the project could not be classified production vs "
                "custom. Ryan OS custom default applied so the load can start now.",
            ))
    decision.equipment_detail = dict(d)


# ---- margin ---------------------------------------------------------------

def _decide_margin(decision, profile, builder_status, explicit, defaults) -> None:
    gm = defaults["gross_margin"]

    if profile and profile.get("requires_ryan_margin_approval"):
        decision.assumptions.append(Assumption(
            "Gross Margin", "HOLD - Ryan approval required", LOW, SRC_PROFILE,
            "Builder Profile requires Ryan to set the margin on every job.",
        ))
        return

    stated = explicit.get("gross_margin")
    if isinstance(stated, (int, float)) and stated > 0:
        value = stated if stated <= 1 else stated / 100.0
        decision.assumptions.append(Assumption(
            "Gross Margin", _pct(value), HIGH, SRC_EMAIL,
            "Margin directed by Ryan or stated in the request.",
        ))
        return

    if profile and isinstance(profile.get("gross_margin"), (int, float)):
        decision.assumptions.append(Assumption(
            "Gross Margin", _pct(profile["gross_margin"]), HIGH, SRC_PROFILE,
            "Contracted / standing margin for this builder.",
        ))
        return

    if builder_status == "homeowner_direct":
        decision.assumptions.append(Assumption(
            "Gross Margin", _pct(gm["homeowner_direct"]), MEDIUM, SRC_DEFAULT,
            "Homeowner / one-time direct customer default.",
        ))
        return

    if builder_status == "new":
        decision.assumptions.append(Assumption(
            "Gross Margin", _pct(gm["new_builder"]), MEDIUM, SRC_DEFAULT,
            "New builder default.",
        ))
        return

    decision.assumptions.append(Assumption(
        "Gross Margin", _pct(gm["existing_builder"]), MEDIUM, SRC_DEFAULT,
        "Existing builder default - no margin recorded in the Builder Profile. "
        "Record the real number in the profile after this job.",
    ))


# ---- system count ---------------------------------------------------------

def _decide_system_count(decision, profile, intake, explicit, body, defaults) -> None:
    sc = defaults["system_count"]
    plans = intake.get("plans") or {}

    # Priority 1 - explicit builder instruction.
    stated = explicit.get("system_count")
    if not isinstance(stated, int):
        stated = extract_system_count(body)
    if isinstance(stated, int) and stated > 0:
        decision.assumptions.append(Assumption(
            "System Count", _systems(stated), HIGH, SRC_EMAIL,
            "Builder stated the system count in the request.",
        ))
        return

    # Priority 2 - mechanical plans.
    mech = intake.get("mechanical_plan_system_count")
    if plans.get("mechanical") and isinstance(mech, int) and mech > 0:
        decision.assumptions.append(Assumption(
            "System Count", _systems(mech), HIGH, SRC_MECH,
            "Taken from the mechanical / HVAC plans.",
        ))
        return

    # Priority 3 - AI recommendation from the architectural plans.
    ai = (intake.get("ai_plan_review") or {}).get("system_count")
    if plans.get("architectural") and isinstance(ai, int) and ai > 0:
        note = (intake.get("ai_plan_review") or {}).get("notes", "")
        decision.assumptions.append(Assumption(
            "System Count", _systems(ai), MEDIUM, SRC_AI_PLANS,
            note or "Recommended from an AI read of the architectural plans.",
        ))
        return

    # Priority 4 - one system per floor.
    stories = intake.get("stories")
    if isinstance(stories, int) and stories > 0:
        decision.assumptions.append(Assumption(
            "System Count", _systems(stories), MEDIUM, SRC_DEFAULT,
            "Ryan OS default - one system per floor.",
        ))
    else:
        fallback = sc["unknown_story_count_fallback"]
        decision.assumptions.append(Assumption(
            "System Count", _systems(fallback), LOW, SRC_UNCONFIRMED,
            "Story count not confirmed. Ryan OS default of one system per floor "
            f"applied against an assumed {fallback}-story home.",
        ))

    if profile and profile.get("system_count_rule"):
        decision.standing_instructions.append(
            f"Builder system-count rule: {profile['system_count_rule']}"
        )


def _systems(n: int) -> str:
    return f"{n} system" if n == 1 else f"{n} systems"


# ---- permit ---------------------------------------------------------------

def _decide_permit(decision, profile, intake, defaults) -> None:
    stated = (intake.get("jurisdiction") or "").strip()
    pj = (profile or {}).get("jurisdiction") or {}

    if pj.get("name") and pj.get("permit_handled_by") in ("WCS", "builder"):
        who = pj["permit_handled_by"]
        allowance = pj.get("permit_allowance") or "per job"
        value = f"{pj['name']} - permit pulled by {who} ({allowance})"
        decision.assumptions.append(Assumption(
            "Permit", value, HIGH, SRC_PROFILE, pj.get("notes", ""),
        ))
        return

    if stated:
        decision.assumptions.append(Assumption(
            "Permit", f"{stated} - include standard permit allowance", MEDIUM, SRC_EMAIL,
            "Jurisdiction identified from the request. Confirm fee schedule before the bid is finalized.",
        ))
        return

    decision.assumptions.append(Assumption(
        "Permit", "Include standard permit allowance", LOW, SRC_UNCONFIRMED,
        "Jurisdiction not confirmed.",
    ))


# ---- Manual J envelope ----------------------------------------------------

def _decide_manual_j(decision, profile, intake, defaults) -> None:
    mj = dict(defaults["manual_j_defaults"])
    mj.pop("note", None)
    overrides = (profile or {}).get("manual_j_overrides") or {}
    supplied = intake.get("manual_j") or {}

    resolved: Dict[str, List[str]] = {}
    for key, default_value in mj.items():
        if supplied.get(key):
            resolved[key] = [supplied[key], HIGH, SRC_EMAIL]
        elif overrides.get(key):
            resolved[key] = [overrides[key], HIGH, SRC_PROFILE]
        else:
            resolved[key] = [default_value, MEDIUM, SRC_DEFAULT]

    decision.manual_j = resolved


# ---- options --------------------------------------------------------------

def _decide_options(decision, profile, defaults) -> None:
    opts = (profile or {}).get("options") or {}
    excluded = set(opts.get("exclude") or [])
    reasons = opts.get("exclude_reasons") or {}

    for item in defaults["always_include"]:
        if item["key"] in excluded:
            reason = reasons.get(item["key"], "excluded per Builder Profile")
            decision.standing_instructions.append(
                f"{item['label']}: NOT included - {reason}"
            )
            continue
        decision.options.append(f"{item['label']}: {item['default_text']}")

    for extra in opts.get("additional") or []:
        decision.options.append(extra)

    for instruction in (profile or {}).get("standing_instructions") or []:
        decision.standing_instructions.append(instruction)


# ---- attachments ----------------------------------------------------------

def _decide_attachments(decision, profile, intake) -> None:
    decision.attachments = list(intake.get("attachments") or [])
    plans = intake.get("plans") or {}

    expected = (profile or {}).get("attachments_expected") or ["architectural plans"]
    have_text = " ".join(decision.attachments).lower()

    missing = []
    if not plans.get("architectural") and "plan" not in have_text:
        missing.append("architectural plans")
    for exp in expected:
        e = exp.lower()
        if e == "architectural plans":
            continue
        # Match on any meaningful token so "lot list" finds "Lot_list.xlsx"
        # but a short filler word like "of" or "the" never matches by accident.
        tokens = [t for t in re.split(r"[^a-z0-9]+", e) if len(t) >= 4]
        if tokens and not any(t in have_text for t in tokens):
            missing.append(exp)

    seen = set()
    decision.missing_attachments = [m for m in missing if not (m in seen or seen.add(m))]


# ---- rush -----------------------------------------------------------------

def _detect_rush(decision, intake, body, defaults) -> None:
    explicit_deadline = ((intake.get("explicit") or {}).get("deadline") or "").strip()
    hits = find_keywords(body, defaults["scope_triggers"]["rush_keywords"])
    decision.deadline = explicit_deadline
    decision.rush = bool(explicit_deadline) or bool(hits)


# ---- escalation -----------------------------------------------------------

def _check_escalations(decision, profile, builder_status, intake, explicit, body, defaults) -> None:
    # 1. Builder flagged in the library.
    if profile and profile.get("status") == "flagged":
        decision.escalations.append(Escalation(
            "builder_flagged",
            f"{profile.get('display_name')} is flagged in the Builder Library: "
            f"{profile.get('flag_reason', 'no reason recorded')}.",
        ))

    # 2. Margin requires Ryan approval.
    if profile and profile.get("requires_ryan_margin_approval"):
        decision.escalations.append(Escalation(
            "margin_approval_required",
            "Builder Profile requires Ryan to approve the gross margin before the bid is priced.",
        ))

    # 3. Out of governed scope.
    scope_hits = find_keywords(body, defaults["scope_triggers"]["out_of_scope_keywords"])
    declared = (intake.get("project_type") or "").strip().lower()
    if declared and declared not in ("new construction", "residential new construction", ""):
        scope_hits.append(declared)
    if scope_hits:
        decision.escalations.append(Escalation(
            "out_of_governed_scope",
            "Request may fall outside governed residential new-construction scope "
            f"(matched: {', '.join(sorted(set(scope_hits)))}). Governed defaults do not apply cleanly.",
        ))

    # 4. Written instruction contradicts the Builder Profile.
    if profile:
        stated_eq = (explicit.get("equipment") or "").strip()
        prof_eq = (profile.get("equipment") or {}).get("system", "")
        if stated_eq and prof_eq and not _same_equipment_family(stated_eq, prof_eq):
            decision.escalations.append(Escalation(
                "instruction_conflicts_with_profile",
                f"Builder asked for '{stated_eq}' but the Builder Profile standard is "
                f"'{prof_eq}'. Equipment substitution is a business decision.",
            ))

        stated_gm = explicit.get("gross_margin")
        prof_gm = profile.get("gross_margin")
        if isinstance(stated_gm, (int, float)) and isinstance(prof_gm, (int, float)):
            norm = stated_gm if stated_gm <= 1 else stated_gm / 100.0
            if abs(norm - prof_gm) > 0.005:
                decision.escalations.append(Escalation(
                    "instruction_conflicts_with_profile",
                    f"Requested margin {_pct(norm)} differs from the Builder Profile "
                    f"margin {_pct(prof_gm)}.",
                ))


_BRANDS = ["carrier", "lennox", "trane", "goodman", "rheem", "york", "bryant", "daikin", "amana", "american standard"]


def _same_equipment_family(a: str, b: str) -> bool:
    """Conflict detection is brand-level on purpose.

    A superintendent writing 'Carrier 16 SEER' when the profile says 'Carrier
    15.2 SEER2' is a spec detail the estimator resolves. Writing 'Trane' when
    the profile says 'Carrier' is a business decision that belongs to Ryan.
    """
    la, lb = a.lower(), b.lower()
    ba = [x for x in _BRANDS if x in la]
    bb = [x for x in _BRANDS if x in lb]
    if not ba or not bb:
        return True
    return bool(set(ba) & set(bb))


# ---- assembly -------------------------------------------------------------

def _build_known_unknowns(decision: TurnoverDecision) -> List[str]:
    out: List[str] = []
    for a in decision.assumptions:
        if a.is_open_question:
            detail = f" {a.note}" if a.note else ""
            out.append(f"{a.field}: {a.value} - LOW confidence.{detail}")
    for m in decision.missing_attachments:
        out.append(
            f"{m.capitalize()} not attached - requested from the builder. "
            "Start what you can; the load will be finalized when they arrive."
        )
    for e in decision.escalations:
        out.append(f"RYAN REVIEW: {e.reason}")
    return out


def _resolve_outcome(decision: TurnoverDecision) -> str:
    if any(e.blocking for e in decision.escalations):
        return ESCALATE_TO_RYAN
    if decision.known_unknowns:
        return PROCEED_WITH_FLAG
    return PROCEED


def _build_subject(decision: TurnoverDecision, defaults: Dict[str, Any]) -> str:
    subj = defaults["subject"]["format"].format(
        builder=decision.builder_display, project=decision.project
    )
    if decision.blocked:
        subj = defaults["subject"]["escalation_prefix"] + subj
    elif decision.rush:
        subj = defaults["subject"]["rush_prefix"] + subj
    return subj


# --------------------------------------------------------------------------
# Email rendering
# --------------------------------------------------------------------------

def render_email(decision: TurnoverDecision, defaults: Optional[Dict[str, Any]] = None) -> str:
    """Render the internal Load & Bid turnover email as plain text.

    Plain text on purpose: this gets pasted into Outlook. No markdown, no
    bullets that Outlook will mangle, no characters that break in a reply-all
    chain.
    """
    defaults = defaults or load_defaults()
    L: List[str] = []

    L.append(f"TO: {'; '.join(decision.recipients)}")
    L.append(f"SUBJECT: {decision.subject}")
    L.append("")

    if decision.blocked:
        L.append("*** HOLD - DO NOT SEND UNTIL RYAN REVIEWS THE ITEMS UNDER KNOWN UNKNOWNS ***")
        L.append("")

    opener = "Team - please complete the Manual J load and prepare an HVAC bid per the details below."
    if decision.deadline:
        opener += f" Needed by {decision.deadline}."
    elif decision.rush:
        opener += " This one is time sensitive - please start today."
    L.append(opener)
    L.append("")

    L.append(f"Project: {decision.project}")
    L.append(f"Builder: {decision.builder_display}")
    L.append("")

    L.append("Objective")
    L.append(
        "Start the Manual J now and have an HVAC bid ready for review. The assumptions "
        "below are governed Ryan OS defaults - work from them rather than waiting on "
        "open items. Flag anything that materially changes the design."
    )
    L.append("")

    mj = decision.manual_j
    L.append("Manual J Information")
    L.append(f"Builder: {decision.builder_display}")
    L.append(f"Address or Project: {decision.project}")
    for label, key in [
        ("House Direction", "house_direction"),
        ("Attic Insulation", "attic_insulation"),
        ("Walls", "walls"),
        ("Roof Type", "roof_type"),
        ("Windows", "windows"),
        ("Foundation", "foundation"),
        ("Duct Location", "duct_location"),
    ]:
        if key in mj:
            L.append(f"{label}: {mj[key][0]}")
    if decision.conditioned_sqft:
        L.append(f"Conditioned Sq Ft: {decision.conditioned_sqft:,}")
    if decision.stories:
        L.append(f"Stories: {decision.stories}")
    sc = decision.get("System Count")
    if sc:
        L.append(f"Systems: {sc.value} (source: {sc.source})")
    L.append(f"Note: {defaults['system_count']['mandatory_note']}")
    L.append("")

    L.append("Bid Prep Information")
    L.append("Rough Labor: Standard WCS labor rate")
    L.append("Burdens: Standard material and labor burdens")
    permit = decision.get("Permit")
    if permit:
        L.append(f"Permit: {permit.value}")
    if decision.deadline:
        L.append(f"Needed By: {decision.deadline}")
    L.append("")

    L.append("Equipment Assumptions")
    eq = decision.get("Equipment")
    detail = decision.equipment_detail or {}
    if eq:
        L.append(f"System: {eq.value}")
        if detail.get("outdoor_unit"):
            L.append(f"Outdoor Unit: {detail['outdoor_unit']}")
        if detail.get("indoor_unit"):
            L.append(f"Indoor Unit: {detail['indoor_unit']}")
        if detail.get("staging"):
            L.append(f"Staging: {detail['staging']}")
        L.append(f"Basis: {eq.source}")
        if eq.note:
            L.append(f"Note: {eq.note}")
    L.append("")

    L.append("Pricing Profile")
    gm = decision.get("Gross Margin")
    if gm:
        L.append(f"Gross Margin: {gm.value}")
        L.append(f"Basis: {gm.source}")
        if gm.note:
            L.append(f"Note: {gm.note}")
    L.append(f"Customer Type: {_customer_label(decision.builder_status)}")
    L.append("")

    L.append("Options Included")
    for opt in decision.options:
        L.append(f"- {opt}")
    L.append("")

    if decision.standing_instructions:
        L.append("Builder Standing Instructions")
        for s in decision.standing_instructions:
            L.append(f"- {s}")
        L.append("")

    L.append("Known Unknowns")
    if decision.known_unknowns:
        for k in decision.known_unknowns:
            L.append(f"- {k}")
    else:
        L.append("- None. All assumptions are confirmed or governed defaults.")
    L.append("")

    L.append("Assumption Confidence")
    L.append(_confidence_table(decision))
    L.append("")

    L.append("Attachments")
    if decision.attachments:
        for a in decision.attachments:
            L.append(f"- {a}")
    else:
        L.append("- None attached.")
    for m in decision.missing_attachments:
        L.append(f"- {m.capitalize()}: not received, requested from the builder.")
    L.append("")

    L.append(defaults["closing_line"])
    return "\n".join(L)


def _customer_label(status: str) -> str:
    return {
        "existing_production": "Existing production builder",
        "existing_custom": "Existing custom builder",
        "existing_semi_custom": "Existing semi-custom builder",
        "new": "New builder - no Builder Profile on file",
        "homeowner_direct": "Homeowner / one-time direct customer",
    }.get(status, status)


def _confidence_table(decision: TurnoverDecision) -> str:
    rows = [(a.field, a.confidence, a.source) for a in decision.assumptions]
    if not rows:
        return "(none)"
    w1 = max(len(r[0]) for r in rows) + 2
    w2 = max(len(r[1]) for r in rows) + 2
    return "\n".join(f"{r[0]:<{w1}}{r[1]:<{w2}}{r[2]}" for r in rows)

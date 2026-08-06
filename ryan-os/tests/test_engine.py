"""Ryan OS - Bid Turnover Decision Engine tests.

Standard-library unittest on purpose: `python3 ryan-os/tests/test_engine.py`
works on any machine with Python, with nothing installed. These tests are the
regression net for governed defaults - if someone changes a default, a test
here should fail and force them through the governance process.

Run:  python3 ryan-os/tests/test_engine.py
"""

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_RYAN_OS = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_RYAN_OS, "decision-engine"))

import engine  # noqa: E402
from engine import (  # noqa: E402
    BuilderLibrary,
    ESCALATE_TO_RYAN,
    HIGH,
    LOW,
    MEDIUM,
    PROCEED,
    PROCEED_WITH_FLAG,
    decide,
    extract_system_count,
    load_defaults,
    render_email,
)

EXAMPLES_DIR = os.path.join(_RYAN_OS, "builder-library", "examples")


def _load_example(filename: str) -> dict:
    with open(os.path.join(EXAMPLES_DIR, filename), "r", encoding="utf-8") as fh:
        return json.load(fh)


def library() -> BuilderLibrary:
    return BuilderLibrary.from_dir(EXAMPLES_DIR)


def base_intake(**overrides):
    intake = {
        "builder_name": "",
        "from_email": "",
        "project": "Lot 12 Test Ridge",
        "email_subject": "New job",
        "email_body": "Please price this one out.",
        "attachments": ["Architectural Plans.pdf"],
        "plans": {"architectural": True, "mechanical": False},
        "explicit": {},
        "customer_type": "builder",
    }
    intake.update(overrides)
    return intake


class GovernedDefaultsTest(unittest.TestCase):
    """The defaults file is a governance artifact. Pin the values."""

    def setUp(self):
        self.d = load_defaults()

    def test_margin_defaults_match_governance(self):
        gm = self.d["gross_margin"]
        self.assertEqual(gm["existing_builder"], 0.35)
        self.assertEqual(gm["new_builder"], 0.30)
        self.assertEqual(gm["homeowner_direct"], 0.35)

    def test_custom_default_is_lennox_el19kpv(self):
        c = self.d["equipment"]["custom_default"]
        self.assertIn("EL19KPV", c["system"])
        self.assertIn("variable-speed", c["indoor_unit"].lower())

    def test_production_default_is_carrier(self):
        self.assertIn("Carrier", self.d["equipment"]["production_default"]["system"])

    def test_all_required_options_present(self):
        keys = {o["key"] for o in self.d["always_include"]}
        self.assertEqual(
            keys,
            {
                "dehumidifier", "decorative_grilles", "fresh_air", "exhaust_fans",
                "permits", "standard_labor", "standard_burdens", "design_concern_flag",
            },
        )

    def test_three_recipients(self):
        to = self.d["recipients"]["to"]
        self.assertEqual(len(to), 3)
        self.assertTrue(any("estimating3@wahoocomfortsolutions.com" == r for r in to))


class BuilderMatchingTest(unittest.TestCase):
    def test_matches_on_email_domain(self):
        p = library().match("totally different name", "super@exampleproduction.com")
        self.assertIsNotNone(p)
        self.assertEqual(p["builder_id"], "example-production-homes")

    def test_matches_on_display_name(self):
        p = library().match("Example Custom Builders", "")
        self.assertEqual(p["builder_id"], "example-custom-builders")

    def test_matches_on_alias(self):
        p = library().match("EPH", "")
        self.assertEqual(p["builder_id"], "example-production-homes")

    def test_unknown_builder_returns_none(self):
        self.assertIsNone(library().match("Nobody We Know", "x@nobodyweknow.com"))

    def test_profiles_dir_missing_is_not_fatal(self):
        lib = BuilderLibrary.from_dir(os.path.join(_RYAN_OS, "does-not-exist"))
        self.assertEqual(lib.profiles, [])
        self.assertIsNone(lib.match("Anyone", ""))


class EquipmentDecisionTest(unittest.TestCase):
    def test_production_profile_uses_profile_config(self):
        d = decide(base_intake(from_email="s@exampleproduction.com"), library())
        eq = d.get("Equipment")
        self.assertEqual(eq.confidence, HIGH)
        self.assertEqual(eq.source, "Builder Profile")
        self.assertIn("Carrier", eq.value)

    def test_existing_custom_without_profile_equipment_uses_lennox(self):
        d = decide(base_intake(from_email="o@examplecustom.com"), library())
        eq = d.get("Equipment")
        self.assertIn("EL19KPV", eq.value)
        self.assertEqual(eq.confidence, HIGH)
        self.assertEqual(eq.source, "Ryan OS default")
        self.assertIn("variable-speed air handler", d.equipment_detail["indoor_unit"].lower())

    def test_new_builder_unclassifiable_gets_custom_default_flagged_low(self):
        d = decide(base_intake(builder_name="Brand New Builder"), library())
        eq = d.get("Equipment")
        self.assertIn("EL19KPV", eq.value)
        self.assertEqual(eq.confidence, LOW)
        self.assertEqual(d.project_classification, "uncertain")
        # Speed first: an unclassifiable new builder still ships the email.
        self.assertEqual(d.outcome, PROCEED_WITH_FLAG)

    def test_new_builder_production_signals_get_carrier(self):
        d = decide(
            base_intake(
                builder_name="Brand New Builder",
                email_body="Lot 14, plan #2210, elevation B in the new subdivision phase 2.",
                conditioned_sqft=2400,
            ),
            library(),
        )
        self.assertEqual(d.project_classification, "production")
        self.assertIn("Carrier", d.get("Equipment").value)

    def test_new_builder_custom_signals_get_lennox_medium(self):
        d = decide(
            base_intake(
                builder_name="Brand New Builder",
                email_body="Custom home for a homeowner, architect drawings attached.",
                conditioned_sqft=4800,
            ),
            library(),
        )
        self.assertEqual(d.project_classification, "custom")
        eq = d.get("Equipment")
        self.assertIn("EL19KPV", eq.value)
        self.assertEqual(eq.confidence, MEDIUM)

    def test_explicit_equipment_in_email_wins(self):
        d = decide(
            base_intake(
                builder_name="Brand New Builder",
                explicit={"equipment": "Carrier Infinity 20 variable speed heat pump"},
            ),
            library(),
        )
        eq = d.get("Equipment")
        self.assertEqual(eq.confidence, HIGH)
        self.assertEqual(eq.source, "Builder email")


class MarginDecisionTest(unittest.TestCase):
    def test_profile_margin_wins(self):
        d = decide(base_intake(from_email="s@exampleproduction.com"), library())
        gm = d.get("Gross Margin")
        self.assertEqual(gm.value, "20%")
        self.assertEqual(gm.confidence, HIGH)

    def test_existing_builder_without_profile_margin_gets_35(self):
        d = decide(base_intake(from_email="o@examplecustom.com"), library())
        self.assertEqual(d.get("Gross Margin").value, "35%")

    def test_new_builder_gets_30(self):
        d = decide(base_intake(builder_name="Brand New Builder"), library())
        self.assertEqual(d.get("Gross Margin").value, "30%")

    def test_homeowner_direct_gets_35(self):
        d = decide(
            base_intake(builder_name="Jane Homeowner", customer_type="homeowner_direct"),
            library(),
        )
        self.assertEqual(d.get("Gross Margin").value, "35%")
        self.assertEqual(d.builder_status, "homeowner_direct")

    def test_margin_is_never_blank(self):
        for intake in [
            base_intake(builder_name="Brand New Builder"),
            base_intake(from_email="o@examplecustom.com"),
            base_intake(builder_name="X", customer_type="homeowner_direct"),
        ]:
            gm = decide(intake, library()).get("Gross Margin")
            self.assertIsNotNone(gm)
            self.assertTrue(gm.value.strip())

    def test_explicit_margin_accepts_percent_or_decimal(self):
        a = decide(base_intake(builder_name="New Co", explicit={"gross_margin": 28}), library())
        b = decide(base_intake(builder_name="New Co", explicit={"gross_margin": 0.28}), library())
        self.assertEqual(a.get("Gross Margin").value, "28%")
        self.assertEqual(b.get("Gross Margin").value, "28%")


class SystemCountDecisionTest(unittest.TestCase):
    def test_priority_1_explicit_beats_everything(self):
        d = decide(
            base_intake(
                explicit={"system_count": 3},
                mechanical_plan_system_count=2,
                stories=1,
                plans={"architectural": True, "mechanical": True},
                ai_plan_review={"system_count": 2},
            ),
            library(),
        )
        sc = d.get("System Count")
        self.assertEqual(sc.value, "3 systems")
        self.assertEqual(sc.source, "Builder email")
        self.assertEqual(sc.confidence, HIGH)

    def test_priority_2_mechanical_plans_beat_ai_and_default(self):
        d = decide(
            base_intake(
                mechanical_plan_system_count=2,
                plans={"architectural": True, "mechanical": True},
                ai_plan_review={"system_count": 3},
                stories=1,
            ),
            library(),
        )
        sc = d.get("System Count")
        self.assertEqual(sc.value, "2 systems")
        self.assertEqual(sc.source, "Mechanical plans")

    def test_priority_3_ai_plan_review_beats_default(self):
        d = decide(
            base_intake(ai_plan_review={"system_count": 2, "notes": "Split at stair."}, stories=1),
            library(),
        )
        sc = d.get("System Count")
        self.assertEqual(sc.value, "2 systems")
        self.assertEqual(sc.source, "AI plan review")
        self.assertEqual(sc.confidence, MEDIUM)

    def test_priority_4_one_system_per_floor(self):
        d = decide(base_intake(stories=2), library())
        sc = d.get("System Count")
        self.assertEqual(sc.value, "2 systems")
        self.assertEqual(sc.confidence, MEDIUM)
        self.assertEqual(sc.source, "Ryan OS default")

    def test_unknown_stories_falls_back_to_one_and_flags_low(self):
        d = decide(base_intake(), library())
        sc = d.get("System Count")
        self.assertEqual(sc.value, "1 system")
        self.assertEqual(sc.confidence, LOW)

    def test_manual_j_caveat_always_in_email(self):
        body = render_email(decide(base_intake(stories=2), library()))
        self.assertIn("Manual J may change the final design", body)

    def test_extract_system_count_from_prose(self):
        self.assertEqual(extract_system_count("This one needs two systems."), 2)
        self.assertEqual(extract_system_count("Single system house."), 1)
        self.assertEqual(extract_system_count("3 systems please"), 3)
        self.assertIsNone(extract_system_count("No mention of quantity here."))

    def test_extract_does_not_false_positive_on_unrelated_numbers(self):
        self.assertIsNone(extract_system_count("Lot 2 in phase 3, 2400 sqft."))


class OptionsTest(unittest.TestCase):
    def test_all_eight_options_included_by_default(self):
        d = decide(base_intake(builder_name="Brand New Builder"), library())
        self.assertEqual(len(d.options), 8)
        joined = " ".join(d.options).lower()
        for token in ["dehumidifier", "grille", "fresh air", "exhaust", "permit", "labor", "burden", "design concern"]:
            self.assertIn(token, joined)

    def test_profile_can_exclude_an_option_with_a_reason(self):
        d = decide(base_intake(from_email="s@exampleproduction.com"), library())
        joined = " ".join(d.options).lower()
        self.assertNotIn("decorative grille", joined)
        self.assertTrue(any("NOT included" in s for s in d.standing_instructions))

    def test_profile_additional_options_appear(self):
        d = decide(base_intake(from_email="s@exampleproduction.com"), library())
        self.assertTrue(any("media filter" in o.lower() for o in d.options))

    def test_standing_instructions_render(self):
        body = render_email(decide(base_intake(from_email="s@exampleproduction.com"), library()))
        self.assertIn("broken out by plan number", body)


class EscalationTest(unittest.TestCase):
    def test_clean_known_builder_does_not_escalate(self):
        d = decide(
            base_intake(
                from_email="s@exampleproduction.com",
                stories=1,
                jurisdiction="Hays County",
                attachments=["Plans.pdf", "Plan number 2210", "Lot list.xlsx"],
            ),
            library(),
        )
        self.assertNotEqual(d.outcome, ESCALATE_TO_RYAN)

    def test_out_of_scope_keyword_escalates(self):
        d = decide(
            base_intake(builder_name="Someone", email_body="This is a geothermal system for the estate."),
            library(),
        )
        self.assertEqual(d.outcome, ESCALATE_TO_RYAN)
        self.assertTrue(any(e.key == "out_of_governed_scope" for e in d.escalations))

    def test_brand_conflict_with_profile_escalates(self):
        d = decide(
            base_intake(
                from_email="s@exampleproduction.com",
                explicit={"equipment": "Trane XR15"},
            ),
            library(),
        )
        self.assertEqual(d.outcome, ESCALATE_TO_RYAN)
        self.assertTrue(any(e.key == "instruction_conflicts_with_profile" for e in d.escalations))

    def test_same_brand_spec_difference_does_not_escalate(self):
        d = decide(
            base_intake(
                from_email="s@exampleproduction.com",
                explicit={"equipment": "Carrier 16 SEER2 heat pump"},
                stories=1,
            ),
            library(),
        )
        self.assertFalse(any(e.key == "instruction_conflicts_with_profile" for e in d.escalations))

    def test_flagged_builder_escalates(self):
        prof = _load_example("example-custom-builders.json")
        prof["status"] = "flagged"
        prof["flag_reason"] = "Open pricing dispute on Lot 9."
        d = decide(base_intake(from_email="o@examplecustom.com"), BuilderLibrary([prof]))
        self.assertEqual(d.outcome, ESCALATE_TO_RYAN)
        self.assertTrue(any(e.key == "builder_flagged" for e in d.escalations))

    def test_margin_approval_required_escalates_and_holds_margin(self):
        prof = _load_example("example-custom-builders.json")
        prof["requires_ryan_margin_approval"] = True
        d = decide(base_intake(from_email="o@examplecustom.com"), BuilderLibrary([prof]))
        self.assertEqual(d.outcome, ESCALATE_TO_RYAN)
        self.assertIn("HOLD", d.get("Gross Margin").value)

    def test_missing_plans_never_escalate(self):
        """Speed principle: a missing attachment is a flag, never a stop."""
        d = decide(
            base_intake(from_email="o@examplecustom.com", attachments=[], plans={}, stories=1),
            library(),
        )
        self.assertNotEqual(d.outcome, ESCALATE_TO_RYAN)
        self.assertTrue(d.missing_attachments)
        self.assertTrue(any("not attached" in k for k in d.known_unknowns))

    def test_rush_never_escalates_and_marks_subject(self):
        d = decide(
            base_intake(
                from_email="o@examplecustom.com",
                stories=1,
                email_body="Need this ASAP, going to contract tomorrow.",
            ),
            library(),
        )
        self.assertNotEqual(d.outcome, ESCALATE_TO_RYAN)
        self.assertTrue(d.rush)
        self.assertTrue(d.subject.startswith("RUSH - "))

    def test_escalation_still_produces_a_full_draft(self):
        d = decide(base_intake(builder_name="X", email_body="commercial tenant finish"), library())
        body = render_email(d)
        self.assertIn("HOLD - DO NOT SEND", body)
        self.assertIn("Manual J Information", body)
        self.assertIn("Options Included", body)
        self.assertTrue(d.subject.startswith("HOLD - RYAN REVIEW - "))


class ConfidenceTest(unittest.TestCase):
    def test_every_assumption_has_confidence_and_source(self):
        d = decide(base_intake(builder_name="Brand New Builder"), library())
        self.assertTrue(d.assumptions)
        for a in d.assumptions:
            self.assertIn(a.confidence, ("HIGH", "MEDIUM", "LOW"))
            self.assertTrue(a.source.strip())

    def test_low_confidence_items_land_in_known_unknowns(self):
        d = decide(base_intake(builder_name="Brand New Builder"), library())
        lows = [a.field for a in d.assumptions if a.confidence == LOW]
        self.assertTrue(lows)
        joined = " ".join(d.known_unknowns)
        for f in lows:
            self.assertIn(f, joined)

    def test_permit_low_when_jurisdiction_unknown(self):
        d = decide(base_intake(builder_name="Brand New Builder"), library())
        p = d.get("Permit")
        self.assertEqual(p.confidence, LOW)
        self.assertIn("Jurisdiction not confirmed", p.note)

    def test_permit_high_from_profile(self):
        d = decide(base_intake(from_email="s@exampleproduction.com"), library())
        self.assertEqual(d.get("Permit").confidence, HIGH)


class EmailRenderTest(unittest.TestCase):
    def setUp(self):
        self.d = decide(
            base_intake(from_email="o@examplecustom.com", stories=2, conditioned_sqft=4100),
            library(),
        )
        self.body = render_email(self.d)

    def test_subject_format(self):
        self.assertIn("SUBJECT: LOAD AND BID NEEDED: Example Custom Builders & Lot 12 Test Ridge", self.body)

    def test_all_required_sections_present(self):
        for section in [
            "Project:", "Builder:", "Objective", "Manual J Information",
            "Bid Prep Information", "Equipment Assumptions", "Pricing Profile",
            "Options Included", "Known Unknowns", "Assumption Confidence", "Attachments",
        ]:
            self.assertIn(section, self.body, f"missing section: {section}")

    def test_recipients_on_email(self):
        self.assertIn("estimating3@wahoocomfortsolutions.com", self.body)

    def test_closing_line(self):
        self.assertTrue(
            self.body.rstrip().endswith(
                "Please reply all when the Manual J is complete and again when the bid is complete."
            )
        )

    def test_plain_text_no_markdown(self):
        for token in ["**", "##", "```", "__"]:
            self.assertNotIn(token, self.body)

    def test_confidence_table_has_a_row_per_assumption(self):
        table_start = self.body.index("Assumption Confidence")
        table_end = self.body.index("Attachments", table_start)
        table = self.body[table_start:table_end]
        for a in self.d.assumptions:
            self.assertIn(a.field, table)
            self.assertIn(a.confidence, table)


class SerializationTest(unittest.TestCase):
    def test_decision_is_json_serializable(self):
        d = decide(base_intake(from_email="o@examplecustom.com", stories=2), library())
        blob = json.dumps(d.to_dict())
        back = json.loads(blob)
        self.assertEqual(back["builder_display"], "Example Custom Builders")
        self.assertTrue(back["assumptions"])

    def test_determinism(self):
        intake = base_intake(from_email="o@examplecustom.com", stories=2)
        a = render_email(decide(intake, library()))
        b = render_email(decide(intake, library()))
        self.assertEqual(a, b)


class ExampleIntakesTest(unittest.TestCase):
    """Every shipped example intake must run clean through the engine."""

    def test_all_examples_render(self):
        ex_dir = os.path.join(_RYAN_OS, "cli", "examples")
        files = [f for f in sorted(os.listdir(ex_dir)) if f.endswith(".json")]
        self.assertTrue(files, "no example intakes shipped")
        for name in files:
            with self.subTest(example=name):
                with open(os.path.join(ex_dir, name), "r", encoding="utf-8") as fh:
                    intake = json.load(fh)
                d = decide(intake, library())
                body = render_email(d)
                self.assertIn("LOAD AND BID NEEDED", body)
                self.assertIn(d.outcome, (PROCEED, PROCEED_WITH_FLAG, ESCALATE_TO_RYAN))


if __name__ == "__main__":
    unittest.main(verbosity=2)

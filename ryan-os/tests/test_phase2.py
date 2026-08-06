"""Ryan OS Phase 2 tests - Builder Profile Proposals and the Asset Registry.

Standard-library unittest, no install required.

Run:  python3 ryan-os/tests/test_phase2.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_RYAN_OS = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_RYAN_OS, "decision-engine"))
sys.path.insert(0, os.path.join(_RYAN_OS, "asset-registry"))
sys.path.insert(0, os.path.join(_RYAN_OS, "cli"))

import engine  # noqa: E402
import profile_proposal  # noqa: E402
from profile_proposal import (  # noqa: E402
    build_profile,
    propose_profile,
    render_proposal,
    slugify,
)
from registry import (  # noqa: E402
    AUTHORITATIVE,
    FOUND,
    FOUND_CANDIDATE,
    GAP,
    GAP_FLAGGED,
    NOT_REGISTERED,
    AssetRegistry,
)

EXAMPLES_DIR = os.path.join(_RYAN_OS, "builder-library", "examples")
HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"


def library():
    return engine.BuilderLibrary.from_dir(EXAMPLES_DIR)


def intake(**overrides):
    base = {
        "builder_name": "Ridgeline Development Group",
        "from_email": "mike@ridgelinedev.com",
        "project": "Lot 7 Barton Creek",
        "email_subject": "HVAC pricing",
        "email_body": "We have a house coming up and need a number.",
        "customer_type": "builder",
        "received_at": "2026-08-06T09:00:00",
    }
    base.update(overrides)
    return base


# ==========================================================================
# Builder Profile Proposals
# ==========================================================================

class ProposalBasicsTest(unittest.TestCase):
    def test_known_builder_produces_no_proposal(self):
        p = propose_profile(intake(builder_name="EPH", from_email="s@exampleproduction.com"), library())
        self.assertTrue(p.profile_exists)
        self.assertEqual(p.existing_profile_id, "example-production-homes")
        self.assertIsNone(p.primary)
        self.assertIn("Profile Found", render_proposal(p))

    def test_unknown_builder_always_gets_a_recommendation(self):
        """The core Phase 2 requirement: a decision, never an open question."""
        p = propose_profile(intake(), library())
        self.assertFalse(p.profile_exists)
        self.assertIsNotNone(p.primary)
        self.assertTrue(p.primary.equipment.get("system"))
        self.assertGreater(p.primary.gross_margin, 0)
        self.assertTrue(p.primary.pricing_profile_label)
        self.assertEqual(len(p.primary.options), 8)

    def test_all_four_classifications_offered(self):
        p = propose_profile(intake(), library())
        keys = {c.key for c in p.candidates}
        self.assertEqual(
            keys,
            {"new_custom", "new_production", "homeowner", "existing_missing_profile"},
        )

    def test_every_candidate_has_reasoning_and_confidence(self):
        p = propose_profile(intake(), library())
        for c in p.candidates:
            self.assertTrue(c.reasoning, f"{c.key} has no reasoning")
            self.assertIn(c.confidence, (HIGH, MEDIUM, LOW))
            self.assertTrue(c.gross_margin_display)

    def test_proposal_is_json_serializable(self):
        p = propose_profile(intake(), library())
        back = json.loads(json.dumps(p.to_dict()))
        self.assertEqual(back["primary"]["key"], p.primary.key)

    def test_rendered_proposal_offers_the_three_choices(self):
        text = render_proposal(propose_profile(intake(), library()))
        self.assertIn("Approve for this project only", text)
        self.assertIn("Create the Builder Profile", text)
        self.assertIn("Override", text)
        self.assertIn("BUILDER PROFILE NOT FOUND", text)


class ClassificationTest(unittest.TestCase):
    def test_homeowner_detected_from_personal_domain_and_language(self):
        p = propose_profile(
            intake(
                builder_name="Sarah Whitfield",
                from_email="swhitfield@gmail.com",
                customer_type="homeowner_direct",
                email_body="We are building our new home on Oak Hollow.",
            ),
            library(),
        )
        self.assertEqual(p.primary.key, "homeowner")
        self.assertEqual(p.primary.confidence, HIGH)
        self.assertEqual(p.primary.gross_margin, 0.35)

    def test_production_signals_pick_new_production(self):
        p = propose_profile(
            intake(email_body="Lot 14, plan #2210, elevation B, phase 2 subdivision.", conditioned_sqft=2400),
            library(),
        )
        self.assertEqual(p.primary.key, "new_production")
        self.assertIn("Carrier", p.primary.equipment["system"])

    def test_custom_signals_pick_new_custom(self):
        p = propose_profile(
            intake(email_body="Custom home, architect set attached, one-off design.", conditioned_sqft=5200),
            library(),
        )
        self.assertEqual(p.primary.key, "new_custom")
        self.assertIn("EL19KPV", p.primary.equipment["system"])

    def test_existing_relationship_language_detected(self):
        p = propose_profile(
            intake(email_body="Another one for you - same package as last time."),
            library(),
        )
        self.assertEqual(p.primary.key, "existing_missing_profile")
        self.assertEqual(p.primary.gross_margin, 0.35)

    def test_existing_missing_profile_respects_production_evidence(self):
        """The candidate must not hardcode custom equipment."""
        p = propose_profile(
            intake(
                email_body="Another one for you, same as last time. Plan 1420 elevation A.",
                conditioned_sqft=2600,
            ),
            library(),
        )
        self.assertEqual(p.primary.key, "existing_missing_profile")
        self.assertIn("Carrier", p.primary.equipment["system"])
        self.assertEqual(p.primary.builder_type, "production")

    def test_no_signals_still_yields_a_ranked_recommendation(self):
        p = propose_profile(intake(email_body="", email_subject="", from_email=""), library())
        self.assertIsNotNone(p.primary)
        self.assertEqual(p.primary.confidence, LOW)

    def test_confidence_reflects_separation_not_raw_score(self):
        strong = propose_profile(
            intake(from_email="s@gmail.com", customer_type="homeowner_direct",
                   email_body="our new home"),
            library(),
        )
        weak = propose_profile(intake(email_body="need a price"), library())
        self.assertEqual(strong.primary.confidence, HIGH)
        self.assertEqual(weak.primary.confidence, LOW)


class PrefillTest(unittest.TestCase):
    def setUp(self):
        self.p = propose_profile(intake(), library())
        self.prof = self.p.prefilled_profile

    def test_slug_generated_from_name(self):
        self.assertEqual(self.prof["builder_id"], "ridgeline-development-group")

    def test_slug_dedupes(self):
        self.assertEqual(slugify("Acme Homes", ["acme-homes"]), "acme-homes-2")
        self.assertEqual(slugify("Acme Homes", ["acme-homes", "acme-homes-2"]), "acme-homes-3")
        self.assertEqual(slugify("!!!"), "unnamed-builder")

    def test_aliases_include_name_acronym_and_domain(self):
        self.assertIn("Ridgeline Development Group", self.prof["aliases"])
        self.assertIn("RDG", self.prof["aliases"])
        self.assertIn("ridgelinedev.com", self.prof["aliases"])

    def test_contact_captured_from_sender(self):
        c = self.prof["contacts"][0]
        self.assertEqual(c["email"], "mike@ridgelinedev.com")
        self.assertEqual(c["name"], "Mike")

    def test_derived_contact_name_is_flagged_for_confirmation(self):
        self.assertTrue(any("confirm the spelling" in n for n in self.p.needs_confirmation))

    def test_personal_domain_not_added_as_alias(self):
        p = propose_profile(
            intake(builder_name="Sarah Whitfield", from_email="s@gmail.com",
                   customer_type="homeowner_direct"),
            library(),
        )
        self.assertNotIn("gmail.com", p.prefilled_profile["aliases"])

    def test_equipment_left_blank_to_inherit_governed_default(self):
        """Freezing a copy of the default into every profile creates drift."""
        self.assertEqual(self.prof["equipment"]["system"], "")
        self.assertIn("falls through", self.prof["equipment"]["notes"])

    def test_margin_prefilled_from_pricing_profile(self):
        self.assertEqual(self.prof["gross_margin"], 0.30)

    def test_jurisdiction_carried_through_when_known(self):
        p = propose_profile(intake(jurisdiction="Hays County"), library())
        self.assertEqual(p.prefilled_profile["jurisdiction"]["name"], "Hays County")

    def test_unknown_jurisdiction_flagged(self):
        self.assertTrue(any("Jurisdiction is unknown" in n for n in self.p.needs_confirmation))

    def test_dates_prefilled_from_received_at(self):
        self.assertEqual(self.prof["first_job_date"], "2026-08-06")
        self.assertEqual(self.prof["last_reviewed"], "2026-08-06")

    def test_overrides_applied(self):
        p = propose_profile(intake(), library())
        prof = build_profile(intake(), p.primary, library(), overrides={"gross_margin": 0.32})
        self.assertEqual(prof["gross_margin"], 0.32)


class ProfileRoundTripTest(unittest.TestCase):
    """The Phase 2 promise: approving a profile makes the next job automatic."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, prof):
        with open(os.path.join(self.tmp, f"{prof['builder_id']}.json"), "w", encoding="utf-8") as fh:
            json.dump(prof, fh, indent=2)

    def test_created_profile_upgrades_the_next_decision(self):
        job = intake(stories=1, attachments=["Plans.pdf"], plans={"architectural": True})

        before = engine.decide(job, engine.BuilderLibrary([]))
        self.assertEqual(before.get("Gross Margin").source, "Ryan OS default")
        self.assertIsNone(before.profile_id)

        proposal = propose_profile(job, engine.BuilderLibrary([]))
        self._write(proposal.prefilled_profile)

        after = engine.decide(job, engine.BuilderLibrary.from_dir(self.tmp))
        self.assertEqual(after.get("Gross Margin").source, "Builder Profile")
        self.assertEqual(after.get("Gross Margin").confidence, HIGH)
        self.assertEqual(after.profile_id, "ridgeline-development-group")

    def test_created_profile_matches_a_shortened_name_next_time(self):
        proposal = propose_profile(intake(), engine.BuilderLibrary([]))
        self._write(proposal.prefilled_profile)

        lib = engine.BuilderLibrary.from_dir(self.tmp)
        self.assertIsNotNone(lib.match("Ridgeline", "mike@ridgelinedev.com"))
        self.assertIsNotNone(lib.match("", "someone.else@ridgelinedev.com"))

    def test_generated_profile_passes_schema_validation(self):
        import profile as profile_cli

        with open(os.path.join(_RYAN_OS, "builder-library", "schema",
                               "builder_profile.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)

        for body in ["custom home architect", "plan 2210 elevation lot", "our new home"]:
            p = propose_profile(intake(email_body=body), library())
            errors = profile_cli.validate_profile(p.prefilled_profile, schema)
            self.assertEqual(errors, [], f"validation failed for '{body}': {errors}")


# ==========================================================================
# Asset Registry
# ==========================================================================

class RegistryIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.reg = AssetRegistry.load()

    def test_registry_validates_clean(self):
        self.assertEqual(self.reg.validate(), [])

    def test_registry_is_not_empty(self):
        self.assertGreater(len(self.reg.assets), 10)

    def test_every_asset_answers_the_five_questions(self):
        for a in self.reg.assets:
            self.assertTrue(a.what_it_is, f"{a.asset_id}: what")
            self.assertTrue(a.where_it_is.get("kind"), f"{a.asset_id}: where")
            self.assertTrue(a.owner, f"{a.asset_id}: owner")
            self.assertTrue(a.use_when, f"{a.asset_id}: use_when")
            # "what does it replace" is answered by replaces/replaced_by, which
            # are legitimately empty for an original asset - the schema allows it.

    def test_gaps_all_carry_a_recommendation(self):
        gaps = self.reg.gaps()
        self.assertTrue(gaps)
        for a in gaps:
            self.assertTrue(a.gap_recommendation, f"{a.asset_id} has no recommendation")

    def test_deprecated_assets_name_a_successor(self):
        for a in self.reg.by_status("deprecated"):
            self.assertTrue(a.replaced_by, f"{a.asset_id} is deprecated with no successor")
            self.assertIsNotNone(self.reg.get(a.replaced_by))

    def test_core_assets_registered(self):
        for asset_id in ["woods-forms-app", "bid-turnover-engine", "governed-defaults",
                         "builder-library", "asset-registry", "pricing-workbook"]:
            self.assertIsNotNone(self.reg.get(asset_id), f"missing {asset_id}")

    def test_registry_registers_itself(self):
        me = self.reg.get("asset-registry")
        self.assertEqual(me.status, AUTHORITATIVE)


class RegistryResolveTest(unittest.TestCase):
    def setUp(self):
        self.reg = AssetRegistry.load()

    def test_authoritative_hit_says_use_it(self):
        r = self.reg.resolve("proposal template")
        self.assertEqual(r.outcome, FOUND)
        self.assertTrue(r.usable)
        self.assertEqual(r.asset.asset_id, "quickbid-proposal")

    def test_known_gap_is_flagged_not_substituted(self):
        r = self.reg.resolve("pricing workbook")
        self.assertEqual(r.outcome, GAP_FLAGGED)
        self.assertFalse(r.usable)
        self.assertIn("Do NOT substitute", r.action_required)

    def test_unregistered_never_returns_a_silent_match(self):
        r = self.reg.resolve("truck inventory spreadsheet")
        self.assertEqual(r.outcome, NOT_REGISTERED)
        self.assertIsNone(r.asset)
        self.assertIn("Do NOT search elsewhere", r.action_required)

    def test_prose_only_match_is_not_authority(self):
        """Regression: a query word appearing once in a description must not
        promote an unrelated asset to AUTHORITATIVE.

        'spreadsheet' appears in the equipment-schedule description but in no
        asset's keywords, so it is prose-only evidence and must not match.
        """
        schedule = self.reg.get("hvac-equipment-schedule-template")
        self.assertIn("spreadsheet", schedule.what_it_is.lower())
        self.assertNotIn("spreadsheet", " ".join(schedule.keywords).lower())

        self.assertEqual(self.reg.search("spreadsheet"), [])
        self.assertEqual(self.reg.resolve("truck inventory spreadsheet").outcome, NOT_REGISTERED)

    def test_deprecated_query_redirects_to_successor(self):
        r = self.reg.resolve("wcs bid request")
        self.assertEqual(r.outcome, FOUND)
        self.assertEqual(r.asset.asset_id, "bid-turnover-engine")
        self.assertIn("deprecated", r.message)

    def test_candidate_is_usable_but_labelled(self):
        r = self.reg.resolve("portable grille")
        self.assertEqual(r.outcome, FOUND_CANDIDATE)
        self.assertTrue(r.usable)
        self.assertIn("CANDIDATE", r.message)

    def test_resolve_always_gives_an_action(self):
        for q in ["pricing", "form", "nonsense query xyz", "grille", "outlook"]:
            r = self.reg.resolve(q)
            self.assertTrue(r.action_required, f"no action for '{q}'")

    def test_resolution_is_json_serializable(self):
        back = json.loads(json.dumps(self.reg.resolve("grille order").to_dict()))
        self.assertIn("outcome", back)
        self.assertIn("usable", back)


class RegistrySearchTest(unittest.TestCase):
    def setUp(self):
        self.reg = AssetRegistry.load()

    def test_search_by_keyword(self):
        ids = [a.asset_id for a in self.reg.search("manual j")]
        self.assertIn("form-load-calc-request", ids)

    def test_search_by_exact_id(self):
        self.assertEqual(self.reg.search("quickbid-proposal")[0].asset_id, "quickbid-proposal")

    def test_search_empty_query_returns_nothing(self):
        self.assertEqual(self.reg.search(""), [])

    def test_authoritative_outranks_deprecated_on_equal_relevance(self):
        results = self.reg.search("bid")
        statuses = [a.status for a in results[:3]]
        self.assertIn("authoritative", statuses)

    def test_by_category_and_gaps(self):
        self.assertTrue(self.reg.by_category("form"))
        self.assertTrue(all(a.status == GAP for a in self.reg.gaps()))

    def test_categories_listed(self):
        cats = self.reg.categories()
        self.assertIn("form", cats)
        self.assertIn("pricing-workbook", cats)


if __name__ == "__main__":
    unittest.main(verbosity=2)

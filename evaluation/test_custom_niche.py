"""End-to-end test: create a custom niche outside the 3 pre-built ones.
Uses the LLM-powered draft generation, then saves the reviewed result.

Usage:
    python -m evaluation.test_custom_niche
"""

import sys
import json
import random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.niche_generator import generate_niche_draft
from backend.niche_manager import save_niche_draft, get_niche_config, get_available_niches, NICHES_DIR


# Sample posts for a niche that is NOT gps-telematics, b2b-saas, or fintech
# These are healthcare / health-tech related posts
HEALTHTECH_POSTS = [
    "Our telemedicine platform reduced no-show rates by 40% with automated reminders",
    "HIPAA-compliant video consultations are now the standard for behavioral health",
    "How we integrated EHR data with our patient engagement app",
    "The ROI of AI-powered diagnostic triage in emergency departments",
    "Patient portal adoption doubled after we added mobile biometric authentication",
    "Interoperability challenges between legacy hospital systems and modern APIs",
    "Value-based care models require real-time population health analytics",
    "Clinical decision support systems reduce diagnostic errors by 35% in primary care",
    "Wearable device data integration is changing chronic disease management",
    "Revenue cycle management automation saved our practice $200K annually",
    "Remote patient monitoring for hypertension improved outcomes by 28%",
    "The role of FHIR APIs in modern healthcare data exchange",
    "AI scribes are cutting physician documentation time by 50%",
    "Patient satisfaction scores improved with automated follow-up messaging",
    "Cloud-based PACS systems are replacing on-premise radiology storage",
    "Prior authorization automation reduced processing time from days to hours",
    "Virtual nursing programs help address staffing shortages in acute care",
    "Healthcare chatbot triage reduced ED visits for non-urgent cases by 22%",
    "Claims denial management AI recovered 15% more revenue for hospitals",
    "Digital therapeutics are gaining FDA clearance for mental health treatment",
    "Population health stratification identifies high-risk patients before crises",
    "Real-world evidence platforms are accelerating clinical trial recruitment",
    "Medication adherence tracking through smart pill bottles and mobile apps",
    "Telehealth reimbursement policies are driving virtual care expansion",
    "Healthcare cybersecurity threats increased 45% — how hospitals are responding",
]

NICHE_ID = "healthtech-digital-health"
DISPLAY_NAME = "HealthTech & Digital Health"


def main():
    # Clean up any previous test run
    niche_dir = NICHES_DIR / NICHE_ID
    if niche_dir.exists():
        print(f"Cleaning up previous test niche at {niche_dir}")
        import shutil
        shutil.rmtree(niche_dir)

    print("=" * 70)
    print(f"Test: Create custom niche '{DISPLAY_NAME}'")
    print(f"Sample posts: {len(HEALTHTECH_POSTS)}")
    print("=" * 70)

    print("\nStep 1: Generate draft via LLM...")
    draft = generate_niche_draft(NICHE_ID, DISPLAY_NAME, HEALTHTECH_POSTS)

    fallback = draft.get("_fallback")
    if fallback:
        print(f"  LLM fallback triggered: {fallback[:80]}...")
        print("  Using heuristic-generated draft instead")
    else:
        print("  LLM draft generated successfully")
        print(f"  Corpus entries: {len(draft.get('corpus', []))}")
        print(f"  Jargon categories: {list(draft.get('jargon', {}).keys())}")
        print(f"  Sample topics: {draft.get('sample_topics', [])}")
        print(f"  Description: {draft.get('description', 'N/A')}")

    description = draft.get("description", f"Auto-generated niche for {DISPLAY_NAME}")
    corpus = draft.get("corpus", HEALTHTECH_POSTS[:60])
    jargon = draft.get("jargon", {})
    sample_topics = draft.get("sample_topics", HEALTHTECH_POSTS[:5])

    # Simulate user review: we accept the draft as-is for this automated test
    print("\nStep 2: Saving reviewed draft (simulated user approval)...")
    config = save_niche_draft(
        niche_id=NICHE_ID,
        display_name=DISPLAY_NAME,
        description=description,
        sample_posts=HEALTHTECH_POSTS,
        corpus=corpus,
        jargon=jargon,
        sample_topics=sample_topics,
    )
    print(f"  Config saved: {config['niche_id']}")

    print("\nStep 3: Verify niche is available...")
    niches = get_available_niches()
    found = [n for n in niches if n["niche_id"] == NICHE_ID]
    if found:
        print(f"  [OK] Niche '{NICHE_ID}' found in available niches list")
        print(f"     Display name: {found[0]['display_name']}")
        print(f"     Description: {found[0]['description']}")
    else:
        print(f"  [FAIL] Niche '{NICHE_ID}' NOT found in available niches")
        sys.exit(1)

    print("\nStep 4: Load niche files from disk...")
    config_file = niche_dir / "config.json"
    corpus_file = niche_dir / "seed_corpus.json"
    jargon_file = niche_dir / "jargon_expansion.json"

    assert config_file.exists(), f"Missing {config_file}"
    assert corpus_file.exists(), f"Missing {corpus_file}"
    assert jargon_file.exists(), f"Missing {jargon_file}"

    corpus_loaded = json.loads(corpus_file.read_text())
    jargon_loaded = json.loads(jargon_file.read_text())

    print(f"  config.json: [OK] ({config_file.stat().st_size} bytes)")
    print(f"  seed_corpus.json: [OK] ({len(corpus_loaded)} entries, {corpus_file.stat().st_size} bytes)")
    print(f"  jargon_expansion.json: [OK] ({len(jargon_loaded)} keys, {jargon_file.stat().st_size} bytes)")

    if jargon_loaded.get("industry_terms"):
        categories = list(jargon_loaded["industry_terms"].keys())
        total_terms = sum(len(v) for v in jargon_loaded["industry_terms"].values())
        print(f"     Industry terms: {total_terms} across {len(categories)} categories: {categories}")

    print("\n" + "=" * 70)
    print("RESULT: CUSTOM NICHE CREATED SUCCESSFULLY")
    print(f"  Niche: {NICHE_ID}")
    print(f"  Type: {'LLM-generated' if not fallback else 'Heuristic fallback'}")
    print(f"  Corpus size: {len(corpus)}")
    print(f"  Jargon categories: {list(jargon.keys())}")
    print("=" * 70)


if __name__ == "__main__":
    main()

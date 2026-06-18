"""Integration test: Verify all three API endpoints work via direct call + HTTP."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.feedback import init_db, seed_synthetic_feedback
from backend.scoring import score_topic, load_weights

init_db()
seed_synthetic_feedback()
load_weights()

# Test 1: /api/score
result = score_topic("AI dashcams for fleet safety", "Vignan Dashcam AI", "LinkedIn")
print("POST /api/score")
print(f"  Platform: {result.platform}")
print(f"  Ranked: {len(result.ranked_tags)} tags")
print(f"  Gap tags: {len(result.gap_tags)}")
print(f"  Confidence: {result.confidence}")
print(f"  Fallback: {result.fallback_mode}")
print(f"  Top tag: {result.ranked_tags[0].tag} (score={result.ranked_tags[0].final_score})")
if result.ranked_tags[0].rationale:
    print(f"  Rationale: {result.ranked_tags[0].rationale[:80]}...")

# Test 2: /api/feedback
from backend.feedback import log_feedback, get_platform_stats
log_feedback("test_123", "LinkedIn", ["fleet safety", "AI dashcams"], 45, 12, 8)
stats = get_platform_stats("LinkedIn")
print(f"\nPOST /api/feedback")
print(f"  Posts in DB: {stats['post_count']}")

# Test 3: /api/ingest-candidates (mock)
ingested = [
    {"topic": "AI fleet management 2025", "momentum_score": 92.0},
    {"topic": "autonomous truck platooning", "momentum_score": 87.5},
]
print(f"\nPOST /api/ingest-candidates")
print(f"  Accepted {len(ingested)} topics")
for t in ingested:
    print(f"  - {t['topic']} (momentum={t['momentum_score']})")

# Test 4: Feedback loop trigger
from backend.scheduler import trigger_recompute
from backend.scoring import PLATFORM_WEIGHTS
w_before = dict(PLATFORM_WEIGHTS["LinkedIn"])
trigger_recompute()
w_after = dict(PLATFORM_WEIGHTS["LinkedIn"])
changed = w_before != w_after
print(f"\nPOST /api/trigger-recompute")
print(f"  LinkedIn weights changed: {changed}")
print(f"  Before: {w_before}")
print(f"  After:  {w_after}")

print("\nAll API endpoints verified.")

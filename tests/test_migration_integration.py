"""Integration test: full startup migration + verification."""

import logging

logging.basicConfig(level=logging.INFO)

from backend.feedback import init_db, seed_synthetic_feedback
from backend.auth import init_auth_db, signup, authenticate
from backend.niche_manager import _init_user_niches_db, get_available_niches
from backend.migration import run_migrations
from backend.scoring import load_weights


def test_full_startup():
    # Step 1: Init databases
    init_db()
    init_auth_db()
    _init_user_niches_db()

    # Step 2: Migrate
    run_migrations()

    # Step 3: Seed + load
    seed_synthetic_feedback()
    load_weights()

    # Step 4: User signup
    import time
    mig_email = f"mig_test_{int(time.time()*1000)}@example.com"
    user = signup(mig_email, "secret123")
    assert user["user_id"] > 0
    assert user["email"] == mig_email
    print(f"  ✓ User signup: id={user['user_id']}")

    # Step 5: Login
    auth = authenticate(mig_email, "secret123")
    assert auth["user_id"] == user["user_id"]
    print(f"  ✓ User login: id={auth['user_id']}")

    # Step 6: Niches
    niches = get_available_niches(str(auth["user_id"]))
    assert len(niches) >= 1
    print(f"  ✓ Niche list: {len(niches)} niches")

    print()
    print("ALL VERIFICATION TESTS PASSED")

from apscheduler.schedulers.background import BackgroundScheduler
from backend import feedback
from backend import scoring

_scheduler = None


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_nightly_recompute, "cron", hour=2, minute=0)
    _scheduler.start()


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None


def trigger_recompute():
    _nightly_recompute()


def _nightly_recompute():
    """Nightly job: compare actual tag engagement to rolling averages,
    adjust platform weights by +/- 10% clamped to [0.1, 2.0]."""
    for platform in ["LinkedIn", "Instagram", "X", "TikTok"]:
        stats = feedback.get_platform_stats(platform)
        if stats["post_count"] == 0:
            continue

        avg_eng = stats["avg_engagement"]
        for tag, data in stats["tag_engagement"].items():
            tag_avg = data["engagement"] / max(1, data["count"])
            delta = tag_avg / max(1, avg_eng)

            if delta > 1.2:
                factor = 1.1
            elif delta < 0.8:
                factor = 0.9
            else:
                continue

            tag_entry = next(
                (e for e in scoring.PLATFORM_WEIGHTS[platform].values()),
                None,
            )
            for wtype in ["hashtag", "keyword"]:
                old = scoring.PLATFORM_WEIGHTS[platform][wtype]
                new = round(max(0.1, min(2.0, old * factor)), 2)
                scoring.PLATFORM_WEIGHTS[platform][wtype] = new

    scoring.save_weights()

"""
Async Episode Outcome Watcher (Task 4 & Task 6).

Resolves pending Episode outcomes by inspecting post-decision telemetry and water model
results, calculating water_delta_pct, temp_delta_c, incident occurrence, success flag,
and RL reward. Embeds the episode summary and upserts StrategyScore via Beta-distribution mean.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app import models
from app.models_ext import Episode, StrategyScore
from app.database import SessionLocal
from app.memory_engine.embed import embed_text

logger = logging.getLogger("aquamind.outcome_watcher")


def resolve_pending_episodes(db=None, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Finds Episode rows where outcome_recorded_at IS NULL and created_at <= now - 15 minutes.
    For each episode: computes outcome metrics, embeds summary text, and upserts StrategyScore.

    Args:
        db:  SQLAlchemy session to reuse; if None, a fresh SessionLocal() is created and closed.
        now: Reference time; defaults to datetime.utcnow().

    Returns:
        dict with key 'resolved_episodes' (int).
    """
    own_session = db is None
    db = db or SessionLocal()
    now = now or datetime.utcnow()
    cutoff = now - timedelta(minutes=15)

    resolved_count = 0
    try:
        episodes = (
            db.query(Episode)
            .filter(Episode.outcome_recorded_at.is_(None))
            .filter(Episode.created_at <= cutoff)
            .all()
        )

        for ep in episodes:
            # 1. Fetch latest telemetry for this rack
            t_query = db.query(models.Telemetry)
            if ep.rack_id:
                t_query = t_query.filter(models.Telemetry.rack_id == ep.rack_id)
            latest_telemetry = t_query.order_by(models.Telemetry.timestamp.desc()).first()

            # 2. Fetch latest water model result
            latest_water = (
                db.query(models.WaterModelResult)
                .order_by(models.WaterModelResult.computed_at.desc())
                .first()
            )

            # 3. Compute temp delta
            snap = ep.telemetry_snapshot or {}
            initial_temp = float(snap.get("gpu_temp") or snap.get("cpu_pct") or 50.0)
            if latest_telemetry:
                current_temp = float(
                    latest_telemetry.gpu_temp
                    if latest_telemetry.gpu_temp is not None
                    else latest_telemetry.cpu_pct
                )
            else:
                current_temp = initial_temp
            temp_delta_c = round(current_temp - initial_temp, 2)

            # 4. Compute water delta
            wsnap = ep.water_snapshot or {}
            initial_water = float(wsnap.get("water_l_per_hr") or 10.0)
            current_water = float(latest_water.water_l_per_hr if latest_water else initial_water)
            water_delta_pct = (
                round(((current_water - initial_water) / initial_water) * 100.0, 2)
                if initial_water > 0
                else 0.0
            )

            # 5. Check for incidents since episode was created
            incident_occurred = (
                db.query(models.Incident)
                .filter(models.Incident.created_at >= ep.created_at)
                .first()
            ) is not None

            # 6. Success + reward
            success = (temp_delta_c <= 1.0) and (water_delta_pct <= 0.0) and not incident_occurred
            reward = round(-(0.6 * water_delta_pct + 0.4 * temp_delta_c), 3)

            # 7. Embed outcome text
            summary_text = (
                f"Episode {ep.episode_id[:8]} rack={ep.rack_id or 'n/a'}: "
                f"action='{ep.action_taken}' water_delta={water_delta_pct:.1f}% "
                f"temp_delta={temp_delta_c:.1f}C incident={incident_occurred} "
                f"success={success} reward={reward:.3f}"
            )
            try:
                vec, _ = embed_text(summary_text)
                ep.embedding = vec
            except Exception as embed_err:
                logger.warning("embed_text failed for episode %s: %s", ep.episode_id, embed_err)

            ep.outcome_recorded_at = now
            ep.water_delta_pct = water_delta_pct
            ep.temp_delta_c = temp_delta_c
            ep.incident_occurred = incident_occurred
            ep.success = success
            ep.reward = reward

            # 8. Upsert StrategyScore (Task 6)
            strategy_key = ep.action_taken
            score = db.get(StrategyScore, strategy_key)
            if score is None:
                score = StrategyScore(
                    strategy_key=strategy_key,
                    success_count=0,
                    failure_count=0,
                    total_water_saved_l=0.0,
                )
                db.add(score)
                # Flush immediately so subsequent loop iterations can locate
                # this row via db.get() and avoid a UNIQUE PK violation.
                db.flush()

            if success:
                score.success_count += 1
            else:
                score.failure_count += 1

            if water_delta_pct < 0 and initial_water > 0:
                water_saved_l = abs(initial_water - current_water)
                score.total_water_saved_l = round(score.total_water_saved_l + water_saved_l, 2)

            # Beta-distribution mean: (successes+1) / (successes+failures+2)
            score.confidence = round(
                (score.success_count + 1) / (score.success_count + score.failure_count + 2), 3
            )
            score.last_used_at = now

            resolved_count += 1
            logger.debug("Resolved episode %s: success=%s reward=%.3f", ep.episode_id[:8], success, reward)

        db.commit()
        logger.info("resolve_pending_episodes: resolved=%d", resolved_count)

    except Exception as exc:
        db.rollback()
        logger.error("resolve_pending_episodes failed: %s", exc)
        raise
    finally:
        if own_session:
            db.close()

    return {"resolved_episodes": resolved_count}

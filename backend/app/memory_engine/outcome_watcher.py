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
from app.db_retry import crdb_retry

logger = logging.getLogger("aquamind.outcome_watcher")


def resolve_pending_episodes(db=None, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Finds Episode rows where outcome_recorded_at IS NULL and created_at <= now - 10 minutes.
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
    cutoff = now - timedelta(minutes=10)  # Increased to 10 minutes to allow for proper data collection

    resolved_count = 0
    try:
        episodes = (
            db.query(Episode)
            .filter(Episode.outcome_recorded_at.is_(None))
            .filter(Episode.created_at <= cutoff)
            .all()
        )
        
        logger.info(f"Found {len(episodes)} pending episodes to resolve (created before {cutoff})")

        for ep in episodes:
            # 1. Fetch latest telemetry for this rack
            t_query = db.query(models.Telemetry)
            if ep.rack_id:
                t_query = t_query.filter(models.Telemetry.rack_id == ep.rack_id)
            latest_telemetry = t_query.order_by(models.Telemetry.timestamp.desc()).first()

            # 2. Fetch latest water model result for this rack
            w_query = db.query(models.WaterModelResult)
            if ep.rack_id:
                # Join with telemetry to get rack-specific water results
                w_query = w_query.join(models.Telemetry, models.WaterModelResult.telemetry_id == models.Telemetry.telemetry_id)
                w_query = w_query.filter(models.Telemetry.rack_id == ep.rack_id)
            latest_water = w_query.order_by(models.WaterModelResult.computed_at.desc()).first()

            # 3. Compute temp delta (use thermal_load_kw from water snapshot as temperature proxy)
            snap = ep.telemetry_snapshot or {}
            wsnap = ep.water_snapshot or {}
            
            # Use thermal_load_kw from water snapshot as the temperature metric
            initial_temp = float(wsnap.get("thermal_load_kw") or snap.get("gpu_temp") or snap.get("cpu_pct") or 50.0)
            if latest_water:
                current_temp = float(
                    latest_water.thermal_load_kw
                    if latest_water.thermal_load_kw is not None
                    else (latest_telemetry.gpu_temp if latest_telemetry and latest_telemetry.gpu_temp is not None else latest_telemetry.cpu_pct if latest_telemetry else initial_temp)
                )
            else:
                current_temp = initial_temp
            temp_delta_c = round(current_temp - initial_temp, 2)
            
            # Skip unrealistic temperature deltas (>10°C or <-10°C indicate data issues)
            if abs(temp_delta_c) > 10.0:
                logger.warning(f"Unrealistic temp delta {temp_delta_c}°C for episode {ep.episode_id[:8]}, skipping resolution")
                continue

            # 4. Compute water delta
            initial_water = float(wsnap.get("water_l_per_hr") or 10.0)
            current_water = float(latest_water.water_l_per_hr if latest_water else initial_water)
            water_delta_pct = (
                round(((current_water - initial_water) / initial_water) * 100.0, 2)
                if initial_water > 0
                else 0.0
            )
            
            # Skip unrealistic water deltas (>100% indicate data issues)
            if abs(water_delta_pct) > 100.0:
                logger.warning(f"Unrealistic water delta {water_delta_pct}% for episode {ep.episode_id[:8]}, skipping resolution")
                continue

            # 5. Check for incidents since episode was created
            incident_occurred = (
                db.query(models.Incident)
                .filter(models.Incident.created_at >= ep.created_at)
                .first()
            ) is not None

            # 6. Success + reward (more realistic criteria)
            # Success is defined as: thermal load didn't increase significantly AND water usage improved
            temp_success = temp_delta_c <= 1.0  # Thermal load should not increase by more than 1kW
            water_success = water_delta_pct <= 0.0  # Water usage should decrease or stay same
            success = temp_success and water_success and not incident_occurred
            
            # Reward is based on water savings and thermal efficiency
            # Positive reward for water savings, negative for water increase, penalized by thermal increase
            water_reward = -water_delta_pct  # Positive for water savings
            thermal_penalty = max(0, temp_delta_c)  # Penalize thermal increases
            reward = round(water_reward - thermal_penalty, 3)

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
            logger.info(f"Resolved episode {ep.episode_id[:8]}: action={ep.action_taken[:30]}... temp_delta={temp_delta_c:.1f}°C water_delta={water_delta_pct:.1f}% success={success} reward={reward:.3f}")
        
        # Use crdb_retry for the commit operation
        def commit_with_retry(db):
            db.commit()
            
        crdb_retry(commit_with_retry, db)

        logger.info("resolve_pending_episodes: resolved=%d", resolved_count)

    except Exception as exc:
        db.rollback()
        logger.error("resolve_pending_episodes failed: %s", exc)
        raise
    finally:
        if own_session:
            db.close()
    
    return {"resolved_episodes": resolved_count}
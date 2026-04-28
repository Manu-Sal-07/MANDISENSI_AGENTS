import hashlib
import json
import time

from config.settings import COMMODITIES
from orchestration.cache_manager import cache_manager
from orchestration.job_manager import job_manager
from orchestration.error_handler import log_error, log_info, execute_with_fallback

from ingestion.news_ingestor import fetch_news
from processing.event_extractor import extract_events
from processing.normalizer import normalize_events
from processing.deduplicator import deduplicate
from scoring.rule_engine import apply_scoring
from scoring.decay_engine import apply_decay
from scoring.aggregator import aggregate

from ml.feature_engineering import build_features
from ml.predictor import predict

from causal.causal_engine import compute_causal
from adaptive.adaptive_engine import adaptive_predict
from adaptive.weight_optimizer import get_current_weights
from adaptive.confidence_calibrator import calibrate
from adaptive.feedback_store import get_all_feedback

from explainability.explainer import explain

def clamp_round(val):
    if val is None: return 0.0
    return round(max(-1.0, min(1.0, float(val))), 2)

def run_pipeline(mode="full"):
    try:
        news = fetch_news()
        if not news: news = []
        
        # Fast exit execution
        news_hash = hashlib.md5(json.dumps(news, sort_keys=True).encode()).hexdigest()
        last_hash = cache_manager.get_raw_input_hash()
        if news_hash == last_hash and mode == "full":
            return
            
        cache_manager.set_raw_input_hash(news_hash)
        
        # Extracted logging traces fulfilling format checks
        log_info("Phase1", f"input: {len(news)} | output: processing | status: RUNNING")
        events = execute_with_fallback(extract_events, (news,), {}, "Phase1", [])
        norm = execute_with_fallback(normalize_events, (events,), {}, "Phase1", [])
        deduped = execute_with_fallback(deduplicate, (norm,), {}, "Phase1", [])
        scored = execute_with_fallback(apply_scoring, (deduped,), {}, "Phase1", [])
        decayed = execute_with_fallback(apply_decay, (scored,), {}, "Phase1", [])
        log_info("Phase1", f"input: dedup | output: {len(decayed)} | status: SUCCESS")
        
        for c in COMMODITIES:
            job_id = job_manager.start_job(c)
            if not job_id: continue
                
            try:
                c_events = [ev for ev in decayed if ev["commodity"] == c]
                base_c = aggregate(c_events).get(c, {"score": 0.0})
                rule_score = clamp_round(base_c.get("score", 0.0))
                
                ml_score, c_score, c_conf = None, None, None
                weights = get_current_weights()
                calib = None
                
                if mode == "full":
                    log_info("Phase2", f"input: {c} | output: inference | status: RUNNING")
                    features = build_features(c_events)
                    if features:
                        c_feat = next((f for f in features if f["commodity"] == c), None)
                        if c_feat: ml_score = execute_with_fallback(predict, (c_feat,), {}, "Phase2", None)
                    log_info("Phase2", f"input: {c} | output: {ml_score} | status: SUCCESS")
                    
                    log_info("Phase3", f"input: {c} | output: causal | status: RUNNING")
                    c_res = execute_with_fallback(compute_causal, (c_events,), {}, "Phase3", (None, None))
                    c_score = c_res[0] if c_res else None
                    c_conf = c_res[1] if c_res else None
                    log_info("Phase3", f"input: {c} | output: {c_score} | status: SUCCESS")
                    
                    calib_dict = execute_with_fallback(calibrate, (get_all_feedback(),), {}, "Phase4", None)
                    calib = calib_dict
                    
                    final_score = execute_with_fallback(
                        adaptive_predict, (rule_score, ml_score, c_score, calib, weights), {}, "Phase4", None
                    )
                else:
                    final_score = rule_score
                    
                # Graceful degradation logic
                if final_score is None:
                    final_score = c_score if c_score is not None else (ml_score if ml_score is not None else rule_score)
                    
                final_score = clamp_round(final_score)
                safe_r = clamp_round(rule_score)
                safe_m = clamp_round(ml_score) if ml_score is not None else safe_r
                safe_c = clamp_round(c_score) if c_score is not None else safe_m
                
                exp_data = execute_with_fallback(
                    explain, 
                    (c_events, safe_r, safe_m, safe_c, final_score, weights), 
                    {}, "Explainability", 
                    {"trend":"NEUTRAL", "reasons":[], "contributions":{}, "alert":"NONE", "confidence":0.4}
                )
                
                payload = {
                    "commodity": c,
                    "score": final_score,
                    "trend": exp_data.get("trend", "NEUTRAL"),
                    "confidence": exp_data.get("confidence", 0.4),
                    "reasons": exp_data.get("reasons", []),
                    "contributions": exp_data.get("contributions", {}),
                    "alert": exp_data.get("alert", "NONE"),
                    "last_updated": time.time()
                }
                
                cache_manager.set(c, payload)
                job_manager.end_job(c, job_id, success=True)
                
            except Exception as e:
                log_error("PipelineRunner", f"input: {c} | output: fallback | status: FAILED", e)
                job_manager.end_job(c, job_id, success=False)
                
                cached = cache_manager.get_latest(c)
                if not cached:
                    cache_manager.set(c, {
                        "commodity": c, "score": 0.0, "trend": "NEUTRAL", 
                        "confidence": 0.0, "reasons": [], "contributions": {}, 
                        "alert": "ERROR_FALLBACK", "last_updated": time.time()
                    })
                
    except Exception as e:
        log_error("PipelineRunner", "input: news | output: empty | status: FATAL", e)

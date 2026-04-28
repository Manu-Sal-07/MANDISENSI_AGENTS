import unittest
from ingestion.news_ingestor import fetch_news
from processing.event_extractor import extract_events
from processing.normalizer import normalize_events
from processing.deduplicator import deduplicate
from scoring.rule_engine import apply_scoring
from scoring.decay_engine import apply_decay
from scoring.aggregator import aggregate

class TestPipeline(unittest.TestCase):
    def test_pipeline_flows(self):
        news = fetch_news()
        self.assertGreater(len(news), 0)
        
        events = extract_events(news)
        self.assertGreater(len(events), 0)
        
        norm = normalize_events(events)
        self.assertGreater(len(norm), 0)
        
        dedup = deduplicate(norm)
        self.assertLessEqual(len(dedup), len(norm))
        
        scored = apply_scoring(dedup)
        self.assertEqual(len(scored), len(dedup))
        
        decayed = apply_decay(scored)
        
        final_scores = aggregate(decayed)
        self.assertIn("onion", final_scores)
        self.assertIn("wheat", final_scores)
        self.assertIn("rice", final_scores)
        
        self.assertEqual(final_scores["onion"]["score"], 0.59)
        self.assertEqual(final_scores["wheat"]["score"], 0.32)
        self.assertEqual(final_scores["rice"]["score"], 0.0)

if __name__ == '__main__':
    unittest.main()

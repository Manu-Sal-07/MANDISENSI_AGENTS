import sqlite3

class MemoryDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commodity TEXT,
                    event_type TEXT,
                    confidence REAL,
                    event_date TEXT,
                    impact REAL,
                    adjusted_score REAL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    commodity TEXT PRIMARY KEY,
                    score REAL,
                    rule_score REAL,
                    ml_score REAL,
                    causal_score REAL,
                    causal_confidence REAL,
                    event_count INTEGER,
                    confidence_level TEXT
                )
            """)

    def store_events(self, events):
        with self.conn:
            for ev in events:
                self.conn.execute("""
                    INSERT INTO events (commodity, event_type, confidence, event_date, impact, adjusted_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (ev["commodity"], ev["event_type"], ev["confidence"], ev["event_date"], ev.get("impact",0), ev.get("adjusted_score",0)))

    def store_scores(self, scores_dict):
        with self.conn:
            for comm, data in scores_dict.items():
                self.conn.execute("""
                    INSERT INTO scores (commodity, score, rule_score, ml_score, causal_score, causal_confidence, event_count, confidence_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(commodity) DO UPDATE SET
                        score=excluded.score,
                        rule_score=excluded.rule_score,
                        ml_score=excluded.ml_score,
                        causal_score=excluded.causal_score,
                        causal_confidence=excluded.causal_confidence,
                        event_count=excluded.event_count,
                        confidence_level=excluded.confidence_level
                """, (comm, data["score"], data.get("rule_score"), data.get("ml_score"), 
                      data.get("causal_score"), data.get("causal_confidence"), 
                      data["event_count"], data["confidence_level"]))

    def get_score(self, commodity):
        cur = self.conn.cursor()
        cur.execute("SELECT commodity, score, rule_score, ml_score, causal_score, causal_confidence FROM scores WHERE commodity=?", (commodity,))
        row = cur.fetchone()
        if row:
            return {
                "commodity": row[0],
                "score": row[1],
                "rule_score": row[2],
                "ml_score": row[3],
                "causal_score": row[4],
                "causal_confidence": row[5]
            }
        return None

db_instance = MemoryDB()

def store_data(events, scores):
    db_instance.store_events(events)
    db_instance.store_scores(scores)

-- ═══════════════════════════════════════════════════════════════════════════════
-- MandiSense AI — Production Database Schema
--
-- PostgreSQL 15+
-- Run: psql -U mandisense -d mandisense_db -f schema.sql
--
-- Design rationale:
--   • prediction_log: Core table. Stores every prediction cycle with all agent
--     inputs, Phase-1 outputs, and backfilled actuals. Replaces JSONL logging.
--   • market_prices: Time-series of daily commodity prices per mandi.
--   • arrival_volumes: Time-series of daily arrival quantities.
--   • model_registry: Tracks trained model versions for rollback & audit.
--   • api_request_log: Optional structured request/response logging (JSONB).
--
-- Indexing philosophy:
--   • Composite indexes on (commodity, mandi, time DESC) for the hot path.
--   • Partial indexes on NULL columns to accelerate backfill queries.
--   • No unnecessary indexes — each one slows writes.
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── 1. Prediction Log ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prediction_log (
    -- Primary key
    id                      BIGSERIAL       PRIMARY KEY,
    record_id               UUID            NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    -- Context
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    commodity               VARCHAR(50)     NOT NULL,
    mandi                   VARCHAR(100)    NOT NULL,

    -- Seasonality Agent Inputs
    seasonality_pred_30d    DECIMAL(10,6),
    seasonality_confidence  DECIMAL(5,4),
    seasonality_volatility  DECIMAL(5,4),
    seasonality_regime      VARCHAR(30),

    -- Arrival Agent Inputs
    arrival_pred_7d         DECIMAL(10,6),
    arrival_confidence      DECIMAL(5,4),
    arrival_supply_stress   DECIMAL(5,4),
    arrival_regime          VARCHAR(30),

    -- External Agent Inputs
    external_impact         DECIMAL(5,4),
    external_confidence     DECIMAL(5,4),

    -- Phase-1.5 Outputs
    phase1_prediction       DECIMAL(8,4),
    phase1_confidence       DECIMAL(5,4),
    phase1_conflict         BOOLEAN         DEFAULT FALSE,
    phase1_strong_conflict  BOOLEAN         DEFAULT FALSE,

    -- Phase-2.5 Outputs (nullable — only set when learned model runs)
    final_prediction        DECIMAL(8,4),
    final_confidence        DECIMAL(5,4),
    alpha                   DECIMAL(5,4),
    learned_residual        DECIMAL(8,4),
    regime_detected         VARCHAR(30),
    blend_mode              VARCHAR(20),

    -- Outcome (backfilled after 7 days)
    actual_7d_change        DECIMAL(8,4),
    outcome_filled_at       TIMESTAMPTZ
);

-- Hot-path: fetch predictions for a commodity/mandi sorted by time
CREATE INDEX IF NOT EXISTS idx_pred_commodity_time
    ON prediction_log (commodity, mandi, created_at DESC);

-- Backfill query: find unfilled records efficiently
CREATE INDEX IF NOT EXISTS idx_pred_unfilled
    ON prediction_log (commodity, mandi, created_at)
    WHERE actual_7d_change IS NULL;

-- Training query: fetch completed records sorted by time
CREATE INDEX IF NOT EXISTS idx_pred_completed
    ON prediction_log (commodity, mandi, created_at)
    WHERE actual_7d_change IS NOT NULL;

-- UUID lookup (for API record retrieval)
-- Already covered by UNIQUE constraint on record_id


-- ── 2. Market Prices ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS market_prices (
    id              BIGSERIAL       PRIMARY KEY,
    commodity       VARCHAR(50)     NOT NULL,
    mandi           VARCHAR(100)    NOT NULL,
    price_date      DATE            NOT NULL,
    modal_price     DECIMAL(10,2),
    min_price       DECIMAL(10,2),
    max_price       DECIMAL(10,2),
    created_at      TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT uq_market_price UNIQUE (commodity, mandi, price_date)
);

CREATE INDEX IF NOT EXISTS idx_prices_lookup
    ON market_prices (commodity, mandi, price_date DESC);


-- ── 3. Arrival Volumes ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS arrival_volumes (
    id                  BIGSERIAL       PRIMARY KEY,
    commodity           VARCHAR(50)     NOT NULL,
    mandi               VARCHAR(100)    NOT NULL,
    arrival_date        DATE            NOT NULL,
    quantity_tonnes     DECIMAL(12,2),
    created_at          TIMESTAMPTZ     DEFAULT NOW(),

    CONSTRAINT uq_arrival_volume UNIQUE (commodity, mandi, arrival_date)
);

CREATE INDEX IF NOT EXISTS idx_arrivals_lookup
    ON arrival_volumes (commodity, mandi, arrival_date DESC);


-- ── 4. Model Registry ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_registry (
    id              SERIAL          PRIMARY KEY,
    regime          VARCHAR(30)     NOT NULL,
    version         VARCHAR(20)     NOT NULL,
    r2_train        DECIMAL(6,4),
    r2_val          DECIMAL(6,4),
    mae_val         DECIMAL(8,4),
    n_train         INTEGER,
    n_val           INTEGER,
    artifact_path   VARCHAR(500),
    feature_names   TEXT[],         -- PostgreSQL array of feature names
    trained_at      TIMESTAMPTZ     NOT NULL,
    is_active       BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    notes           TEXT
);

-- Quick lookup of active model per regime
CREATE INDEX IF NOT EXISTS idx_model_active
    ON model_registry (regime) WHERE is_active = TRUE;

-- History lookup
CREATE INDEX IF NOT EXISTS idx_model_regime_time
    ON model_registry (regime, trained_at DESC);


-- ── 5. API Request Log (Optional — for debugging / audit) ────────────────────

CREATE TABLE IF NOT EXISTS api_request_log (
    id              BIGSERIAL       PRIMARY KEY,
    request_id      VARCHAR(30)     NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    endpoint        VARCHAR(100),
    method          VARCHAR(10),
    commodity       VARCHAR(50),
    mandi           VARCHAR(100),
    latency_ms      DECIMAL(8,1),
    status_code     SMALLINT,
    request_body    JSONB,
    response_body   JSONB
);

CREATE INDEX IF NOT EXISTS idx_api_log_time
    ON api_request_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_log_commodity
    ON api_request_log (commodity, mandi, created_at DESC);

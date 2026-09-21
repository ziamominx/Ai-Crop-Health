-- ============================================================
-- Agricure — AI Crop Health & Early Warning Agent
-- PostgreSQL schema (reference DDL).
--
-- The FastAPI app creates the same schema automatically via
-- SQLAlchemy (Base.metadata.create_all) on startup / seed.
-- Use this file when you prefer explicit SQL setup or psql.
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120)  NOT NULL,
    email           VARCHAR(255)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    role            VARCHAR(10)   NOT NULL DEFAULT 'FARMER'
                    CHECK (role IN ('FARMER', 'OFFICER', 'ADMIN')),
    phone           VARCHAR(20),
    language        VARCHAR(5)    NOT NULL DEFAULT 'en',
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS farms (
    id          SERIAL PRIMARY KEY,
    farmer_id   INTEGER       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_name   VARCHAR(160)  NOT NULL,
    location    VARCHAR(120)  NOT NULL,
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    district    VARCHAR(120),
    state       VARCHAR(120)  DEFAULT 'Maharashtra',
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_farms_farmer ON farms (farmer_id);

CREATE TABLE IF NOT EXISTS crop_reports (
    id                 SERIAL PRIMARY KEY,
    farmer_id          INTEGER      NOT NULL REFERENCES users(id),
    farm_id            INTEGER      REFERENCES farms(id),
    crop               VARCHAR(60)  NOT NULL,
    image_url          VARCHAR(500),
    image_path         VARCHAR(500),
    disease            VARCHAR(120),
    is_healthy         BOOLEAN      NOT NULL DEFAULT FALSE,
    confidence         DOUBLE PRECISION NOT NULL DEFAULT 0,
    severity           VARCHAR(10)  NOT NULL DEFAULT 'Low'
                       CHECK (severity IN ('Low', 'Moderate', 'High')),
    risk_level         VARCHAR(10)  NOT NULL DEFAULT 'Low'
                       CHECK (risk_level IN ('Low', 'Moderate', 'High')),
    risk_score         INTEGER      NOT NULL DEFAULT 0,
    risk_factors       TEXT,
    model_version      VARCHAR(60),
    is_demo_inference  BOOLEAN      NOT NULL DEFAULT FALSE,
    temperature        DOUBLE PRECISION,
    humidity           DOUBLE PRECISION,
    rainfall           DOUBLE PRECISION,
    soil_moisture      DOUBLE PRECISION,
    leaf_wetness       DOUBLE PRECISION,
    pest_count         INTEGER,
    location           VARCHAR(120),
    status             VARCHAR(12)  NOT NULL DEFAULT 'PENDING'
                       CHECK (status IN ('PENDING','ANALYZED','VERIFIED','CORRECTED','REJECTED')),
    officer_verified   BOOLEAN      NOT NULL DEFAULT FALSE,
    low_confidence     BOOLEAN      NOT NULL DEFAULT FALSE,
    followup_days      INTEGER      NOT NULL DEFAULT 7,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_reports_farmer  ON crop_reports (farmer_id);
CREATE INDEX IF NOT EXISTS ix_reports_farm    ON crop_reports (farm_id);
CREATE INDEX IF NOT EXISTS ix_reports_crop    ON crop_reports (crop);
CREATE INDEX IF NOT EXISTS ix_reports_loc     ON crop_reports (location);
CREATE INDEX IF NOT EXISTS ix_reports_created ON crop_reports (created_at);

CREATE TABLE IF NOT EXISTS recommendations (
    id              SERIAL PRIMARY KEY,
    report_id       INTEGER      NOT NULL REFERENCES crop_reports(id) ON DELETE CASCADE,
    recommendation  VARCHAR(500) NOT NULL,
    priority        VARCHAR(20)  NOT NULL DEFAULT 'MEDIUM',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_reco_report ON recommendations (report_id);

CREATE TABLE IF NOT EXISTS referrals (
    id          SERIAL PRIMARY KEY,
    report_id   INTEGER      NOT NULL REFERENCES crop_reports(id),
    farmer_id   INTEGER      NOT NULL REFERENCES users(id),
    officer_id  INTEGER      REFERENCES users(id),
    reason      VARCHAR(300) NOT NULL,
    status      VARCHAR(12)  NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','ASSIGNED','IN_PROGRESS','RESOLVED')),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_referrals_report  ON referrals (report_id);
CREATE INDEX IF NOT EXISTS ix_referrals_farmer  ON referrals (farmer_id);
CREATE INDEX IF NOT EXISTS ix_referrals_officer ON referrals (officer_id);

CREATE TABLE IF NOT EXISTS officer_verifications (
    id                   SERIAL PRIMARY KEY,
    report_id            INTEGER      NOT NULL REFERENCES crop_reports(id),
    officer_id           INTEGER      NOT NULL REFERENCES users(id),
    original_disease     VARCHAR(120),
    corrected_disease    VARCHAR(120),
    remarks              VARCHAR(500),
    lab_sample_requested BOOLEAN      NOT NULL DEFAULT FALSE,
    verified_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_verify_report  ON officer_verifications (report_id);
CREATE INDEX IF NOT EXISTS ix_verify_officer ON officer_verifications (officer_id);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id           SERIAL PRIMARY KEY,
    farm_id      INTEGER     NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    trap_type    VARCHAR(60),
    temperature  DOUBLE PRECISION,
    humidity     DOUBLE PRECISION,
    soil_moisture DOUBLE PRECISION,
    leaf_wetness DOUBLE PRECISION,
    pest_count   INTEGER,
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sensors_farm ON sensor_readings (farm_id);

CREATE TABLE IF NOT EXISTS notifications (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER      NOT NULL REFERENCES users(id),
    report_id  INTEGER      REFERENCES crop_reports(id),
    type       VARCHAR(40)  NOT NULL,
    title      VARCHAR(160) NOT NULL,
    message    TEXT         NOT NULL,
    is_read    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_notif_user ON notifications (user_id);

CREATE TABLE IF NOT EXISTS model_feedback (
    id                  SERIAL PRIMARY KEY,
    report_id           INTEGER      NOT NULL REFERENCES crop_reports(id),
    predicted_disease   VARCHAR(120),
    actual_disease      VARCHAR(120),
    was_correct         BOOLEAN      NOT NULL,
    officer_id          INTEGER      NOT NULL REFERENCES users(id),
    in_retraining_queue BOOLEAN      NOT NULL DEFAULT FALSE,
    model_version       VARCHAR(60),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_feedback_report  ON model_feedback (report_id);
CREATE INDEX IF NOT EXISTS ix_feedback_officer ON model_feedback (officer_id);

CREATE TABLE IF NOT EXISTS model_versions (
    id               SERIAL PRIMARY KEY,
    version          VARCHAR(60)  NOT NULL UNIQUE,
    model_name       VARCHAR(160) NOT NULL,
    status           VARCHAR(30)  NOT NULL DEFAULT 'ACTIVE',
    training_samples INTEGER      NOT NULL DEFAULT 0,
    accuracy         DOUBLE PRECISION,
    notes            VARCHAR(500),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_settings (
    key          VARCHAR(60)  PRIMARY KEY,
    value        VARCHAR(120) NOT NULL,
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_decisions (
    id                            SERIAL PRIMARY KEY,
    report_id                     INTEGER NOT NULL REFERENCES crop_reports(id),
    decision                      VARCHAR(60)  NOT NULL,
    reason                        TEXT         NOT NULL,
    confidence                    DOUBLE PRECISION NOT NULL DEFAULT 0,
    spread_risk                   VARCHAR(20)  NOT NULL DEFAULT 'Low',
    spread_risk_score             INTEGER      NOT NULL DEFAULT 0,
    priority                      VARCHAR(20)  NOT NULL DEFAULT 'MEDIUM',
    recommended_action            TEXT         NOT NULL DEFAULT '',
    officer_verification_needed   BOOLEAN      NOT NULL DEFAULT FALSE,
    lab_referral_recommended      BOOLEAN      NOT NULL DEFAULT FALSE,
    regional_alert                BOOLEAN      NOT NULL DEFAULT FALSE,
    followup_days                 INTEGER      NOT NULL DEFAULT 7,
    factors                       TEXT,
    created_at                    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_agentdec_report ON agent_decisions (report_id);

CREATE TABLE IF NOT EXISTS agent_activity (
    id         SERIAL PRIMARY KEY,
    report_id  INTEGER      NOT NULL REFERENCES crop_reports(id) ON DELETE CASCADE,
    stage      VARCHAR(40)  NOT NULL,
    message    VARCHAR(300) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_activity_report ON agent_activity (report_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     REFERENCES users(id),
    action      VARCHAR(80) NOT NULL,
    entity_type VARCHAR(60),
    entity_id   INTEGER,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_user   ON audit_logs (user_id);

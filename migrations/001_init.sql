CREATE TABLE IF NOT EXISTS fixtures (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    league TEXT NOT NULL,
    home TEXT NOT NULL,
    away TEXT NOT NULL,
    kickoff TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NS',
    home_goals INTEGER,
    away_goals INTEGER
);
CREATE INDEX IF NOT EXISTS idx_fixtures_date ON fixtures (date);

CREATE TABLE IF NOT EXISTS snapshots (
    fixture_id INTEGER NOT NULL REFERENCES fixtures (id),
    ts TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    home_o REAL NOT NULL,
    draw_o REAL NOT NULL,
    away_o REAL NOT NULL,
    PRIMARY KEY (fixture_id, ts, bookmaker)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_fixture ON snapshots (fixture_id);

CREATE TABLE IF NOT EXISTS slips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    legs_json TEXT NOT NULL,
    total_odds REAL NOT NULL,
    joint_p REAL NOT NULL,
    eff_joint_p REAL NOT NULL,
    bonus_pct REAL NOT NULL DEFAULT 0,
    stake REAL NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    validated INTEGER NOT NULL DEFAULT 0,
    placed_at TEXT,
    bet_id TEXT
);

CREATE TABLE IF NOT EXISTS settlements (
    slip_id INTEGER PRIMARY KEY REFERENCES slips (id),
    result TEXT NOT NULL,
    via_2up INTEGER NOT NULL DEFAULT 0,
    payout REAL NOT NULL DEFAULT 0,
    bonus_paid REAL NOT NULL DEFAULT 0,
    settled_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    bankroll_before REAL NOT NULL,
    delta REAL NOT NULL,
    bankroll_after REAL NOT NULL,
    ref TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_usage (
    day TEXT PRIMARY KEY,
    calls INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ratings_cache (
    season TEXT NOT NULL,
    team TEXT NOT NULL,
    att_h REAL,
    def_h REAL,
    att_a REAL,
    def_a REAL,
    n_home REAL,
    n_away REAL,
    PRIMARY KEY (season, team)
);

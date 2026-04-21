-- WorldQuant BRAIN 因子库数据库
-- SQLite Schema

-- =====================================================
-- 因子表
-- =====================================================
CREATE TABLE IF NOT EXISTS factors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alpha_id TEXT UNIQUE NOT NULL,      -- Alpha唯一标识
    name TEXT,                           -- 因子名称
    type TEXT NOT NULL,                  -- 类型: PPA, AIAC, EXPERIMENTAL
    expression TEXT NOT NULL,            -- Alpha表达式
    region TEXT,                         -- 地区: USA, EUR, CHN, etc.

    -- 核心指标
    sharpe REAL,                        -- Sharpe ratio
    fitness REAL,                        -- Fitness
    turnover REAL,                       -- Turnover
    ppc REAL,                           -- Power Pool Correlation
    margin REAL,                         -- Margin

    -- 元数据
    dataset_id TEXT,                     -- 数据集ID
    theme TEXT,                          -- Theme名称
    tags TEXT,                           -- JSON数组标签
    notes TEXT,                          -- 备注

    -- 状态
    status TEXT DEFAULT 'draft',         -- draft, testing, ready, submitted, active
    os_score REAL,                       -- 续航力评分

    -- 时间戳
    created_date TEXT,
    updated_date TEXT,
    submitted_date TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_factors_type ON factors(type);
CREATE INDEX IF NOT EXISTS idx_factors_status ON factors(status);
CREATE INDEX IF NOT EXISTS idx_factors_region ON factors(region);
CREATE INDEX IF NOT EXISTS idx_factors_sharpe ON factors(sharpe);
CREATE INDEX IF NOT EXISTS idx_factors_ppc ON factors(ppc);

-- =====================================================
-- 相关性族群表
-- =====================================================
CREATE TABLE IF NOT EXISTS alpha_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER NOT NULL,         -- 族群ID
    alpha_id TEXT NOT NULL,             -- Alpha唯一标识

    -- 族群信息
    correlation_threshold REAL,           -- 相关性阈值
    representative_id TEXT,               -- 代表Alpha ID

    -- 约束
    UNIQUE(family_id, alpha_id),

    FOREIGN KEY (alpha_id) REFERENCES factors(alpha_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_families_family_id ON alpha_families(family_id);

-- =====================================================
-- 提交记录表
-- =====================================================
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alpha_id TEXT NOT NULL,
    submitted_date TEXT NOT NULL,

    -- 提交时的指标
    sharpe REAL,
    fitness REAL,
    ppc REAL,
    turnover REAL,

    -- 结果
    result TEXT,                         -- accepted, rejected, pending
    rejection_reasons TEXT,              -- JSON数组

    FOREIGN KEY (alpha_id) REFERENCES factors(alpha_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_submissions_alpha ON submissions(alpha_id);
CREATE INDEX IF NOT EXISTS idx_submissions_date ON submissions(submitted_date);

-- =====================================================
-- 数据集表
-- =====================================================
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT UNIQUE NOT NULL,    -- 数据集标识
    name TEXT,                           -- 数据集名称
    region TEXT,                         -- 地区
    description TEXT,                     -- 描述

    -- 字段统计
    field_count INTEGER,
    field_pattern TEXT,                 -- 字段命名模式

    -- 状态
    last_used TEXT,                      -- 最后使用时间
    favorite INTEGER DEFAULT 0          -- 是否收藏
);

-- =====================================================
-- 每日研究日志表
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date TEXT UNIQUE NOT NULL,      -- 日期 YYYY-MM-DD

    -- 当日统计
    alphas_mined INTEGER DEFAULT 0,     -- 挖掘Alpha数
    alphas_submitted INTEGER DEFAULT 0, -- 提交数
    alphas_accepted INTEGER DEFAULT 0,  -- 通过数

    -- 遇到的问题
    issues TEXT,                        -- JSON数组

    -- 明日计划
    tomorrow_plan TEXT,

    -- 时间戳
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 触发器：自动更新updated_date
-- =====================================================
CREATE TRIGGER IF NOT EXISTS update_factor_timestamp
AFTER UPDATE ON factors
BEGIN
    UPDATE factors SET updated_date = datetime('now') WHERE alpha_id = NEW.alpha_id;
END;

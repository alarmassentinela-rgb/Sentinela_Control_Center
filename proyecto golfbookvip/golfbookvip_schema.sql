-- ============================================================
-- GOLFBOOKVIP.COM — Schema Completo PostgreSQL
-- Versión: 1.0
-- ============================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis"; -- Para coordenadas GPS del campo

-- ============================================================
-- SECCIÓN 1: SUSCRIPCIONES Y PLANES
-- ============================================================

CREATE TABLE subscription_plans (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(50) UNIQUE NOT NULL, -- 'free', 'player_pro', 'club_starter', 'club_pro', 'enterprise'
    name            VARCHAR(100) NOT NULL,
    plan_type       VARCHAR(20) NOT NULL CHECK (plan_type IN ('player', 'club')),
    price_monthly   DECIMAL(10,2) DEFAULT 0,
    price_yearly    DECIMAL(10,2) DEFAULT 0,
    max_members     INT,           -- NULL = ilimitado
    max_courses     INT,           -- NULL = ilimitado
    max_groups      INT,
    max_rounds_history INT,        -- NULL = ilimitado
    features        JSONB,         -- lista de features habilitados
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Features por plan (control granular)
CREATE TABLE plan_features (
    id              SERIAL PRIMARY KEY,
    plan_id         INT REFERENCES subscription_plans(id),
    feature_key     VARCHAR(100) NOT NULL, -- 'advanced_stats', 'pdf_export', 'tee_time', etc.
    is_enabled      BOOLEAN DEFAULT TRUE,
    UNIQUE(plan_id, feature_key)
);

-- ============================================================
-- SECCIÓN 2: USUARIOS
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(30),
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    username        VARCHAR(50) UNIQUE NOT NULL,
    avatar_url      VARCHAR(500),
    gender          VARCHAR(10) CHECK (gender IN ('male', 'female', 'other')),
    birthdate       DATE,
    country         VARCHAR(100),
    city            VARCHAR(100),
    -- Hándicap
    initial_handicap        DECIMAL(4,1),   -- Capturado al registrarse
    handicap_index          DECIMAL(4,1),   -- Calculado por el sistema WHS
    handicap_last_updated   TIMESTAMPTZ,
    handicap_rounds_count   INT DEFAULT 0,  -- Rondas válidas para hándicap
    -- Suscripción
    plan_id         INT REFERENCES subscription_plans(id),
    plan_expires_at TIMESTAMPTZ,
    -- Estado
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,
    email_verified  BOOLEAN DEFAULT FALSE,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Tokens de dispositivo para Push Notifications
CREATE TABLE push_tokens (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(500) NOT NULL,
    platform        VARCHAR(20) CHECK (platform IN ('ios', 'android', 'web')),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, token)
);

-- Suscripciones de usuarios
CREATE TABLE user_subscriptions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    plan_id         INT REFERENCES subscription_plans(id),
    status          VARCHAR(20) CHECK (status IN ('active', 'cancelled', 'expired', 'trial', 'past_due')),
    stripe_sub_id   VARCHAR(200),
    trial_ends_at   TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end   TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SECCIÓN 3: CLUBES
-- ============================================================

CREATE TABLE clubs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(200) UNIQUE NOT NULL,
    description     TEXT,
    logo_url        VARCHAR(500),
    cover_url       VARCHAR(500),
    country         VARCHAR(100),
    city            VARCHAR(100),
    address         TEXT,
    phone           VARCHAR(30),
    email           VARCHAR(255),
    website         VARCHAR(300),
    instagram       VARCHAR(200),
    facebook        VARCHAR(200),
    -- Configuración
    currency        VARCHAR(10) DEFAULT 'USD',
    timezone        VARCHAR(100) DEFAULT 'America/Mexico_City',
    -- Suscripción del club
    plan_id         INT REFERENCES subscription_plans(id),
    plan_expires_at TIMESTAMPTZ,
    stripe_customer_id VARCHAR(200),
    -- Estado
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Suscripciones de clubes
CREATE TABLE club_subscriptions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id         UUID REFERENCES clubs(id),
    plan_id         INT REFERENCES subscription_plans(id),
    status          VARCHAR(20) CHECK (status IN ('active', 'cancelled', 'expired', 'trial', 'past_due')),
    stripe_sub_id   VARCHAR(200),
    trial_ends_at   TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end   TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Staff del club (admin, asistentes)
CREATE TABLE club_staff (
    id              SERIAL PRIMARY KEY,
    club_id         UUID REFERENCES clubs(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(30) CHECK (role IN ('owner', 'admin', 'staff')),
    is_active       BOOLEAN DEFAULT TRUE,
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(club_id, user_id)
);

-- Tipos de membresía del club
CREATE TABLE membership_types (
    id              SERIAL PRIMARY KEY,
    club_id         UUID REFERENCES clubs(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,  -- 'Full', 'Social', 'Junior', 'Senior', 'Corporativa'
    description     TEXT,
    monthly_fee     DECIMAL(10,2) DEFAULT 0,
    yearly_fee      DECIMAL(10,2) DEFAULT 0,
    benefits        JSONB,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Socios del club
CREATE TABLE club_members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id         UUID REFERENCES clubs(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    membership_type_id INT REFERENCES membership_types(id),
    member_number   VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'pending')),
    joined_at       DATE NOT NULL DEFAULT CURRENT_DATE,
    expires_at      DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(club_id, user_id)
);

-- Cuenta corriente del socio en el club
CREATE TABLE member_accounts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id         UUID REFERENCES clubs(id),
    user_id         UUID REFERENCES users(id),
    balance         DECIMAL(12,2) DEFAULT 0,
    credit_limit    DECIMAL(12,2) DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(club_id, user_id)
);

-- Movimientos de cuenta del socio
CREATE TABLE account_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id      UUID REFERENCES member_accounts(id),
    type            VARCHAR(30) CHECK (type IN ('charge', 'payment', 'credit', 'refund', 'bet_win', 'bet_loss', 'green_fee', 'membership_fee', 'other')),
    amount          DECIMAL(12,2) NOT NULL,
    balance_after   DECIMAL(12,2) NOT NULL,
    description     VARCHAR(500),
    reference_id    UUID,           -- ID de jugada, torneo, etc.
    reference_type  VARCHAR(50),    -- 'round', 'event', 'manual'
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SECCIÓN 4: CAMPOS DE GOLF
-- ============================================================

CREATE TABLE courses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id         UUID REFERENCES clubs(id) ON DELETE SET NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    country         VARCHAR(100),
    city            VARCHAR(100),
    address         TEXT,
    latitude        DECIMAL(10,8),
    longitude       DECIMAL(11,8),
    cover_url       VARCHAR(500),
    -- Datos técnicos
    holes_count     INT DEFAULT 18 CHECK (holes_count IN (9, 18)),
    par_total       INT,
    course_rating   DECIMAL(4,1),   -- Ej: 72.4
    slope_rating    INT,            -- Ej: 131
    -- Estado
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Hoyos del campo
CREATE TABLE course_holes (
    id              SERIAL PRIMARY KEY,
    course_id       UUID REFERENCES courses(id) ON DELETE CASCADE,
    hole_number     INT NOT NULL CHECK (hole_number BETWEEN 1 AND 18),
    par             INT NOT NULL CHECK (par BETWEEN 3 AND 6),
    stroke_index    INT CHECK (stroke_index BETWEEN 1 AND 18), -- Dificultad para hándicap
    distance_meters INT,
    distance_yards  INT,
    description     TEXT,
    image_url       VARCHAR(500),
    latitude        DECIMAL(10,8),   -- GPS del tee
    longitude       DECIMAL(11,8),
    UNIQUE(course_id, hole_number)
);

-- ============================================================
-- SECCIÓN 4B: SEGUIMIENTO ENTRE USUARIOS (para visibilidad 'friends')
-- ============================================================

CREATE TABLE user_follows (
    id              SERIAL PRIMARY KEY,
    follower_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    following_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(follower_id, following_id),
    CHECK (follower_id <> following_id)
);

CREATE INDEX idx_follows_follower ON user_follows(follower_id);
CREATE INDEX idx_follows_following ON user_follows(following_id);

-- ============================================================
-- SECCIÓN 5: GRUPOS
-- ============================================================

CREATE TABLE groups (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id         UUID REFERENCES clubs(id) ON DELETE SET NULL,
    created_by      UUID REFERENCES users(id),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    avatar_url      VARCHAR(500),
    cover_url       VARCHAR(500),
    is_private      BOOLEAN DEFAULT FALSE,
    max_members     INT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Miembros del grupo
CREATE TABLE group_members (
    id              SERIAL PRIMARY KEY,
    group_id        UUID REFERENCES groups(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    status          VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'banned', 'pending')),
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, user_id)
);

-- ============================================================
-- SECCIÓN 6: JUGADAS (ROUNDS)
-- ============================================================

CREATE TABLE rounds (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id         UUID REFERENCES clubs(id) ON DELETE SET NULL,
    group_id        UUID REFERENCES groups(id) ON DELETE SET NULL,
    course_id       UUID REFERENCES courses(id),
    created_by      UUID REFERENCES users(id),
    name            VARCHAR(200),
    -- Formato de juego
    game_format     VARCHAR(30) NOT NULL CHECK (game_format IN (
                        'stroke_play', 'stableford', 'stableford_modified',
                        'match_play', 'scramble', 'florida_scramble',
                        'best_ball', 'skins', 'par_bogey'
                    )),
    team_size       INT DEFAULT 1,   -- 1=individual, 2/3/4=equipos (Florida/Scramble)
    scoring_type    VARCHAR(20) DEFAULT 'gross' CHECK (scoring_type IN ('gross', 'net')),
    -- Horario
    scheduled_at    TIMESTAMPTZ NOT NULL,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    -- Estado
    status          VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN (
                        'scheduled', 'active', 'finished', 'cancelled'
                    )),
    holes_to_play   INT DEFAULT 18 CHECK (holes_to_play IN (9, 18)),
    -- Clima (guardado al iniciar)
    weather_temp    DECIMAL(4,1),
    weather_wind    DECIMAL(4,1),
    weather_conditions VARCHAR(100),
    -- Meta
    notes           TEXT,
    is_handicap_valid BOOLEAN DEFAULT TRUE, -- si cuenta para el hándicap WHS
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Configuración de apuestas de la jugada
CREATE TABLE round_bet_config (
    id              SERIAL PRIMARY KEY,
    round_id        UUID UNIQUE REFERENCES rounds(id) ON DELETE CASCADE,
    -- Apuesta principal
    entry_fee       DECIMAL(10,2) DEFAULT 0,      -- Monto de entrada por jugador
    -- Nassau
    nassau_enabled  BOOLEAN DEFAULT FALSE,
    nassau_front9   DECIMAL(10,2) DEFAULT 0,
    nassau_back9    DECIMAL(10,2) DEFAULT 0,
    nassau_total    DECIMAL(10,2) DEFAULT 0,
    -- Apuesta por hoyo (Skins / Match Play)
    per_hole_bet    DECIMAL(10,2) DEFAULT 0,
    -- Valor por punto (Stableford)
    point_value     DECIMAL(10,2) DEFAULT 0,
    -- Pressers
    pressers_enabled BOOLEAN DEFAULT FALSE,
    presser_amount  DECIMAL(10,2) DEFAULT 0,
    -- Pájaros
    birdie_prize    DECIMAL(10,2) DEFAULT 0,
    eagle_prize     DECIMAL(10,2) DEFAULT 0,
    albatross_prize DECIMAL(10,2) DEFAULT 0,
    hole_in_one_prize DECIMAL(10,2) DEFAULT 0,
    -- Three-putt
    three_putt_penalty DECIMAL(10,2) DEFAULT 0,
    -- Oyes (Par 3)
    oyes_enabled    BOOLEAN DEFAULT FALSE,
    oyes_prize      DECIMAL(10,2) DEFAULT 0,
    oyes_accumulates BOOLEAN DEFAULT TRUE,  -- Si nadie gana, acumula
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Jugadores confirmados en la jugada
CREATE TABLE round_players (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    round_id        UUID REFERENCES rounds(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    team_number     INT,            -- Para formatos de equipo (Florida, Scramble)
    tee_order       INT,            -- Orden de salida
    handicap_index  DECIMAL(4,1),   -- Hándicap al momento de la jugada
    course_handicap INT,            -- Hándicap ajustado al campo
    status          VARCHAR(20) DEFAULT 'invited' CHECK (status IN (
                        'invited', 'confirmed', 'declined', 'no_show', 'playing', 'finished'
                    )),
    is_guest        BOOLEAN DEFAULT FALSE,  -- Invitado externo al grupo/club
    confirmed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(round_id, user_id)
);

-- Espectadores en tiempo real
CREATE TABLE round_spectators (
    id              SERIAL PRIMARY KEY,
    round_id        UUID REFERENCES rounds(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    left_at         TIMESTAMPTZ,
    UNIQUE(round_id, user_id)
);

-- ============================================================
-- SECCIÓN 7: SCORES EN TIEMPO REAL
-- ============================================================

CREATE TABLE scores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    round_id        UUID REFERENCES rounds(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    hole_number     INT NOT NULL CHECK (hole_number BETWEEN 1 AND 18),
    -- Score
    gross_score     INT,            -- Golpes totales en el hoyo
    net_score       INT,            -- Score con hándicap aplicado
    putts           INT,            -- Número de putts
    -- Para Florida Scramble
    played_shot     BOOLEAN DEFAULT TRUE, -- FALSE si no jugó este golpe (regla Florida)
    -- Stableford
    stableford_points INT,
    -- Cálculos especiales
    is_birdie       BOOLEAN DEFAULT FALSE,
    is_eagle        BOOLEAN DEFAULT FALSE,
    is_albatross    BOOLEAN DEFAULT FALSE,
    is_hole_in_one  BOOLEAN DEFAULT FALSE,
    is_bogey        BOOLEAN DEFAULT FALSE,
    is_double_bogey BOOLEAN DEFAULT FALSE,
    is_three_putt   BOOLEAN DEFAULT FALSE,
    -- Oye (Par 3)
    oye_distance_cm INT,            -- Distancia al pin en cm
    oye_winner      BOOLEAN DEFAULT FALSE,
    -- GPS del golpe
    shot_latitude   DECIMAL(10,8),
    shot_longitude  DECIMAL(11,8),
    -- Meta
    notes           VARCHAR(500),
    recorded_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(round_id, user_id, hole_number)
);

-- Resultados de apuestas por hoyo
CREATE TABLE hole_bet_results (
    id              SERIAL PRIMARY KEY,
    round_id        UUID REFERENCES rounds(id) ON DELETE CASCADE,
    hole_number     INT NOT NULL,
    bet_type        VARCHAR(30) CHECK (bet_type IN (
                        'skin', 'match_play', 'birdie', 'eagle', 'albatross',
                        'hole_in_one', 'three_putt', 'oye', 'nassau_front',
                        'nassau_back', 'nassau_total'
                    )),
    winner_user_id  UUID REFERENCES users(id),
    amount          DECIMAL(10,2),
    is_accumulated  BOOLEAN DEFAULT FALSE,  -- El oye/skin se acumula
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Balance de apuestas por jugador (actualizado en tiempo real)
CREATE TABLE round_player_balance (
    id              SERIAL PRIMARY KEY,
    round_id        UUID REFERENCES rounds(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    -- Desglose
    entry_fee       DECIMAL(10,2) DEFAULT 0,
    nassau_balance  DECIMAL(10,2) DEFAULT 0,
    skins_balance   DECIMAL(10,2) DEFAULT 0,
    birds_earned    DECIMAL(10,2) DEFAULT 0,
    three_putt_loss DECIMAL(10,2) DEFAULT 0,
    oyes_balance    DECIMAL(10,2) DEFAULT 0,
    other_balance   DECIMAL(10,2) DEFAULT 0,
    total_balance   DECIMAL(10,2) DEFAULT 0,  -- (+) ganó / (-) debe
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(round_id, user_id)
);

-- ============================================================
-- SECCIÓN 8: HÁNDICAP WHS
-- ============================================================

-- Diferencial por ronda
CREATE TABLE score_differentials (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    round_id        UUID REFERENCES rounds(id) ON DELETE SET NULL,
    course_id       UUID REFERENCES courses(id),
    -- Datos del cálculo
    adjusted_gross_score INT NOT NULL,
    course_rating   DECIMAL(4,1) NOT NULL,
    slope_rating    INT NOT NULL,
    differential    DECIMAL(5,2) NOT NULL,  -- (AGS - CR) x (113 / SR)
    -- Ajustes WHS
    pcc_adjustment  DECIMAL(4,2) DEFAULT 0, -- Playing Conditions Calculation
    exceptional_reduction DECIMAL(4,2) DEFAULT 0,
    -- 9 hoyos
    is_nine_hole    BOOLEAN DEFAULT FALSE,
    expected_score_adjustment DECIMAL(4,2) DEFAULT 0,
    -- Control
    is_counting     BOOLEAN DEFAULT TRUE,   -- Si cuenta para el índice
    played_at       DATE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Historial de cambios del Handicap Index
CREATE TABLE handicap_history (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    handicap_index  DECIMAL(4,1) NOT NULL,
    previous_index  DECIMAL(4,1),
    differentials_used JSONB,       -- Los 8 diferenciales usados
    calculation_date DATE NOT NULL,
    rounds_counted  INT,
    soft_cap_applied BOOLEAN DEFAULT FALSE,
    hard_cap_applied BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SECCIÓN 9: ESTADÍSTICAS DEL JUGADOR
-- ============================================================

CREATE TABLE player_stats (
    id              SERIAL PRIMARY KEY,
    user_id         UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    -- Generales
    total_rounds        INT DEFAULT 0,
    total_holes         INT DEFAULT 0,
    -- Promedios
    avg_score           DECIMAL(5,2),
    avg_putts_per_round DECIMAL(4,2),
    avg_putts_per_hole  DECIMAL(4,2),
    -- Porcentajes
    fairways_hit_pct    DECIMAL(5,2),   -- % calles acertadas
    gir_pct             DECIMAL(5,2),   -- % Greens in Regulation
    -- Contadores de resultados
    total_eagles        INT DEFAULT 0,
    total_birdies       INT DEFAULT 0,
    total_pars          INT DEFAULT 0,
    total_bogeys        INT DEFAULT 0,
    total_double_bogeys INT DEFAULT 0,
    total_worse         INT DEFAULT 0,
    total_hole_in_ones  INT DEFAULT 0,
    total_three_putts   INT DEFAULT 0,
    -- Records personales
    best_score_18       INT,
    best_score_9        INT,
    best_differential   DECIMAL(5,2),
    -- Apuestas
    total_bet_won       DECIMAL(12,2) DEFAULT 0,
    total_bet_lost      DECIMAL(12,2) DEFAULT 0,
    -- Actualización
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Estadísticas por hoyo específico (para detectar hoyos difíciles)
CREATE TABLE player_hole_stats (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    course_id       UUID REFERENCES courses(id) ON DELETE CASCADE,
    hole_number     INT NOT NULL,
    times_played    INT DEFAULT 0,
    avg_score       DECIMAL(4,2),
    avg_putts       DECIMAL(4,2),
    best_score      INT,
    worst_score     INT,
    birdies         INT DEFAULT 0,
    pars            INT DEFAULT 0,
    bogeys          INT DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, course_id, hole_number)
);

-- ============================================================
-- SECCIÓN 10: LOGROS Y BADGES
-- ============================================================

CREATE TABLE badges (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(100) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    icon_url        VARCHAR(500),
    category        VARCHAR(50) CHECK (category IN ('scoring', 'consistency', 'social', 'betting', 'milestone')),
    criteria        JSONB,          -- Condiciones para obtenerlo
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE player_badges (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    badge_id        INT REFERENCES badges(id),
    round_id        UUID REFERENCES rounds(id) ON DELETE SET NULL,
    earned_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, badge_id)
);

-- ============================================================
-- SECCIÓN 11: EVENTOS Y TORNEOS DEL CLUB
-- ============================================================

CREATE TABLE club_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    club_id         UUID REFERENCES clubs(id) ON DELETE CASCADE,
    created_by      UUID REFERENCES users(id),
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    cover_url       VARCHAR(500),
    event_type      VARCHAR(30) CHECK (event_type IN ('tournament', 'social', 'training', 'announcement', 'other')),
    game_format     VARCHAR(30),    -- Formato del torneo
    start_date      TIMESTAMPTZ,
    end_date        TIMESTAMPTZ,
    registration_deadline TIMESTAMPTZ,
    max_participants INT,
    entry_fee       DECIMAL(10,2) DEFAULT 0,
    prizes          JSONB,
    status          VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'active', 'finished', 'cancelled')),
    is_members_only BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Inscripciones a eventos
CREATE TABLE event_registrations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID REFERENCES club_events(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'registered' CHECK (status IN ('registered', 'confirmed', 'cancelled', 'waitlist')),
    registered_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, user_id)
);

-- ============================================================
-- SECCIÓN 12: RESERVAS DE TEE TIME
-- ============================================================

CREATE TABLE tee_time_slots (
    id              SERIAL PRIMARY KEY,
    course_id       UUID REFERENCES courses(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    time            TIME NOT NULL,
    max_players     INT DEFAULT 4,
    available_spots INT DEFAULT 4,
    is_blocked      BOOLEAN DEFAULT FALSE,
    block_reason    VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(course_id, date, time)
);

CREATE TABLE tee_time_bookings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slot_id         INT REFERENCES tee_time_slots(id),
    user_id         UUID REFERENCES users(id),
    players_count   INT DEFAULT 1,
    status          VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'no_show')),
    notes           TEXT,
    booked_at       TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at    TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ
);

-- ============================================================
-- SECCIÓN 13: FEED SOCIAL
-- ============================================================

CREATE TABLE posts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    author_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    -- Contexto (a qué pertenece el post)
    club_id         UUID REFERENCES clubs(id) ON DELETE CASCADE,
    group_id        UUID REFERENCES groups(id) ON DELETE CASCADE,
    round_id        UUID REFERENCES rounds(id) ON DELETE SET NULL,
    -- Contenido
    content         TEXT,
    post_type       VARCHAR(30) DEFAULT 'regular' CHECK (post_type IN (
                        'regular', 'score_share', 'achievement', 'round_summary',
                        'club_announcement', 'event_announcement'
                    )),
    -- Visibilidad
    visibility      VARCHAR(20) DEFAULT 'group' CHECK (visibility IN ('public', 'club', 'group', 'friends')),
    -- Estadísticas
    comments_count  INT DEFAULT 0,
    reactions_count INT DEFAULT 0,
    -- Estado
    is_pinned       BOOLEAN DEFAULT FALSE,
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Media del post (fotos/videos)
CREATE TABLE post_media (
    id              SERIAL PRIMARY KEY,
    post_id         UUID REFERENCES posts(id) ON DELETE CASCADE,
    media_type      VARCHAR(10) CHECK (media_type IN ('image', 'video')),
    url             VARCHAR(500) NOT NULL,
    thumbnail_url   VARCHAR(500),
    order_index     INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Comentarios
CREATE TABLE post_comments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id         UUID REFERENCES posts(id) ON DELETE CASCADE,
    author_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES post_comments(id) ON DELETE SET NULL,
    content         TEXT NOT NULL,
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Reacciones (posts y scores)
CREATE TABLE reactions (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    target_type     VARCHAR(20) CHECK (target_type IN ('post', 'score', 'comment')),
    target_id       UUID NOT NULL,
    reaction_type   VARCHAR(20) CHECK (reaction_type IN ('like', 'fire', 'clap', 'laugh', 'sad')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, target_type, target_id)
);

-- ============================================================
-- SECCIÓN 14: NOTIFICACIONES
-- ============================================================

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(50) CHECK (type IN (
                        'round_invite', 'round_started', 'round_finished',
                        'score_update', 'bet_result', 'new_comment',
                        'new_reaction', 'badge_earned', 'event_reminder',
                        'membership_expiry', 'payment_due', 'club_announcement',
                        'handicap_updated', 'spectator_invite'
                    )),
    title           VARCHAR(300),
    body            TEXT,
    data            JSONB,          -- Datos extras para deep link
    is_read         BOOLEAN DEFAULT FALSE,
    is_sent_push    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SECCIÓN 15: FACTURAS Y PAGOS (Stripe)
-- ============================================================

CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    club_id         UUID REFERENCES clubs(id),
    stripe_invoice_id VARCHAR(200),
    amount          DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(10) DEFAULT 'USD',
    status          VARCHAR(20) CHECK (status IN ('draft', 'open', 'paid', 'void', 'uncollectible')),
    description     VARCHAR(500),
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES PARA RENDIMIENTO
-- ============================================================

-- Usuarios
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Jugadas
CREATE INDEX idx_rounds_club ON rounds(club_id);
CREATE INDEX idx_rounds_group ON rounds(group_id);
CREATE INDEX idx_rounds_status ON rounds(status);
CREATE INDEX idx_rounds_scheduled ON rounds(scheduled_at);

-- Scores
CREATE INDEX idx_scores_round ON scores(round_id);
CREATE INDEX idx_scores_user ON scores(user_id);
CREATE INDEX idx_scores_round_hole ON scores(round_id, hole_number);

-- Hándicap
CREATE INDEX idx_differentials_user ON score_differentials(user_id);
CREATE INDEX idx_differentials_played ON score_differentials(user_id, played_at DESC);

-- Feed social
CREATE INDEX idx_posts_club ON posts(club_id);
CREATE INDEX idx_posts_group ON posts(group_id);
CREATE INDEX idx_posts_created ON posts(created_at DESC);

-- Notificaciones
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);

-- Balance
CREATE INDEX idx_balance_round ON round_player_balance(round_id);

-- ============================================================
-- DATOS INICIALES
-- ============================================================

-- Planes de suscripción
INSERT INTO subscription_plans (code, name, plan_type, price_monthly, price_yearly, max_members, max_courses, max_groups, max_rounds_history) VALUES
('free_player',     'Jugador Free',     'player', 0,    0,    NULL, NULL, 1,    20),
('player_pro',      'Jugador Pro',      'player', 4.99, 49.9, NULL, NULL, NULL, NULL),
('free_club',       'Club Free',        'club',   0,    0,    30,   1,    NULL, NULL),
('club_starter',    'Club Starter',     'club',   49,   490,  100,  2,    NULL, NULL),
('club_pro',        'Club Pro',         'club',   149,  1490, 500,  NULL, NULL, NULL),
('club_enterprise', 'Club Enterprise',  'club',   0,    0,    NULL, NULL, NULL, NULL);

-- Badges iniciales
INSERT INTO badges (code, name, description, category) VALUES
('first_eagle',      'Primer Águila',        'Anotaste tu primer Eagle',                     'scoring'),
('hole_in_one',      'Hoyo en Uno',          'Lograste un hoyo en uno',                      'scoring'),
('five_birdies',     '5 Pájaros en un día',  'Anotaste 5 birdies en una sola ronda',         'scoring'),
('personal_best',    'Nuevo Récord',         'Lograste tu mejor score personal',             'scoring'),
('ten_wins',         'Campeón Serial',       'Ganaste 10 jugadas',                           'milestone'),
('hundred_rounds',   '100 Rondas',           'Completaste 100 rondas en el sistema',         'milestone'),
('handicap_under10', 'Élite',               'Bajaste tu hándicap a menos de 10',            'milestone'),
('first_round',      'Primera Jugada',       'Completaste tu primera jugada en el sistema',  'milestone'),
('social_star',      'Estrella Social',      'Recibiste 50 reacciones en el feed',           'social'),
('oye_king',         'Rey de los Oyes',      'Ganaste 10 oyes en par 3',                     'scoring');

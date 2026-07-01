--
-- PostgreSQL database dump
--

\restrict FbebjyUdNUqYzhqstbUKSPxsv6hXgeudTt2jL8FJF5YW259Hr4JSfujhH6bJ0Q3

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.account_transactions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    account_id uuid,
    type character varying(30),
    amount numeric(12,2) NOT NULL,
    balance_after numeric(12,2) NOT NULL,
    description character varying(500),
    reference_id uuid,
    reference_type character varying(50),
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT account_transactions_type_check CHECK (((type)::text = ANY ((ARRAY['charge'::character varying, 'payment'::character varying, 'credit'::character varying, 'refund'::character varying, 'bet_win'::character varying, 'bet_loss'::character varying, 'green_fee'::character varying, 'membership_fee'::character varying, 'other'::character varying])::text[])))
);


--
-- Name: badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.badges (
    id integer NOT NULL,
    code character varying(100) NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    icon_url character varying(500),
    category character varying(50),
    criteria jsonb,
    is_active boolean DEFAULT true,
    CONSTRAINT badges_category_check CHECK (((category)::text = ANY ((ARRAY['scoring'::character varying, 'consistency'::character varying, 'social'::character varying, 'betting'::character varying, 'milestone'::character varying])::text[])))
);


--
-- Name: badges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.badges_id_seq OWNED BY public.badges.id;


--
-- Name: club_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.club_events (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    club_id uuid,
    created_by uuid,
    title character varying(300) NOT NULL,
    description text,
    cover_url character varying(500),
    event_type character varying(30),
    game_format character varying(30),
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    registration_deadline timestamp with time zone,
    max_participants integer,
    entry_fee numeric(10,2) DEFAULT 0,
    prizes jsonb,
    status character varying(20) DEFAULT 'draft'::character varying,
    is_members_only boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT club_events_event_type_check CHECK (((event_type)::text = ANY ((ARRAY['tournament'::character varying, 'social'::character varying, 'training'::character varying, 'announcement'::character varying, 'other'::character varying])::text[]))),
    CONSTRAINT club_events_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'active'::character varying, 'finished'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: club_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.club_members (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    club_id uuid,
    user_id uuid,
    membership_type_id integer,
    member_number character varying(50),
    status character varying(20) DEFAULT 'active'::character varying,
    joined_at date DEFAULT CURRENT_DATE NOT NULL,
    expires_at date,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    onboarding_source character varying(20) DEFAULT 'manual'::character varying,
    CONSTRAINT club_members_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying, 'suspended'::character varying, 'pending'::character varying])::text[])))
);


--
-- Name: club_staff; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.club_staff (
    id integer NOT NULL,
    club_id uuid,
    user_id uuid,
    role character varying(30),
    is_active boolean DEFAULT true,
    joined_at timestamp with time zone DEFAULT now(),
    CONSTRAINT club_staff_role_check CHECK (((role)::text = ANY ((ARRAY['owner'::character varying, 'admin'::character varying, 'staff'::character varying])::text[])))
);


--
-- Name: club_staff_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.club_staff_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: club_staff_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.club_staff_id_seq OWNED BY public.club_staff.id;


--
-- Name: club_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.club_subscriptions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    club_id uuid,
    plan_id integer,
    status character varying(20),
    stripe_sub_id character varying(200),
    trial_ends_at timestamp with time zone,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    cancelled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT club_subscriptions_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'cancelled'::character varying, 'expired'::character varying, 'trial'::character varying, 'past_due'::character varying])::text[])))
);


--
-- Name: clubs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clubs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(200) NOT NULL,
    slug character varying(200) NOT NULL,
    description text,
    logo_url character varying(500),
    cover_url character varying(500),
    country character varying(100),
    city character varying(100),
    address text,
    phone character varying(30),
    email character varying(255),
    website character varying(300),
    instagram character varying(200),
    facebook character varying(200),
    currency character varying(10) DEFAULT 'USD'::character varying,
    timezone character varying(100) DEFAULT 'America/Mexico_City'::character varying,
    plan_id integer,
    plan_expires_at timestamp with time zone,
    stripe_customer_id character varying(200),
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    access_type character varying(20) DEFAULT 'private'::character varying NOT NULL,
    allow_guests boolean DEFAULT true NOT NULL,
    guest_requires_sponsor boolean DEFAULT true NOT NULL,
    max_guests_per_booking integer DEFAULT 3 NOT NULL,
    max_guest_visits_per_year integer DEFAULT 6 NOT NULL,
    guest_fee_to_sponsor boolean DEFAULT true NOT NULL,
    members_advance_days integer DEFAULT 30 NOT NULL,
    public_advance_days integer DEFAULT 7 NOT NULL,
    invite_code character varying(32),
    default_membership_type_id integer,
    CONSTRAINT clubs_access_type_check CHECK (((access_type)::text = ANY ((ARRAY['private'::character varying, 'semi_private'::character varying, 'public'::character varying])::text[])))
);


--
-- Name: course_holes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_holes (
    id integer NOT NULL,
    course_id uuid,
    hole_number integer NOT NULL,
    par integer NOT NULL,
    stroke_index integer,
    distance_meters integer,
    distance_yards integer,
    description text,
    image_url character varying(500),
    latitude numeric(10,8),
    longitude numeric(11,8),
    distance_yards_black integer,
    distance_yards_blue integer,
    distance_yards_white integer,
    distance_yards_red integer,
    green_latitude numeric(10,8),
    green_longitude numeric(11,8),
    tee_latitude numeric(10,8),
    tee_longitude numeric(11,8),
    CONSTRAINT course_holes_hole_number_check CHECK (((hole_number >= 1) AND (hole_number <= 18))),
    CONSTRAINT course_holes_par_check CHECK (((par >= 3) AND (par <= 6))),
    CONSTRAINT course_holes_stroke_index_check CHECK (((stroke_index >= 1) AND (stroke_index <= 18)))
);


--
-- Name: course_holes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_holes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_holes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_holes_id_seq OWNED BY public.course_holes.id;


--
-- Name: courses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.courses (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    club_id uuid,
    name character varying(200) NOT NULL,
    description text,
    country character varying(100),
    city character varying(100),
    address text,
    latitude numeric(10,8),
    longitude numeric(11,8),
    cover_url character varying(500),
    holes_count integer DEFAULT 18,
    par_total integer,
    course_rating numeric(4,1),
    slope_rating integer,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by uuid,
    CONSTRAINT courses_holes_count_check CHECK ((holes_count = ANY (ARRAY[9, 18])))
);


--
-- Name: event_registrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_registrations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    event_id uuid,
    user_id uuid,
    status character varying(20) DEFAULT 'registered'::character varying,
    registered_at timestamp with time zone DEFAULT now(),
    CONSTRAINT event_registrations_status_check CHECK (((status)::text = ANY ((ARRAY['registered'::character varying, 'confirmed'::character varying, 'cancelled'::character varying, 'waitlist'::character varying])::text[])))
);


--
-- Name: group_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.group_members (
    id integer NOT NULL,
    group_id uuid,
    user_id uuid,
    role character varying(20) DEFAULT 'member'::character varying,
    status character varying(20) DEFAULT 'active'::character varying,
    joined_at timestamp with time zone DEFAULT now(),
    CONSTRAINT group_members_role_check CHECK (((role)::text = ANY ((ARRAY['owner'::character varying, 'admin'::character varying, 'member'::character varying])::text[]))),
    CONSTRAINT group_members_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying, 'banned'::character varying, 'pending'::character varying])::text[])))
);


--
-- Name: group_members_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.group_members_id_seq OWNED BY public.group_members.id;


--
-- Name: groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.groups (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    club_id uuid,
    created_by uuid,
    name character varying(200) NOT NULL,
    description text,
    avatar_url character varying(500),
    cover_url character varying(500),
    is_private boolean DEFAULT false,
    max_members integer,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    invite_code character varying(10)
);


--
-- Name: handicap_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.handicap_history (
    id integer NOT NULL,
    user_id uuid,
    handicap_index numeric(4,1) NOT NULL,
    previous_index numeric(4,1),
    differentials_used jsonb,
    calculation_date date NOT NULL,
    rounds_counted integer,
    soft_cap_applied boolean DEFAULT false,
    hard_cap_applied boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: handicap_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.handicap_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: handicap_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.handicap_history_id_seq OWNED BY public.handicap_history.id;


--
-- Name: hole_bet_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hole_bet_results (
    id integer NOT NULL,
    round_id uuid,
    hole_number integer NOT NULL,
    bet_type character varying(30),
    winner_user_id uuid,
    amount numeric(10,2),
    is_accumulated boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT hole_bet_results_bet_type_check CHECK (((bet_type)::text = ANY ((ARRAY['skin'::character varying, 'match_play'::character varying, 'birdie'::character varying, 'eagle'::character varying, 'albatross'::character varying, 'hole_in_one'::character varying, 'three_putt'::character varying, 'oye'::character varying, 'nassau_front'::character varying, 'nassau_back'::character varying, 'nassau_total'::character varying])::text[])))
);


--
-- Name: hole_bet_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.hole_bet_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hole_bet_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.hole_bet_results_id_seq OWNED BY public.hole_bet_results.id;


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoices (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    club_id uuid,
    stripe_invoice_id character varying(200),
    amount numeric(10,2) NOT NULL,
    currency character varying(10) DEFAULT 'USD'::character varying,
    status character varying(20),
    description character varying(500),
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT invoices_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'open'::character varying, 'paid'::character varying, 'void'::character varying, 'uncollectible'::character varying])::text[])))
);


--
-- Name: member_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.member_accounts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    club_id uuid,
    user_id uuid,
    balance numeric(12,2) DEFAULT 0,
    credit_limit numeric(12,2) DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: membership_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.membership_types (
    id integer NOT NULL,
    club_id uuid,
    name character varying(100) NOT NULL,
    description text,
    monthly_fee numeric(10,2) DEFAULT 0,
    yearly_fee numeric(10,2) DEFAULT 0,
    benefits jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: membership_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.membership_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: membership_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.membership_types_id_seq OWNED BY public.membership_types.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    type character varying(50),
    title character varying(300),
    body text,
    data jsonb,
    is_read boolean DEFAULT false,
    is_sent_push boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT notifications_type_check CHECK (((type)::text = ANY ((ARRAY['round_invite'::character varying, 'round_started'::character varying, 'round_finished'::character varying, 'score_update'::character varying, 'bet_result'::character varying, 'new_comment'::character varying, 'new_reaction'::character varying, 'badge_earned'::character varying, 'event_reminder'::character varying, 'membership_expiry'::character varying, 'payment_due'::character varying, 'club_announcement'::character varying, 'handicap_updated'::character varying, 'spectator_invite'::character varying])::text[])))
);


--
-- Name: plan_features; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plan_features (
    id integer NOT NULL,
    plan_id integer,
    feature_key character varying(100) NOT NULL,
    is_enabled boolean DEFAULT true
);


--
-- Name: plan_features_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plan_features_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plan_features_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plan_features_id_seq OWNED BY public.plan_features.id;


--
-- Name: player_badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_badges (
    id integer NOT NULL,
    user_id uuid,
    badge_id integer,
    round_id uuid,
    earned_at timestamp with time zone DEFAULT now()
);


--
-- Name: player_badges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: player_badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_badges_id_seq OWNED BY public.player_badges.id;


--
-- Name: player_hole_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_hole_stats (
    id integer NOT NULL,
    user_id uuid,
    course_id uuid,
    hole_number integer NOT NULL,
    times_played integer DEFAULT 0,
    avg_score numeric(4,2),
    avg_putts numeric(4,2),
    best_score integer,
    worst_score integer,
    birdies integer DEFAULT 0,
    pars integer DEFAULT 0,
    bogeys integer DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: player_hole_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_hole_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: player_hole_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_hole_stats_id_seq OWNED BY public.player_hole_stats.id;


--
-- Name: player_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_stats (
    id integer NOT NULL,
    user_id uuid,
    total_rounds integer DEFAULT 0,
    total_holes integer DEFAULT 0,
    avg_score numeric(5,2),
    avg_putts_per_round numeric(4,2),
    avg_putts_per_hole numeric(4,2),
    fairways_hit_pct numeric(5,2),
    gir_pct numeric(5,2),
    total_eagles integer DEFAULT 0,
    total_birdies integer DEFAULT 0,
    total_pars integer DEFAULT 0,
    total_bogeys integer DEFAULT 0,
    total_double_bogeys integer DEFAULT 0,
    total_worse integer DEFAULT 0,
    total_hole_in_ones integer DEFAULT 0,
    total_three_putts integer DEFAULT 0,
    best_score_18 integer,
    best_score_9 integer,
    best_differential numeric(5,2),
    total_bet_won numeric(12,2) DEFAULT 0,
    total_bet_lost numeric(12,2) DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: player_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: player_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_stats_id_seq OWNED BY public.player_stats.id;


--
-- Name: post_comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.post_comments (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    post_id uuid,
    author_id uuid,
    parent_id uuid,
    content text NOT NULL,
    is_deleted boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: post_media; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.post_media (
    id integer NOT NULL,
    post_id uuid,
    media_type character varying(10),
    url character varying(500) NOT NULL,
    thumbnail_url character varying(500),
    order_index integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT post_media_media_type_check CHECK (((media_type)::text = ANY ((ARRAY['image'::character varying, 'video'::character varying])::text[])))
);


--
-- Name: post_media_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.post_media_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: post_media_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.post_media_id_seq OWNED BY public.post_media.id;


--
-- Name: posts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.posts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    author_id uuid,
    club_id uuid,
    group_id uuid,
    round_id uuid,
    content text,
    post_type character varying(30) DEFAULT 'regular'::character varying,
    visibility character varying(20) DEFAULT 'group'::character varying,
    comments_count integer DEFAULT 0,
    reactions_count integer DEFAULT 0,
    is_pinned boolean DEFAULT false,
    is_deleted boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT posts_post_type_check CHECK (((post_type)::text = ANY ((ARRAY['regular'::character varying, 'score_share'::character varying, 'achievement'::character varying, 'round_summary'::character varying, 'club_announcement'::character varying, 'event_announcement'::character varying])::text[]))),
    CONSTRAINT posts_visibility_check CHECK (((visibility)::text = ANY ((ARRAY['public'::character varying, 'club'::character varying, 'group'::character varying, 'friends'::character varying])::text[])))
);


--
-- Name: push_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.push_tokens (
    id integer NOT NULL,
    user_id uuid,
    token character varying(500) NOT NULL,
    platform character varying(20),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT push_tokens_platform_check CHECK (((platform)::text = ANY ((ARRAY['ios'::character varying, 'android'::character varying, 'web'::character varying])::text[])))
);


--
-- Name: push_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.push_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: push_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.push_tokens_id_seq OWNED BY public.push_tokens.id;


--
-- Name: reactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reactions (
    id integer NOT NULL,
    user_id uuid,
    target_type character varying(20),
    target_id uuid NOT NULL,
    reaction_type character varying(20),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT reactions_reaction_type_check CHECK (((reaction_type)::text = ANY ((ARRAY['like'::character varying, 'fire'::character varying, 'clap'::character varying, 'laugh'::character varying, 'sad'::character varying])::text[]))),
    CONSTRAINT reactions_target_type_check CHECK (((target_type)::text = ANY ((ARRAY['post'::character varying, 'score'::character varying, 'comment'::character varying])::text[])))
);


--
-- Name: reactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reactions_id_seq OWNED BY public.reactions.id;


--
-- Name: round_bet_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.round_bet_config (
    id integer NOT NULL,
    round_id uuid,
    entry_fee numeric(10,2) DEFAULT 0,
    nassau_enabled boolean DEFAULT false,
    nassau_front9 numeric(10,2) DEFAULT 0,
    nassau_back9 numeric(10,2) DEFAULT 0,
    nassau_total numeric(10,2) DEFAULT 0,
    per_hole_bet numeric(10,2) DEFAULT 0,
    point_value numeric(10,2) DEFAULT 0,
    pressers_enabled boolean DEFAULT false,
    presser_amount numeric(10,2) DEFAULT 0,
    birdie_prize numeric(10,2) DEFAULT 0,
    eagle_prize numeric(10,2) DEFAULT 0,
    albatross_prize numeric(10,2) DEFAULT 0,
    hole_in_one_prize numeric(10,2) DEFAULT 0,
    three_putt_penalty numeric(10,2) DEFAULT 0,
    oyes_enabled boolean DEFAULT false,
    oyes_prize numeric(10,2) DEFAULT 0,
    oyes_accumulates boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    skins_enabled boolean DEFAULT false,
    skins_value numeric(10,2) DEFAULT 0,
    skins_use_net boolean DEFAULT false
);


--
-- Name: round_bet_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.round_bet_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: round_bet_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.round_bet_config_id_seq OWNED BY public.round_bet_config.id;


--
-- Name: round_player_balance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.round_player_balance (
    id integer NOT NULL,
    round_id uuid,
    user_id uuid,
    entry_fee numeric(10,2) DEFAULT 0,
    nassau_balance numeric(10,2) DEFAULT 0,
    skins_balance numeric(10,2) DEFAULT 0,
    birds_earned numeric(10,2) DEFAULT 0,
    three_putt_loss numeric(10,2) DEFAULT 0,
    oyes_balance numeric(10,2) DEFAULT 0,
    other_balance numeric(10,2) DEFAULT 0,
    total_balance numeric(10,2) DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: round_player_balance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.round_player_balance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: round_player_balance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.round_player_balance_id_seq OWNED BY public.round_player_balance.id;


--
-- Name: round_players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.round_players (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    round_id uuid,
    user_id uuid,
    team_number integer,
    tee_order integer,
    handicap_index numeric(4,1),
    course_handicap integer,
    status character varying(20) DEFAULT 'invited'::character varying,
    is_guest boolean DEFAULT false,
    confirmed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    tee_color character varying(10),
    in_bet boolean DEFAULT true,
    match_order integer,
    tee_group integer,
    starting_hole integer,
    participant_mode character varying(20) DEFAULT 'playing'::character varying,
    withdrawn_at timestamp with time zone,
    withdrawn_reason character varying(200),
    is_group_scorer boolean DEFAULT false NOT NULL,
    score_validated_at timestamp with time zone,
    CONSTRAINT round_players_participant_mode_check CHECK (((participant_mode)::text = ANY (ARRAY['playing'::text, 'observer'::text]))),
    CONSTRAINT round_players_status_check CHECK (((status)::text = ANY (ARRAY['invited'::text, 'confirmed'::text, 'declined'::text, 'no_show'::text, 'playing'::text, 'finished'::text, 'withdrawn'::text])))
);


--
-- Name: round_spectators; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.round_spectators (
    id integer NOT NULL,
    round_id uuid,
    user_id uuid,
    joined_at timestamp with time zone DEFAULT now(),
    left_at timestamp with time zone
);


--
-- Name: round_spectators_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.round_spectators_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: round_spectators_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.round_spectators_id_seq OWNED BY public.round_spectators.id;


--
-- Name: round_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.round_teams (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    round_id uuid NOT NULL,
    team_number integer NOT NULL,
    name character varying(50) NOT NULL,
    color character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: rounds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rounds (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    club_id uuid,
    group_id uuid,
    course_id uuid,
    created_by uuid,
    name character varying(200),
    game_format character varying(30) NOT NULL,
    team_size integer DEFAULT 1,
    scoring_type character varying(20) DEFAULT 'gross'::character varying,
    scheduled_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    status character varying(20) DEFAULT 'scheduled'::character varying,
    holes_to_play integer DEFAULT 18,
    weather_temp numeric(4,1),
    weather_wind numeric(4,1),
    weather_conditions character varying(100),
    notes text,
    is_handicap_valid boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    invite_code character varying(12),
    teams_published boolean DEFAULT false,
    max_handicap integer,
    CONSTRAINT rounds_game_format_check CHECK (((game_format)::text = ANY ((ARRAY['stroke'::character varying, 'stableford'::character varying, 'stableford_modified'::character varying, 'match'::character varying, 'skins'::character varying, 'florida'::character varying, 'scramble'::character varying, 'best_ball'::character varying])::text[]))),
    CONSTRAINT rounds_holes_to_play_check CHECK ((holes_to_play = ANY (ARRAY[9, 18]))),
    CONSTRAINT rounds_scoring_type_check CHECK (((scoring_type)::text = ANY ((ARRAY['gross'::character varying, 'net'::character varying])::text[]))),
    CONSTRAINT rounds_status_check CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'active'::character varying, 'finished'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: score_differentials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.score_differentials (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    round_id uuid,
    course_id uuid,
    adjusted_gross_score integer NOT NULL,
    course_rating numeric(4,1) NOT NULL,
    slope_rating integer NOT NULL,
    differential numeric(5,2) NOT NULL,
    pcc_adjustment numeric(4,2) DEFAULT 0,
    exceptional_reduction numeric(4,2) DEFAULT 0,
    is_nine_hole boolean DEFAULT false,
    expected_score_adjustment numeric(4,2) DEFAULT 0,
    is_counting boolean DEFAULT true,
    played_at date NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scores (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    round_id uuid,
    user_id uuid,
    hole_number integer NOT NULL,
    gross_score integer,
    net_score integer,
    putts integer,
    played_shot boolean DEFAULT true,
    stableford_points integer,
    is_birdie boolean DEFAULT false,
    is_eagle boolean DEFAULT false,
    is_albatross boolean DEFAULT false,
    is_hole_in_one boolean DEFAULT false,
    is_bogey boolean DEFAULT false,
    is_double_bogey boolean DEFAULT false,
    is_three_putt boolean DEFAULT false,
    oye_distance_cm integer,
    oye_winner boolean DEFAULT false,
    shot_latitude numeric(10,8),
    shot_longitude numeric(11,8),
    notes character varying(500),
    recorded_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    entered_by uuid,
    conflict_score integer,
    conflict_entered_by uuid,
    has_conflict boolean DEFAULT false,
    CONSTRAINT scores_hole_number_check CHECK (((hole_number >= 1) AND (hole_number <= 18)))
);


--
-- Name: subscription_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_plans (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    plan_type character varying(20) NOT NULL,
    price_monthly numeric(10,2) DEFAULT 0,
    price_yearly numeric(10,2) DEFAULT 0,
    max_members integer,
    max_courses integer,
    max_groups integer,
    max_rounds_history integer,
    features jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT subscription_plans_plan_type_check CHECK (((plan_type)::text = ANY ((ARRAY['player'::character varying, 'club'::character varying])::text[])))
);


--
-- Name: subscription_plans_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.subscription_plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subscription_plans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.subscription_plans_id_seq OWNED BY public.subscription_plans.id;


--
-- Name: tee_time_booking_players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tee_time_booking_players (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    booking_id uuid NOT NULL,
    player_type character varying(20) NOT NULL,
    user_id uuid,
    guest_name character varying(200),
    guest_email character varying(255),
    sponsor_id uuid,
    fee_amount numeric(10,2) DEFAULT 0 NOT NULL,
    added_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT tee_time_booking_players_player_type_check CHECK (((player_type)::text = ANY ((ARRAY['member'::character varying, 'guest'::character varying, 'public'::character varying])::text[])))
);


--
-- Name: tee_time_bookings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tee_time_bookings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    slot_id integer,
    user_id uuid,
    players_count integer DEFAULT 1,
    status character varying(20) DEFAULT 'pending'::character varying,
    notes text,
    booked_at timestamp with time zone DEFAULT now(),
    confirmed_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    reminder_24h_sent boolean DEFAULT false NOT NULL,
    reminder_1h_sent boolean DEFAULT false NOT NULL,
    CONSTRAINT tee_time_bookings_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'confirmed'::character varying, 'cancelled'::character varying, 'no_show'::character varying])::text[])))
);


--
-- Name: tee_time_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tee_time_slots (
    id integer NOT NULL,
    course_id uuid,
    date date NOT NULL,
    "time" time without time zone NOT NULL,
    max_players integer DEFAULT 4,
    available_spots integer DEFAULT 4,
    is_blocked boolean DEFAULT false,
    block_reason character varying(200),
    created_at timestamp with time zone DEFAULT now(),
    club_id uuid,
    tier character varying(20) DEFAULT 'members_only'::character varying NOT NULL,
    green_fee_member numeric(10,2) DEFAULT 0 NOT NULL,
    green_fee_guest numeric(10,2) DEFAULT 0 NOT NULL,
    green_fee_public numeric(10,2) DEFAULT 0 NOT NULL,
    CONSTRAINT tee_time_slots_tier_check CHECK (((tier)::text = ANY ((ARRAY['members_only'::character varying, 'members_priority'::character varying, 'public'::character varying])::text[])))
);


--
-- Name: tee_time_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tee_time_slots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tee_time_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tee_time_slots_id_seq OWNED BY public.tee_time_slots.id;


--
-- Name: telegram_link_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.telegram_link_tokens (
    token character varying(40) NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    used_at timestamp with time zone
);


--
-- Name: user_follows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_follows (
    id integer NOT NULL,
    follower_id uuid,
    following_id uuid,
    status character varying(20) DEFAULT 'active'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_follows_check CHECK ((follower_id <> following_id)),
    CONSTRAINT user_follows_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'blocked'::character varying])::text[])))
);


--
-- Name: user_follows_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_follows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_follows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_follows_id_seq OWNED BY public.user_follows.id;


--
-- Name: user_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_subscriptions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    plan_id integer,
    status character varying(20),
    stripe_sub_id character varying(200),
    trial_ends_at timestamp with time zone,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    cancelled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_subscriptions_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'cancelled'::character varying, 'expired'::character varying, 'trial'::character varying, 'past_due'::character varying])::text[])))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email character varying(255) NOT NULL,
    phone character varying(30),
    password_hash character varying(255) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    username character varying(50) NOT NULL,
    avatar_url character varying(500),
    gender character varying(10),
    birthdate date,
    country character varying(100),
    city character varying(100),
    initial_handicap numeric(4,1),
    handicap_index numeric(4,1),
    handicap_last_updated timestamp with time zone,
    handicap_rounds_count integer DEFAULT 0,
    plan_id integer,
    plan_expires_at timestamp with time zone,
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    email_verified boolean DEFAULT false,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    is_lifetime_member boolean DEFAULT false,
    founder_member_at timestamp with time zone,
    is_superadmin boolean DEFAULT false,
    notify_email boolean DEFAULT true NOT NULL,
    notify_inapp boolean DEFAULT true NOT NULL,
    telegram_chat_id character varying(50),
    telegram_username character varying(100),
    notify_telegram boolean DEFAULT true NOT NULL,
    CONSTRAINT users_gender_check CHECK (((gender)::text = ANY ((ARRAY['male'::character varying, 'female'::character varying, 'other'::character varying])::text[])))
);


--
-- Name: badges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges ALTER COLUMN id SET DEFAULT nextval('public.badges_id_seq'::regclass);


--
-- Name: club_staff id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_staff ALTER COLUMN id SET DEFAULT nextval('public.club_staff_id_seq'::regclass);


--
-- Name: course_holes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_holes ALTER COLUMN id SET DEFAULT nextval('public.course_holes_id_seq'::regclass);


--
-- Name: group_members id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members ALTER COLUMN id SET DEFAULT nextval('public.group_members_id_seq'::regclass);


--
-- Name: handicap_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.handicap_history ALTER COLUMN id SET DEFAULT nextval('public.handicap_history_id_seq'::regclass);


--
-- Name: hole_bet_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hole_bet_results ALTER COLUMN id SET DEFAULT nextval('public.hole_bet_results_id_seq'::regclass);


--
-- Name: membership_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership_types ALTER COLUMN id SET DEFAULT nextval('public.membership_types_id_seq'::regclass);


--
-- Name: plan_features id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plan_features ALTER COLUMN id SET DEFAULT nextval('public.plan_features_id_seq'::regclass);


--
-- Name: player_badges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_badges ALTER COLUMN id SET DEFAULT nextval('public.player_badges_id_seq'::regclass);


--
-- Name: player_hole_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_hole_stats ALTER COLUMN id SET DEFAULT nextval('public.player_hole_stats_id_seq'::regclass);


--
-- Name: player_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_stats ALTER COLUMN id SET DEFAULT nextval('public.player_stats_id_seq'::regclass);


--
-- Name: post_media id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.post_media ALTER COLUMN id SET DEFAULT nextval('public.post_media_id_seq'::regclass);


--
-- Name: push_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_tokens ALTER COLUMN id SET DEFAULT nextval('public.push_tokens_id_seq'::regclass);


--
-- Name: reactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reactions ALTER COLUMN id SET DEFAULT nextval('public.reactions_id_seq'::regclass);


--
-- Name: round_bet_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_bet_config ALTER COLUMN id SET DEFAULT nextval('public.round_bet_config_id_seq'::regclass);


--
-- Name: round_player_balance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_player_balance ALTER COLUMN id SET DEFAULT nextval('public.round_player_balance_id_seq'::regclass);


--
-- Name: round_spectators id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_spectators ALTER COLUMN id SET DEFAULT nextval('public.round_spectators_id_seq'::regclass);


--
-- Name: subscription_plans id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans ALTER COLUMN id SET DEFAULT nextval('public.subscription_plans_id_seq'::regclass);


--
-- Name: tee_time_slots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_slots ALTER COLUMN id SET DEFAULT nextval('public.tee_time_slots_id_seq'::regclass);


--
-- Name: user_follows id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_follows ALTER COLUMN id SET DEFAULT nextval('public.user_follows_id_seq'::regclass);


--
-- Name: account_transactions account_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_transactions
    ADD CONSTRAINT account_transactions_pkey PRIMARY KEY (id);


--
-- Name: badges badges_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_code_key UNIQUE (code);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (id);


--
-- Name: club_events club_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_events
    ADD CONSTRAINT club_events_pkey PRIMARY KEY (id);


--
-- Name: club_members club_members_club_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_members
    ADD CONSTRAINT club_members_club_id_user_id_key UNIQUE (club_id, user_id);


--
-- Name: club_members club_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_members
    ADD CONSTRAINT club_members_pkey PRIMARY KEY (id);


--
-- Name: club_staff club_staff_club_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_staff
    ADD CONSTRAINT club_staff_club_id_user_id_key UNIQUE (club_id, user_id);


--
-- Name: club_staff club_staff_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_staff
    ADD CONSTRAINT club_staff_pkey PRIMARY KEY (id);


--
-- Name: club_subscriptions club_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_subscriptions
    ADD CONSTRAINT club_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: clubs clubs_invite_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_invite_code_key UNIQUE (invite_code);


--
-- Name: clubs clubs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_pkey PRIMARY KEY (id);


--
-- Name: clubs clubs_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_slug_key UNIQUE (slug);


--
-- Name: course_holes course_holes_course_id_hole_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_holes
    ADD CONSTRAINT course_holes_course_id_hole_number_key UNIQUE (course_id, hole_number);


--
-- Name: course_holes course_holes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_holes
    ADD CONSTRAINT course_holes_pkey PRIMARY KEY (id);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: event_registrations event_registrations_event_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registrations
    ADD CONSTRAINT event_registrations_event_id_user_id_key UNIQUE (event_id, user_id);


--
-- Name: event_registrations event_registrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registrations
    ADD CONSTRAINT event_registrations_pkey PRIMARY KEY (id);


--
-- Name: group_members group_members_group_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_user_id_key UNIQUE (group_id, user_id);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: groups groups_invite_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_invite_code_key UNIQUE (invite_code);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: handicap_history handicap_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.handicap_history
    ADD CONSTRAINT handicap_history_pkey PRIMARY KEY (id);


--
-- Name: hole_bet_results hole_bet_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hole_bet_results
    ADD CONSTRAINT hole_bet_results_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: member_accounts member_accounts_club_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_accounts
    ADD CONSTRAINT member_accounts_club_id_user_id_key UNIQUE (club_id, user_id);


--
-- Name: member_accounts member_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_accounts
    ADD CONSTRAINT member_accounts_pkey PRIMARY KEY (id);


--
-- Name: membership_types membership_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership_types
    ADD CONSTRAINT membership_types_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: plan_features plan_features_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plan_features
    ADD CONSTRAINT plan_features_pkey PRIMARY KEY (id);


--
-- Name: plan_features plan_features_plan_id_feature_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plan_features
    ADD CONSTRAINT plan_features_plan_id_feature_key_key UNIQUE (plan_id, feature_key);


--
-- Name: player_badges player_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_badges
    ADD CONSTRAINT player_badges_pkey PRIMARY KEY (id);


--
-- Name: player_badges player_badges_user_id_badge_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_badges
    ADD CONSTRAINT player_badges_user_id_badge_id_key UNIQUE (user_id, badge_id);


--
-- Name: player_hole_stats player_hole_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_hole_stats
    ADD CONSTRAINT player_hole_stats_pkey PRIMARY KEY (id);


--
-- Name: player_hole_stats player_hole_stats_user_id_course_id_hole_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_hole_stats
    ADD CONSTRAINT player_hole_stats_user_id_course_id_hole_number_key UNIQUE (user_id, course_id, hole_number);


--
-- Name: player_stats player_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_pkey PRIMARY KEY (id);


--
-- Name: player_stats player_stats_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_user_id_key UNIQUE (user_id);


--
-- Name: post_comments post_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.post_comments
    ADD CONSTRAINT post_comments_pkey PRIMARY KEY (id);


--
-- Name: post_media post_media_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.post_media
    ADD CONSTRAINT post_media_pkey PRIMARY KEY (id);


--
-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


--
-- Name: push_tokens push_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_tokens
    ADD CONSTRAINT push_tokens_pkey PRIMARY KEY (id);


--
-- Name: push_tokens push_tokens_user_id_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_tokens
    ADD CONSTRAINT push_tokens_user_id_token_key UNIQUE (user_id, token);


--
-- Name: reactions reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_pkey PRIMARY KEY (id);


--
-- Name: reactions reactions_user_id_target_type_target_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_user_id_target_type_target_id_key UNIQUE (user_id, target_type, target_id);


--
-- Name: round_bet_config round_bet_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_bet_config
    ADD CONSTRAINT round_bet_config_pkey PRIMARY KEY (id);


--
-- Name: round_bet_config round_bet_config_round_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_bet_config
    ADD CONSTRAINT round_bet_config_round_id_key UNIQUE (round_id);


--
-- Name: round_player_balance round_player_balance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_player_balance
    ADD CONSTRAINT round_player_balance_pkey PRIMARY KEY (id);


--
-- Name: round_player_balance round_player_balance_round_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_player_balance
    ADD CONSTRAINT round_player_balance_round_id_user_id_key UNIQUE (round_id, user_id);


--
-- Name: round_players round_players_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_players
    ADD CONSTRAINT round_players_pkey PRIMARY KEY (id);


--
-- Name: round_players round_players_round_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_players
    ADD CONSTRAINT round_players_round_id_user_id_key UNIQUE (round_id, user_id);


--
-- Name: round_spectators round_spectators_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_spectators
    ADD CONSTRAINT round_spectators_pkey PRIMARY KEY (id);


--
-- Name: round_spectators round_spectators_round_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_spectators
    ADD CONSTRAINT round_spectators_round_id_user_id_key UNIQUE (round_id, user_id);


--
-- Name: round_teams round_teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_teams
    ADD CONSTRAINT round_teams_pkey PRIMARY KEY (id);


--
-- Name: round_teams round_teams_round_id_team_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_teams
    ADD CONSTRAINT round_teams_round_id_team_number_key UNIQUE (round_id, team_number);


--
-- Name: rounds rounds_invite_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rounds
    ADD CONSTRAINT rounds_invite_code_key UNIQUE (invite_code);


--
-- Name: rounds rounds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rounds
    ADD CONSTRAINT rounds_pkey PRIMARY KEY (id);


--
-- Name: score_differentials score_differentials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_differentials
    ADD CONSTRAINT score_differentials_pkey PRIMARY KEY (id);


--
-- Name: scores scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pkey PRIMARY KEY (id);


--
-- Name: scores scores_round_id_user_id_hole_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_round_id_user_id_hole_number_key UNIQUE (round_id, user_id, hole_number);


--
-- Name: subscription_plans subscription_plans_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_code_key UNIQUE (code);


--
-- Name: subscription_plans subscription_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id);


--
-- Name: tee_time_booking_players tee_time_booking_players_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_booking_players
    ADD CONSTRAINT tee_time_booking_players_pkey PRIMARY KEY (id);


--
-- Name: tee_time_bookings tee_time_bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_bookings
    ADD CONSTRAINT tee_time_bookings_pkey PRIMARY KEY (id);


--
-- Name: tee_time_slots tee_time_slots_club_date_time_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_slots
    ADD CONSTRAINT tee_time_slots_club_date_time_key UNIQUE (club_id, date, "time");


--
-- Name: tee_time_slots tee_time_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_slots
    ADD CONSTRAINT tee_time_slots_pkey PRIMARY KEY (id);


--
-- Name: telegram_link_tokens telegram_link_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_link_tokens
    ADD CONSTRAINT telegram_link_tokens_pkey PRIMARY KEY (token);


--
-- Name: user_follows user_follows_follower_id_following_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_follows
    ADD CONSTRAINT user_follows_follower_id_following_id_key UNIQUE (follower_id, following_id);


--
-- Name: user_follows user_follows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_follows
    ADD CONSTRAINT user_follows_pkey PRIMARY KEY (id);


--
-- Name: user_subscriptions user_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_subscriptions
    ADD CONSTRAINT user_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_balance_round; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_balance_round ON public.round_player_balance USING btree (round_id);


--
-- Name: idx_booking_players_booking; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_booking_players_booking ON public.tee_time_booking_players USING btree (booking_id);


--
-- Name: idx_booking_players_sponsor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_booking_players_sponsor ON public.tee_time_booking_players USING btree (sponsor_id) WHERE (sponsor_id IS NOT NULL);


--
-- Name: idx_booking_players_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_booking_players_user ON public.tee_time_booking_players USING btree (user_id) WHERE (user_id IS NOT NULL);


--
-- Name: idx_differentials_played; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_differentials_played ON public.score_differentials USING btree (user_id, played_at DESC);


--
-- Name: idx_differentials_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_differentials_user ON public.score_differentials USING btree (user_id);


--
-- Name: idx_follows_follower; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_follows_follower ON public.user_follows USING btree (follower_id);


--
-- Name: idx_follows_following; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_follows_following ON public.user_follows USING btree (following_id);


--
-- Name: idx_notifications_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_user ON public.notifications USING btree (user_id, is_read, created_at DESC);


--
-- Name: idx_posts_club; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_posts_club ON public.posts USING btree (club_id);


--
-- Name: idx_posts_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_posts_created ON public.posts USING btree (created_at DESC);


--
-- Name: idx_posts_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_posts_group ON public.posts USING btree (group_id);


--
-- Name: idx_rounds_club; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rounds_club ON public.rounds USING btree (club_id);


--
-- Name: idx_rounds_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rounds_group ON public.rounds USING btree (group_id);


--
-- Name: idx_rounds_scheduled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rounds_scheduled ON public.rounds USING btree (scheduled_at);


--
-- Name: idx_rounds_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rounds_status ON public.rounds USING btree (status);


--
-- Name: idx_scores_round; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scores_round ON public.scores USING btree (round_id);


--
-- Name: idx_scores_round_hole; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scores_round_hole ON public.scores USING btree (round_id, hole_number);


--
-- Name: idx_scores_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scores_user ON public.scores USING btree (user_id);


--
-- Name: idx_tee_time_slots_club_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tee_time_slots_club_date ON public.tee_time_slots USING btree (club_id, date);


--
-- Name: idx_telegram_tokens_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_telegram_tokens_user ON public.telegram_link_tokens USING btree (user_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_telegram_chat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_telegram_chat ON public.users USING btree (telegram_chat_id) WHERE (telegram_chat_id IS NOT NULL);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- Name: uq_round_tee_group_scorer; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_round_tee_group_scorer ON public.round_players USING btree (round_id, tee_group) WHERE (is_group_scorer = true);


--
-- Name: account_transactions account_transactions_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_transactions
    ADD CONSTRAINT account_transactions_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.member_accounts(id);


--
-- Name: account_transactions account_transactions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_transactions
    ADD CONSTRAINT account_transactions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: club_events club_events_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_events
    ADD CONSTRAINT club_events_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- Name: club_events club_events_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_events
    ADD CONSTRAINT club_events_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: club_members club_members_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_members
    ADD CONSTRAINT club_members_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- Name: club_members club_members_membership_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_members
    ADD CONSTRAINT club_members_membership_type_id_fkey FOREIGN KEY (membership_type_id) REFERENCES public.membership_types(id);


--
-- Name: club_members club_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_members
    ADD CONSTRAINT club_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: club_staff club_staff_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_staff
    ADD CONSTRAINT club_staff_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- Name: club_staff club_staff_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_staff
    ADD CONSTRAINT club_staff_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: club_subscriptions club_subscriptions_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_subscriptions
    ADD CONSTRAINT club_subscriptions_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: club_subscriptions club_subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.club_subscriptions
    ADD CONSTRAINT club_subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: clubs clubs_default_membership_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_default_membership_type_id_fkey FOREIGN KEY (default_membership_type_id) REFERENCES public.membership_types(id) ON DELETE SET NULL;


--
-- Name: clubs clubs_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: course_holes course_holes_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_holes
    ADD CONSTRAINT course_holes_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: courses courses_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE SET NULL;


--
-- Name: courses courses_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: event_registrations event_registrations_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registrations
    ADD CONSTRAINT event_registrations_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.club_events(id) ON DELETE CASCADE;


--
-- Name: event_registrations event_registrations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registrations
    ADD CONSTRAINT event_registrations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: groups groups_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE SET NULL;


--
-- Name: groups groups_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: handicap_history handicap_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.handicap_history
    ADD CONSTRAINT handicap_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: hole_bet_results hole_bet_results_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hole_bet_results
    ADD CONSTRAINT hole_bet_results_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE CASCADE;


--
-- Name: hole_bet_results hole_bet_results_winner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hole_bet_results
    ADD CONSTRAINT hole_bet_results_winner_user_id_fkey FOREIGN KEY (winner_user_id) REFERENCES public.users(id);


--
-- Name: invoices invoices_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: invoices invoices_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: member_accounts member_accounts_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_accounts
    ADD CONSTRAINT member_accounts_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id);


--
-- Name: member_accounts member_accounts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_accounts
    ADD CONSTRAINT member_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: membership_types membership_types_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership_types
    ADD CONSTRAINT membership_types_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: plan_features plan_features_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plan_features
    ADD CONSTRAINT plan_features_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: player_badges player_badges_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_badges
    ADD CONSTRAINT player_badges_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(id);


--
-- Name: player_badges player_badges_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_badges
    ADD CONSTRAINT player_badges_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE SET NULL;


--
-- Name: player_badges player_badges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_badges
    ADD CONSTRAINT player_badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: player_hole_stats player_hole_stats_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_hole_stats
    ADD CONSTRAINT player_hole_stats_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: player_hole_stats player_hole_stats_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_hole_stats
    ADD CONSTRAINT player_hole_stats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: player_stats player_stats_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: post_comments post_comments_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.post_comments
    ADD CONSTRAINT post_comments_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: post_comments post_comments_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.post_comments
    ADD CONSTRAINT post_comments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.post_comments(id) ON DELETE SET NULL;


--
-- Name: post_comments post_comments_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.post_comments
    ADD CONSTRAINT post_comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;


--
-- Name: post_media post_media_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.post_media
    ADD CONSTRAINT post_media_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;


--
-- Name: posts posts_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: posts posts_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- Name: posts posts_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: posts posts_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE SET NULL;


--
-- Name: push_tokens push_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_tokens
    ADD CONSTRAINT push_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: reactions reactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: round_bet_config round_bet_config_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_bet_config
    ADD CONSTRAINT round_bet_config_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE CASCADE;


--
-- Name: round_player_balance round_player_balance_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_player_balance
    ADD CONSTRAINT round_player_balance_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE CASCADE;


--
-- Name: round_player_balance round_player_balance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_player_balance
    ADD CONSTRAINT round_player_balance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: round_players round_players_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_players
    ADD CONSTRAINT round_players_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE CASCADE;


--
-- Name: round_players round_players_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_players
    ADD CONSTRAINT round_players_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: round_spectators round_spectators_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_spectators
    ADD CONSTRAINT round_spectators_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE CASCADE;


--
-- Name: round_spectators round_spectators_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_spectators
    ADD CONSTRAINT round_spectators_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: round_teams round_teams_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.round_teams
    ADD CONSTRAINT round_teams_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE CASCADE;


--
-- Name: rounds rounds_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rounds
    ADD CONSTRAINT rounds_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE SET NULL;


--
-- Name: rounds rounds_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rounds
    ADD CONSTRAINT rounds_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: rounds rounds_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rounds
    ADD CONSTRAINT rounds_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: rounds rounds_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rounds
    ADD CONSTRAINT rounds_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE SET NULL;


--
-- Name: score_differentials score_differentials_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_differentials
    ADD CONSTRAINT score_differentials_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: score_differentials score_differentials_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_differentials
    ADD CONSTRAINT score_differentials_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE SET NULL;


--
-- Name: score_differentials score_differentials_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_differentials
    ADD CONSTRAINT score_differentials_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: scores scores_conflict_entered_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_conflict_entered_by_fkey FOREIGN KEY (conflict_entered_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: scores scores_entered_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_entered_by_fkey FOREIGN KEY (entered_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: scores scores_round_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_round_id_fkey FOREIGN KEY (round_id) REFERENCES public.rounds(id) ON DELETE CASCADE;


--
-- Name: scores scores_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tee_time_booking_players tee_time_booking_players_added_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_booking_players
    ADD CONSTRAINT tee_time_booking_players_added_by_fkey FOREIGN KEY (added_by) REFERENCES public.users(id);


--
-- Name: tee_time_booking_players tee_time_booking_players_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_booking_players
    ADD CONSTRAINT tee_time_booking_players_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.tee_time_bookings(id) ON DELETE CASCADE;


--
-- Name: tee_time_booking_players tee_time_booking_players_sponsor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_booking_players
    ADD CONSTRAINT tee_time_booking_players_sponsor_id_fkey FOREIGN KEY (sponsor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: tee_time_booking_players tee_time_booking_players_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_booking_players
    ADD CONSTRAINT tee_time_booking_players_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: tee_time_bookings tee_time_bookings_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_bookings
    ADD CONSTRAINT tee_time_bookings_slot_id_fkey FOREIGN KEY (slot_id) REFERENCES public.tee_time_slots(id);


--
-- Name: tee_time_bookings tee_time_bookings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_bookings
    ADD CONSTRAINT tee_time_bookings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: tee_time_slots tee_time_slots_club_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_slots
    ADD CONSTRAINT tee_time_slots_club_id_fkey FOREIGN KEY (club_id) REFERENCES public.clubs(id) ON DELETE CASCADE;


--
-- Name: tee_time_slots tee_time_slots_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tee_time_slots
    ADD CONSTRAINT tee_time_slots_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: telegram_link_tokens telegram_link_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_link_tokens
    ADD CONSTRAINT telegram_link_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_follows user_follows_follower_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_follows
    ADD CONSTRAINT user_follows_follower_id_fkey FOREIGN KEY (follower_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_follows user_follows_following_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_follows
    ADD CONSTRAINT user_follows_following_id_fkey FOREIGN KEY (following_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_subscriptions user_subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_subscriptions
    ADD CONSTRAINT user_subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: user_subscriptions user_subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_subscriptions
    ADD CONSTRAINT user_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- PostgreSQL database dump complete
--

\unrestrict FbebjyUdNUqYzhqstbUKSPxsv6hXgeudTt2jL8FJF5YW259Hr4JSfujhH6bJ0Q3


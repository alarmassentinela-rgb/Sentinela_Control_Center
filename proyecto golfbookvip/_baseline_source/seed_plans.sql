--
-- PostgreSQL database dump
--

\restrict 6d7j0t8pFp3eg6kOGasEvyfauHMckIjdy0ZJoQtdUoMVXXqmP2dCKg9ywBGGcal

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
-- Data for Name: subscription_plans; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.subscription_plans (id, code, name, plan_type, price_monthly, price_yearly, max_members, max_courses, max_groups, max_rounds_history, features, is_active, created_at) VALUES (1, 'free_player', 'Jugador Free', 'player', 0.00, 0.00, NULL, NULL, 1, 20, NULL, true, '2026-04-14 16:52:56.181365+00');
INSERT INTO public.subscription_plans (id, code, name, plan_type, price_monthly, price_yearly, max_members, max_courses, max_groups, max_rounds_history, features, is_active, created_at) VALUES (2, 'player_pro', 'Jugador Pro', 'player', 4.99, 49.90, NULL, NULL, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00');
INSERT INTO public.subscription_plans (id, code, name, plan_type, price_monthly, price_yearly, max_members, max_courses, max_groups, max_rounds_history, features, is_active, created_at) VALUES (3, 'free_club', 'Club Free', 'club', 0.00, 0.00, 30, 1, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00');
INSERT INTO public.subscription_plans (id, code, name, plan_type, price_monthly, price_yearly, max_members, max_courses, max_groups, max_rounds_history, features, is_active, created_at) VALUES (4, 'club_starter', 'Club Starter', 'club', 49.00, 490.00, 100, 2, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00');
INSERT INTO public.subscription_plans (id, code, name, plan_type, price_monthly, price_yearly, max_members, max_courses, max_groups, max_rounds_history, features, is_active, created_at) VALUES (5, 'club_pro', 'Club Pro', 'club', 149.00, 1490.00, 500, NULL, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00');
INSERT INTO public.subscription_plans (id, code, name, plan_type, price_monthly, price_yearly, max_members, max_courses, max_groups, max_rounds_history, features, is_active, created_at) VALUES (6, 'club_enterprise', 'Club Enterprise', 'club', 0.00, 0.00, NULL, NULL, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00');


--
-- Data for Name: plan_features; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: plan_features_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.plan_features_id_seq', 1, false);


--
-- Name: subscription_plans_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.subscription_plans_id_seq', 6, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 6d7j0t8pFp3eg6kOGasEvyfauHMckIjdy0ZJoQtdUoMVXXqmP2dCKg9ywBGGcal


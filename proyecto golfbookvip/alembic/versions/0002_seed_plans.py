"""seed subscription plans

Revision ID: 0002_seed_plans
Revises: 0001_baseline
Create Date: 2026-07-01
"""

from alembic import op


revision = "0002_seed_plans"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        INSERT INTO public.subscription_plans (
            id, code, name, plan_type, price_monthly, price_yearly,
            max_members, max_courses, max_groups, max_rounds_history,
            features, is_active, created_at
        ) VALUES
            (1, 'free_player', 'Jugador Free', 'player', 0.00, 0.00, NULL, NULL, 1, 20, NULL, true, '2026-04-14 16:52:56.181365+00'),
            (2, 'player_pro', 'Jugador Pro', 'player', 4.99, 49.90, NULL, NULL, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00'),
            (3, 'free_club', 'Club Free', 'club', 0.00, 0.00, 30, 1, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00'),
            (4, 'club_starter', 'Club Starter', 'club', 49.00, 490.00, 100, 2, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00'),
            (5, 'club_pro', 'Club Pro', 'club', 149.00, 1490.00, 500, NULL, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00'),
            (6, 'club_enterprise', 'Club Enterprise', 'club', 0.00, 0.00, NULL, NULL, NULL, NULL, NULL, true, '2026-04-14 16:52:56.181365+00')
        ON CONFLICT (code) DO NOTHING
        """
    )
    bind.exec_driver_sql("SELECT pg_catalog.setval('public.subscription_plans_id_seq', 6, true)")
    bind.exec_driver_sql("SELECT pg_catalog.setval('public.plan_features_id_seq', 1, false)")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        DELETE FROM public.subscription_plans
        WHERE code IN (
            'free_player',
            'player_pro',
            'free_club',
            'club_starter',
            'club_pro',
            'club_enterprise'
        )
        """
    )

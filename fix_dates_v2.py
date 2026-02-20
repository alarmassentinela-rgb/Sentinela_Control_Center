from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def run_fix(env):
    print("--- INICIANDO CORRECCIÓN DE FECHAS ---")
    
    # 1. Caso específico SUB-0227
    sub_227 = env['sentinela.subscription'].search([('name', '=', 'SUB-0227')], limit=1)
    if sub_227:
        sub_227.write({'current_period_end': '2026-03-14'})
        sub_227.action_recalculate_dates()
        print(f"SUB-0227 alineada: Fin {sub_227.current_period_end} -> Siguiente {sub_227.next_billing_date}")
    
    # 2. Todos los demás
    all_subs = env['sentinela.subscription'].search([('name', '!=', 'SUB-0227')])
    print(f"Procesando {len(all_subs)} suscripciones adicionales...")
    all_subs.action_recalculate_dates()
    
    env.cr.commit()
    print("--- PROCESO COMPLETADO ---")

if __name__ == "__main__":
    # Este bloque es para cuando se corre vía 'odoo shell < script.py'
    run_fix(env)

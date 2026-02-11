from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """
    Este hook se ejecuta después de instalar/actualizar el módulo.
    Su función es corregir la incompatibilidad de Odoo 18 donde 'tree' 
    debe ser reemplazado por 'list' en las acciones de ventana.
    """
    # Buscamos todas las acciones de ventana creadas por este módulo
    # que tengan 'tree' en su definición de modos de vista.
    # Usamos SQL directo para evitar validaciones del ORM que podrían fallar.
    
    env.cr.execute("""
        UPDATE ir_act_window 
        SET view_mode = REPLACE(view_mode, 'tree', 'list') 
        WHERE view_mode LIKE '%tree%' 
        AND id IN (
            SELECT res_id 
            FROM ir_model_data 
            WHERE module = 'sentinela_monitoring' 
            AND model = 'ir.actions.act_window'
        );
    """)
    
    # También forzar la corrección específica para la acción conflictiva conocida (589)
    # por si el link de ir_model_data se hubiera roto (defensa en profundidad).
    env.cr.execute("""
        UPDATE ir_act_window 
        SET view_mode = 'list,form' 
        WHERE id = 589 AND view_mode LIKE '%tree%';
    """)
    
    # Asegurar que las acciones de Kanban también usen list
    env.cr.execute("""
        UPDATE ir_act_window 
        SET view_mode = 'kanban,list,form' 
        WHERE view_mode LIKE '%kanban,tree,form%'
        AND id IN (
            SELECT res_id 
            FROM ir_model_data 
            WHERE module = 'sentinela_monitoring'
        );
    """)
    
    print("✅ [HOOK] Corrección de 'tree' -> 'list' aplicada exitosamente.")

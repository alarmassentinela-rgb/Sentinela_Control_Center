# Script para cargar las 2 plantillas base de Sentinela
try:
    # 1. Plantilla de Monitoreo
    mon_content = '''
        <div style="font-family: Arial, sans-serif;">
            <h1 style="text-align: center; color: #0056b3;">CONTRATO DE MONITOREO DE ALARMAS</h1>
            <p>CONTRATO QUE CELEBRAN POR UNA PARTE <b>SENTINELA</b> Y POR LA OTRA <b>{{ object.partner_id.name }}</b> (EL CLIENTE).</p>
            
            <h3>DETALLES DEL SERVICIO DE SEGURIDAD</h3>
            <table class="table table-bordered" style="width: 100%; border-collapse: collapse; border: 1px solid black;">
                <tr style="background-color: #f2f2f2;">
                    <td style="border: 1px solid black; padding: 8px;"><b>PLAN CONTRATADO:</b></td>
                    <td style="border: 1px solid black; padding: 8px;">{{ object.product_id.name }}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid black; padding: 8px;"><b>NÚMERO DE CUENTA:</b></td>
                    <td style="border: 1px solid black; padding: 8px;">{{ object.monitoring_account_number or 'PENDIENTE' }}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid black; padding: 8px;"><b>INVERSIÓN MENSUAL:</b></td>
                    <td style="border: 1px solid black; padding: 8px;">{{ object.price_total }} {{ object.currency_id.name }}</td>
                </tr>
            </table>

            <div class="page-break-before" style="page-break-before: always;"></div>
            <h2 style="text-align: center;">CLAUSULAS DE LIMITACION DE RESPONSABILIDAD</h2>
            <p style="text-align: justify;">
                SENTINELA se compromete a la recepción de señales de alarma 24/7... [EDITE ESTE TEXTO]
            </p>
        </div>
    '''
    
    # 2. Plantilla de Internet
    int_content = '''
        <div style="font-family: Arial, sans-serif;">
            <h1 style="text-align: center; color: #28a745;">CONTRATO DE INTERNET INALÁMBRICO (WISP)</h1>
            <p>CLIENTE: <b>{{ object.partner_id.name }}</b></p>
            <p>DOMICILIO DE INSTALACIÓN: {{ object.service_address_id.contact_address or object.partner_id.contact_address }}</p>
            
            <h3>ESPECIFICACIONES TÉCNICAS</h3>
            <ul>
                <li><b>PLAN:</b> {{ object.product_id.name }}</li>
                <li><b>USUARIO PPPoE:</b> {{ object.pppoe_user or 'N/A' }}</li>
                <li><b>IP ASIGNADA:</b> {{ object.ip_address or 'DINÁMICA' }}</li>
            </ul>

            <div class="page-break-before" style="page-break-before: always;"></div>
            <h2 style="text-align: center;">TÉRMINOS Y CONDICIONES DE INTERNET</h2>
            <p style="text-align: justify;">
                El servicio de internet está sujeto a disponibilidad técnica... [EDITE ESTE TEXTO]
            </p>
        </div>
    '''

    # Crear o actualizar
    Tmpl = env['sentinela.contract.template']
    
    t_mon = Tmpl.search([('name', '=', 'Plantilla de Monitoreo')], limit=1)
    if not t_mon:
        t_mon = Tmpl.create({'name': 'Plantilla de Monitoreo', 'content': mon_content})
    else:
        t_mon.write({'content': mon_content})

    t_int = Tmpl.search([('name', '=', 'Plantilla de Internet')], limit=1)
    if not t_int:
        t_int = Tmpl.create({'name': 'Plantilla de Internet', 'content': int_content})
    else:
        t_int.write({'content': int_content})

    # Vincular a productos por nombre/tipo (opcional, pero ayuda)
    env['product.template'].search([('is_subscription', '=', True), ('service_type', '=', 'alarm')]).write({'contract_template_id': t_mon.id})
    env['product.template'].search([('is_subscription', '=', True), ('service_type', '=', 'internet')]).write({'contract_template_id': t_int.id})

    print("EXITO: Plantillas cargadas y vinculadas.")
    env.cr.commit()

except Exception as e:
    print(f"ERROR: {str(e)}")

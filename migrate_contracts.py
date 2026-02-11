from odoo import api, SUPERUSER_ID

def migrate(env):
    # 1. Crear la plantilla con el texto base
    template_vals = {
        'name': 'Contrato Maestro de Monitoreo y Servicios',
        'content': '''
            <div style="font-family: Arial, sans-serif;">
                <h1 style="text-align: center;">CONTRATO DE PRESTACIÓN DE SERVICIOS</h1>
                <p>CONTRATO QUE CELEBRAN POR UNA PARTE <b>SENTINELA</b> Y POR LA OTRA <b>{{ object.partner_id.name }}</b> (EN LO SUCESIVO EL CLIENTE), CON DOMICILIO EN {{ object.service_address_id.contact_address or object.partner_id.contact_address }}.</p>
                
                <h3 style="margin-top: 20px;">RESUMEN DEL SERVICIO</h3>
                <table class="table table-bordered" style="width: 100%; border-collapse: collapse; border: 1px solid black; margin-bottom: 20px;">
                    <tr>
                        <td style="border: 1px solid black; padding: 10px; width: 30%;"><b>PLAN CONTRATADO:</b></td>
                        <td style="border: 1px solid black; padding: 10px;">{{ object.product_id.name }}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid black; padding: 10px;"><b>NÚMERO DE CUENTA:</b></td>
                        <td style="border: 1px solid black; padding: 10px;">{{ object.monitoring_account_number or 'N/A' }}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid black; padding: 10px;"><b>FECHA DE INICIO:</b></td>
                        <td style="border: 1px solid black; padding: 10px;">{{ object.start_date }}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid black; padding: 10px;"><b>INVERSIÓN MENSUAL:</b></td>
                        <td style="border: 1px solid black; padding: 10px;"><b>{{ object.price_total }} {{ object.currency_id.name }}</b></td>
                    </tr>
                </table>

                <p style="margin-top: 30px;">Las partes acuerdan que la prestación del servicio se regirá por las siguientes:</p>

                <div class="page-break-before"></div>
                <h2 style="text-align: center; color: #d9534f;">CLAUSULAS DE LIMITACION DE RESPONSABILIDAD</h2>
                <div style="text-align: justify; font-size: 12px;">
                    <p><b>PRIMERA.-</b> El sistema de monitoreo es un elemento disuasivo y de alerta temprana...</p>
                    <p><b>SEGUNDA.-</b> La empresa no se hace responsable por fallas en las líneas de comunicación del cliente...</p>
                    <p>(Usted puede editar este texto legal completo desde el menú Configuración > Plantillas de Contratos)</p>
                </div>
            </div>
        '''
    }
    template = env['sentinela.contract.template'].create(template_vals)

    # 2. Vincular todos los productos de suscripción a esta nueva plantilla
    products = env['product.template'].search([('is_subscription', '=', True)])
    products.write({'contract_template_id': template.id})
    print(f"EXITO: Se creó la plantilla y se vinculó a {len(products)} productos.")

if __name__ == '__main__':
    # Este script se corre dentro de odoo shell
    migrate(env)

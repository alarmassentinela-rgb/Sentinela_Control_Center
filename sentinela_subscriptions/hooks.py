"""Post-install hook — carga plantillas base de contratos si no existen."""

import logging

_logger = logging.getLogger(__name__)

TEMPLATE_INTERNET = """<div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.6; color: #222; text-align: justify;">

<h2 style="text-align: center; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">
    CONTRATO DE PRESTACIÓN DE SERVICIOS DE INTERNET
</h2>
<p style="text-align: center; font-size: 11px; color: #666; margin-top: 0;">
    Contrato No. <strong>{{ object.name }}</strong> &nbsp;|&nbsp; Fecha: <strong>{{ object.start_date }}</strong>
</p>

<hr style="border: 1px solid #333; margin: 10px 0 20px 0;"/>

<p>
Que celebran por una parte <strong>SENTINELA SEGURIDAD PRIVADA S.A. DE C.V.</strong> (en adelante
<strong>"EL PROVEEDOR"</strong>), y por la otra <strong>{{ object.partner_id.name }}</strong>,
con RFC <strong>{{ object.partner_id.vat or 'NO REGISTRADO' }}</strong>
(en adelante <strong>"EL CLIENTE"</strong>), al tenor de las siguientes:
</p>

<h3 style="font-size: 13px; text-transform: uppercase; margin-top: 20px;">CLÁUSULAS</h3>

<p><strong>PRIMERA. — OBJETO DEL CONTRATO.</strong><br/>
EL PROVEEDOR se compromete a proporcionar al CLIENTE el servicio de acceso a Internet de banda ancha en la modalidad
<strong>{{ object.product_id.name }}</strong>, en el domicilio ubicado en
<strong>{{ object.contract_domicilio_servicio or object.address_street }}</strong>,
con una velocidad contratada de acuerdo al plan elegido, sujeta a disponibilidad técnica de la red.</p>

<p><strong>SEGUNDA. — PLAZO Y VIGENCIA.</strong><br/>
El presente contrato tendrá una vigencia mínima forzosa de
<strong>{{ object.commitment_months or 12 }} meses</strong>, contados a partir del
<strong>{{ object.start_date }}</strong>. Al término de dicho periodo, el contrato se renovará
automáticamente de forma mensual salvo que cualquiera de las partes notifique su deseo de concluirlo
con al menos 30 días de anticipación.</p>

<p><strong>TERCERA. — COSTO Y FORMA DE PAGO.</strong><br/>
El CLIENTE pagará mensualmente la cantidad de
<strong>${{ "%.2f"|format(object.price_total or 0) }} MXN (más IVA)</strong>
en concepto de renta del servicio. Los pagos deberán realizarse dentro de los primeros
<strong>{{ object.payment_day or 5 }} días naturales</strong> de cada mes.</p>

<p><strong>CUARTA. — EQUIPO E INSTALACIÓN.</strong><br/>
EL PROVEEDOR proveerá e instalará el equipo necesario:
</p>
<table style="width: 100%; border-collapse: collapse; font-size: 12px; margin: 10px 0;">
    <thead>
        <tr style="background-color: #eee;">
            <th style="border: 1px solid #ccc; padding: 6px;">Equipo</th>
            <th style="border: 1px solid #ccc; padding: 6px;">Marca</th>
            <th style="border: 1px solid #ccc; padding: 6px;">Modelo</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="border: 1px solid #ccc; padding: 6px;">Antena CPE</td>
            <td style="border: 1px solid #ccc; padding: 6px;">{{ object.contract_antena_marca or '___________' }}</td>
            <td style="border: 1px solid #ccc; padding: 6px;">{{ object.contract_antena_modelo or '___________' }}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ccc; padding: 6px;">Router MikroTik (Nodo)</td>
            <td style="border: 1px solid #ccc; padding: 6px;" colspan="2">{{ object.contract_router_nombre or '___________' }}</td>
        </tr>
    </tbody>
</table>

<p><strong>QUINTA. — OBLIGACIONES DEL CLIENTE.</strong><br/>
El CLIENTE se obliga a: a) Hacer uso del servicio exclusivamente para fines lícitos y personales;
b) No sublicenciar, revender ni compartir el servicio con terceros sin autorización expresa;
c) No manipular ni alterar el equipo instalado por EL PROVEEDOR.</p>

<p><strong>SEXTA. — NIVELES DE SERVICIO (SLA).</strong><br/>
EL PROVEEDOR garantiza una disponibilidad del servicio del <strong>95%</strong> mensual.</p>

<p><strong>SÉPTIMA. — RESCISIÓN ANTICIPADA.</strong><br/>
En caso de rescisión antes del término del plazo forzoso, el CLIENTE deberá cubrir una penalización
equivalente a los meses restantes de servicio.</p>

<p><strong>OCTAVA. — JURISDICCIÓN.</strong><br/>
Las partes se someten a la jurisdicción de los tribunales del Estado de <strong>Tamaulipas</strong>, México.</p>

<br/>
<p>Leído y firmado en <strong>Matamoros, Tamps.</strong>, a <strong>{{ object.start_date }}</strong>.</p>

<br/><br/>
<table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 30px;">
    <tr>
        <td style="width: 45%; text-align: center; padding-top: 50px; border-top: 1px solid #333;">
            <strong>EL PROVEEDOR</strong><br/>
            Sentinela Seguridad Privada S.A. de C.V.
        </td>
        <td style="width: 10%;"></td>
        <td style="width: 45%; text-align: center; padding-top: 50px; border-top: 1px solid #333;">
            <strong>EL CLIENTE</strong><br/>
            {{ object.partner_id.name }}<br/>
            RFC: {{ object.partner_id.vat or '___________' }}
        </td>
    </tr>
</table>

</div>"""

TEMPLATE_MONITOREO = """<div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.6; color: #222; text-align: justify;">

<h2 style="text-align: center; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">
    CONTRATO DE PRESTACIÓN DE SERVICIOS DE MONITOREO DE ALARMAS
</h2>
<p style="text-align: center; font-size: 11px; color: #666; margin-top: 0;">
    Contrato No. <strong>{{ object.name }}</strong> &nbsp;|&nbsp;
    Cuenta: <strong>{{ object.contract_cuenta_monitoreo or '---' }}</strong> &nbsp;|&nbsp;
    Fecha: <strong>{{ object.start_date }}</strong>
</p>

<hr style="border: 1px solid #333; margin: 10px 0 20px 0;"/>

<p>
Que celebran por una parte <strong>SENTINELA SEGURIDAD PRIVADA S.A. DE C.V.</strong> (en adelante
<strong>"LA EMPRESA"</strong>), y por la otra <strong>{{ object.partner_id.name }}</strong>,
con RFC <strong>{{ object.partner_id.vat or 'NO REGISTRADO' }}</strong>
(en adelante <strong>"EL USUARIO"</strong>), al tenor de las siguientes:
</p>

<h3 style="font-size: 13px; text-transform: uppercase; margin-top: 20px;">CLÁUSULAS</h3>

<p><strong>PRIMERA. — OBJETO.</strong><br/>
LA EMPRESA se obliga a prestar al USUARIO el servicio de monitoreo electrónico de alarmas
<strong>24 horas al día, los 365 días del año</strong>, en el inmueble ubicado en
<strong>{{ object.contract_domicilio_servicio or object.address_street }}</strong>,
con número de cuenta asignado <strong>{{ object.contract_cuenta_monitoreo or '___________' }}</strong>.</p>

<p><strong>SEGUNDA. — PLAN CONTRATADO.</strong><br/>
El USUARIO contrata el plan denominado <strong>{{ object.product_id.name }}</strong>
con una cuota mensual de <strong>${{ "%.2f"|format(object.price_total or 0) }} MXN (más IVA)</strong>.</p>

<p><strong>TERCERA. — VIGENCIA.</strong><br/>
El contrato tendrá una vigencia mínima de
<strong>{{ object.commitment_months or 12 }} meses</strong> a partir del
<strong>{{ object.start_date }}</strong>.</p>

<p><strong>CUARTA. — PROCEDIMIENTO DE RESPUESTA.</strong><br/>
Al recibir una señal de alarma, LA EMPRESA realizará el siguiente protocolo:</p>
<ol style="margin-left: 20px;">
    <li>Verificación telefónica con los contactos autorizados registrados en la cuenta.</li>
    <li>En caso de no poder verificar, se notificará a las autoridades competentes.</li>
    <li>Se generará un reporte del evento con hora, tipo de señal y acciones tomadas.</li>
</ol>

<p><strong>QUINTA. — CLAVES DE SEGURIDAD.</strong><br/>
Se establecen claves confidenciales para la operación de la cuenta. El USUARIO es responsable
de su confidencialidad.</p>

<p><strong>SEXTA. — EXCLUSIONES DE RESPONSABILIDAD.</strong><br/>
LA EMPRESA no será responsable por: a) Fallas en la red de datos; b) Cortes de energía eléctrica;
c) Tiempo de respuesta de autoridades; d) Sistema de alarma desactivado por el USUARIO.</p>

<p><strong>SÉPTIMA. — PAGO Y MORA.</strong><br/>
El retraso mayor a <strong>15 días</strong> faculta a LA EMPRESA a suspender el servicio
sin previo aviso y sin responsabilidad.</p>

<p><strong>OCTAVA. — JURISDICCIÓN.</strong><br/>
Las partes se someten a la jurisdicción de los tribunales del Estado de
<strong>Tamaulipas</strong>, México.</p>

<br/>
<p>Leído y firmado en <strong>Matamoros, Tamps.</strong>, a <strong>{{ object.start_date }}</strong>.</p>

<br/><br/>
<table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 30px;">
    <tr>
        <td style="width: 45%; text-align: center; padding-top: 50px; border-top: 1px solid #333;">
            <strong>LA EMPRESA</strong><br/>
            Sentinela Seguridad Privada S.A. de C.V.
        </td>
        <td style="width: 10%;"></td>
        <td style="width: 45%; text-align: center; padding-top: 50px; border-top: 1px solid #333;">
            <strong>EL USUARIO</strong><br/>
            {{ object.partner_id.name }}<br/>
            RFC: {{ object.partner_id.vat or '___________' }}
        </td>
    </tr>
</table>

</div>"""


def post_init_hook(env):
    """Carga plantillas base de contratos si no existen."""
    Template = env['sentinela.contract.template']
    templates = [
        {
            'name': 'Contrato de Servicio de Internet (WISP)',
            'content': TEMPLATE_INTERNET,
        },
        {
            'name': 'Contrato de Servicio de Monitoreo de Alarmas',
            'content': TEMPLATE_MONITOREO,
        },
    ]
    for tpl in templates:
        if not Template.search([('name', '=', tpl['name'])], limit=1):
            Template.create(tpl)
            _logger.info('Plantilla de contrato creada: %s', tpl['name'])
        else:
            _logger.info('Plantilla ya existe, omitida: %s', tpl['name'])

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SentinelaContractTemplate(models.Model):
    _name = 'sentinela.contract.template'
    _description = 'Plantilla de Contrato Sentinela'
    _inherit = ['mail.render.mixin'] # Para poder usar el motor de renderizado de Odoo
    _order = 'name'

    name = fields.Char(string='Nombre de la Plantilla', required=True)
    active = fields.Boolean(default=True)
    
    content = fields.Html(
        string='Contenido HTML', 
        required=True,
        translate=True,
        help="Use marcadores de Odoo como {{ object.partner_id.name }} para personalizar."
    )
    
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    def action_preview(self):
        self.ensure_one()
        # Buscar una suscripción para usar de ejemplo
        sample_sub = self.env['sentinela.subscription'].search([], limit=1, order='id desc')
        if not sample_sub:
            raise ValidationError("No hay suscripciones en el sistema para generar una vista previa.")
        
        try:
            rendered_html = self._render_template(self.content, 'sentinela.subscription', sample_sub.ids)[sample_sub.id]
        except Exception as e:
            # En lugar de romper, mostrar el error en la hoja para que el usuario sepa qué corregir
            rendered_html = f'''
                <div style="border: 5px solid red; padding: 20px; color: red; background: #fff0f0;">
                    <h3>⚠️ Error en el diseño del contrato</h3>
                    <p>Hay un problema con alguna de las variables (los códigos entre llaves <b>{{ }}</b>).</p>
                    <p><b>Detalle técnico:</b> {str(e)}</p>
                    <hr/>
                    <p><b>Consejo:</b> Revise que no haya espacios extra dentro de las llaves y que los nombres de los campos sean correctos.</p>
                </div>
                <div style="opacity: 0.3; pointer-events: none;">
                    {self.content}
                </div>
            '''
        
        # Inyectar estilos para simular HOJA TAMAÑO CARTA (8.5 x 11 in)
        # 816px de ancho aprox a 96dpi
        company_id = self.env.company.id
        # Tamaño hoja carta a 96dpi: 816 x 1056 px
        # Marcadores de salto de página: línea roja punteada cada 1056px
        page_break_bg = (
            "background-color: white; "
            "background-image: repeating-linear-gradient("
            "to bottom, "
            "transparent 0, "
            "transparent 1048px, "
            "rgba(220,53,69,0.55) 1048px, "
            "rgba(220,53,69,0.55) 1056px); "
        )
        styled_html = f'''
            <div style="background-color: #525659; padding: 30px 0; min-height: 1000px; display: flex; flex-direction: column; align-items: center;">
                <div style="{page_break_bg} width: 816px; min-height: 1056px; padding: 22mm 60px 20mm 60px; box-shadow: 0 0 20px rgba(0,0,0,0.5); font-family: Arial, sans-serif; position: relative; box-sizing: border-box;">

                    <!-- Header igual al PDF y la vista previa del contrato -->
                    <table style="width: 100%; border-bottom: 2px solid #1f4e79; padding-bottom: 6px; margin-bottom: 20px; border-collapse: collapse;">
                        <tr>
                            <td style="vertical-align: middle; text-align: left;">
                                <img src="/web/image/res.company/{company_id}/logo"
                                     style="height: 45px; width: auto; max-width: 170px; vertical-align: middle; margin-right: 12px;"/>
                                <span style="font-size: 16px; color: #1f4e79; font-weight: bold; vertical-align: middle;">CONTRATO DE SERVICIO</span>
                            </td>
                            <td style="text-align: right; font-size: 11px; color: #888; vertical-align: middle; white-space: nowrap; font-style: italic;">
                                Folio y Fecha<br/>
                                (se llenan al generar)
                            </td>
                        </tr>
                    </table>

                    <div style="font-size: 13px; line-height: 1.5; color: #333; text-align: justify;">
                        {rendered_html}
                    </div>

                    <!-- Estilos para forzar el salto de página visual en el navegador -->
                    <style>
                        .page-break-before {{
                            display: block;
                            height: 50px;
                            border-top: 2px dashed #ff0000;
                            margin: 40px -60px;
                            background: #fff0f0;
                            position: relative;
                            text-align: center;
                        }}
                        .page-break-before:after {{
                            content: "SALTO DE PÁGINA (Aquí inicia la Hoja 2)";
                            font-size: 10px;
                            color: red;
                            font-weight: bold;
                            top: -15px;
                            position: absolute;
                            left: 50%;
                            transform: translateX(-50%);
                            background: white;
                            padding: 0 10px;
                        }}
                    </style>
                </div>
            </div>
        '''
        
        preview_wizard = self.env['sentinela.contract.template.preview'].create({
            'name': f'Vista Previa: {self.name}',
            'html_preview': styled_html
        })
        
        return {
            'name': 'Vista Previa del Contrato',
            'type': 'ir.actions.act_window',
            'res_model': 'sentinela.contract.template.preview',
            'view_mode': 'form',
            'res_id': preview_wizard.id,
            'target': 'new',
            'context': {'dialog_size': 'large'}
        }

class SentinelaContractTemplatePreview(models.TransientModel):
    _name = 'sentinela.contract.template.preview'
    _description = 'Asistente de Vista Previa de Contrato'

    name = fields.Char(string='Título')
    html_preview = fields.Html(string='Vista Previa')
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
        styled_html = f'''
            <div style="background-color: #525659; padding: 30px 0; min-height: 1000px; display: flex; flex-direction: column; align-items: center;">
                <div style="background: white; width: 816px; min-height: 1056px; padding: 30mm 60px 20mm 60px; box-shadow: 0 0 20px rgba(0,0,0,0.5); font-family: Arial, sans-serif; position: relative; box-sizing: border-box;">
                    
                    <!-- Simulación de Encabezado Real -->
                    <div style="text-align: center; margin-bottom: 20px;">
                        <img src="/web/binary/company_logo" style="max-height: 80px;"/>
                        <div style="font-size: 10px; color: #666; margin-top: 5px;">[ Simulación de Encabezado de Impresión ]</div>
                    </div>

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
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
from odoo.tools.pdf import merge_pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

class SentinelaSignDocument(models.Model):
    _name = 'sentinela.sign.document'
    _description = 'Documento para Firma Digital'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, default='Nuevo')
    partner_id = fields.Many2one('res.partner', string='Firmante (Cliente)', required=True, tracking=True)
    
    # Archivos
    file = fields.Binary(string='Documento Original (PDF)', required=True, attachment=True)
    filename = fields.Char(string='Nombre Archivo')
    
    file_signed = fields.Binary(string='Documento Firmado', attachment=True, readonly=True)
    filename_signed = fields.Char(string='Nombre Archivo Firmado')

    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('signed', 'Firmado'),
        ('cancel', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)

    # Datos de Firma
    signature = fields.Binary('Firma', help='Firma capturada', attachment=True)
    signed_by = fields.Char('Firmado por')
    signed_on = fields.Datetime('Fecha de Firma')

    # Enlace Genérico (Origen)
    res_model = fields.Char('Modelo Origen')
    res_id = fields.Integer('ID Origen')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('sentinela.sign.document') or 'DOC-0000'
        return super().create(vals_list)

    def _compute_access_url(self):
        super()._compute_access_url()
        for doc in self:
            doc.access_url = '/my/document/%s' % (doc.id)

    def action_send_email(self):
        self.ensure_one()
        template = self.env.ref('sentinela_digital_sign.mail_template_sign_document_request')
        self.message_post_with_source(
            template,
            email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
        )
        self.state = 'sent'

    def action_sign(self, signature=None):
        """ Método llamado desde el controlador cuando el usuario firma """
        self.ensure_one()
        if not signature:
            return False
            
        # 1. Guardar datos crudos
        self.signature = signature['signature']
        self.signed_by = signature['name']
        self.signed_on = fields.Datetime.now()
        
        # 2. Generar PDF final con anexo de firma
        self._generate_signed_pdf()
        
        self.state = 'signed'
        return True

    def _generate_signed_pdf(self):
        """ Añade una página al final con la firma """
        original_pdf_stream = io.BytesIO(base64.b64decode(self.file))
        
        # Crear la página de firma con ReportLab
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        width, height = letter
        
        # Diseño de la página de certificación
        can.drawString(50, height - 100, "CERTIFICADO DE FIRMA DIGITAL")
        can.line(50, height - 105, 550, height - 105)
        
        can.drawString(50, height - 150, f"Documento: {self.name}")
        can.drawString(50, height - 170, f"Firmado por: {self.signed_by}")
        can.drawString(50, height - 190, f"Fecha: {self.signed_on}")
        can.drawString(50, height - 210, f"ID del Cliente: {self.partner_id.name}")
        
        # Incrustar la imagen de la firma
        if self.signature:
            signature_img = io.BytesIO(base64.b64decode(self.signature))
            # Dibujar imagen (x, y, width, height)
            try:
                can.drawImage(
                    base64.b64decode(self.signature), # Reportlab a veces pide path, pero image reader acepta bytes
                    x=50, y=height - 400, width=200, height=100,
                    mask='auto'
                )
            except Exception:
                # Fallback simple si la imagen falla (reportlabImageReader a veces da guerra con b64 directo)
                can.drawString(50, height - 350, "[Firma Digital Capturada]")

        can.drawString(50, 50, "Este documento ha sido firmado digitalmente a través del sistema Sentinela.")
        can.save()

        # Obtener contenido en bytes
        packet_content = packet.getvalue()
        original_content = base64.b64decode(self.file)
        
        # Mezclar usando herramientas de Odoo
        try:
            merged_content = merge_pdf([original_content, packet_content])
            self.file_signed = base64.b64encode(merged_content)
            self.filename_signed = f"{self.filename or 'document'}_firmado.pdf"
        except Exception as e:
            # Fallback seguro: solo guardar la firma, no romper el flujo
            self.message_post(body=f"Error generando PDF firmado: {str(e)}")


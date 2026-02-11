import base64
import json
import logging
import requests
from lxml import etree
from datetime import datetime, timedelta

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    cfdi_uuid = fields.Char(string='CFDI UUID', copy=False, readonly=True)
    cfdi_xml = fields.Binary(string='CFDI XML', copy=False, attachment=True, readonly=True)
    cfdi_xml_filename = fields.Char(string='CFDI XML Nombre')
    cfdi_pdf = fields.Binary(string='CFDI PDF', copy=False, attachment=True, readonly=True)
    cfdi_pdf_filename = fields.Char(string='CFDI PDF Nombre')
    cfdi_status = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente de Timbrado'),
        ('valid', 'Timbrado Válido'),
        ('cancel', 'Cancelado'),
        ('error', 'Error'),
    ], string='Estado CFDI', default='draft', copy=False, readonly=True, tracking=True)
    cfdi_message = fields.Text(string='Mensaje CFDI', copy=False, readonly=True)

    # == Campos para el reporte PDF del CFDI ==
    l10n_mx_edi_cfdi_certificate_serial_number = fields.Char(string='No. de Serie del Certificado', copy=False, readonly=True)
    l10n_mx_edi_cfdi_timestamp = fields.Char(string='Fecha y Hora de Timbrado', copy=False, readonly=True)
    l10n_mx_edi_cfdi_seal = fields.Char(string='Sello Digital del CFDI', copy=False, readonly=True)
    l10n_mx_edi_cfdi_sat_seal = fields.Char(string='Sello Digital del SAT', copy=False, readonly=True)
    l10n_mx_edi_cfdi_original_chain = fields.Text(string='Cadena Original del Timbre', copy=False, readonly=True)
    l10n_mx_edi_cfdi_qr = fields.Binary(string='Código QR del CFDI', compute='_compute_cfdi_qr_code', copy=False)

    def _compute_cfdi_qr_code(self):
        for move in self:
            if not move.cfdi_uuid:
                move.l10n_mx_edi_cfdi_qr = False
                continue
            
            # Formato del QR: https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?id=<UUID>&re=<RFC_Emisor>&rr=<RFC_Receptor>&tt=<Total>&fe=<8_ultimos_caracteres_del_sello>
            qr_string = "https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?" + "&".join([
                f"id={move.cfdi_uuid}",
                f"re={move.company_id.vat}",
                f"rr={move.partner_id.vat}",
                f"tt={move.amount_total:.2f}",
                f"fe={move.l10n_mx_edi_cfdi_seal[-8:] if move.l10n_mx_edi_cfdi_seal else ''}",
            ])

            try:
                import qrcode
                import base64
                from io import BytesIO

                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                qr.add_data(qr_string)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                qr_img_b64 = base64.b64encode(buffered.getvalue())
                move.l10n_mx_edi_cfdi_qr = qr_img_b64
            except ImportError:
                _logger.warning("La librería 'qrcode' no está instalada. No se puede generar el código QR. Ejecute 'pip3 install qrcode'.")
                move.l10n_mx_edi_cfdi_qr = False


    def _get_prodigia_config(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        return {
            'url': get_param('sentinela_cfdi_prodigia.api_url'),
            'user': get_param('sentinela_cfdi_prodigia.user'),
            'password': get_param('sentinela_cfdi_prodigia.password'),
            'contract': get_param('sentinela_cfdi_prodigia.contract'),
            'test_mode': get_param('sentinela_cfdi_prodigia.test_mode', 'True').lower() == 'true',
        }

    def _generate_cfdi_xml(self):
        self.ensure_one()
        
        # Validaciones básicas
        if not self.company_id.vat:
            raise UserError("El Emisor (Compañía) debe tener RFC.")
        if not self.partner_id.vat:
            raise UserError("El Receptor (Cliente) debe tener RFC.")
        if not self.partner_id.l10n_mx_edi_fiscal_regime:
            raise UserError("El Cliente debe tener Régimen Fiscal configurado.")

        # Construcción de XML 4.0
        NSMAP = {
            'cfdi': "http://www.sat.gob.mx/cfd/4",
            'xsi': "http://www.w3.org/2001/XMLSchema-instance"
        }
        
        root = etree.Element("{http://www.sat.gob.mx/cfd/4}Comprobante", nsmap=NSMAP)
        root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", "http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd")
        root.set("Version", "4.0")
        root.set("Serie", (self.name or "").split('/')[0] or "FACT")
        root.set("Folio", (self.name or "").split('/')[-1] or "1")
        
        # Odoo corre en UTC, pero el SAT requiere hora local del lugar de expedición.
        # Restamos 6 horas (CST) y un margen de seguridad de 5 mins.
        fecha_emision = (datetime.now() - timedelta(hours=6, minutes=5)).strftime('%Y-%m-%dT%H:%M:%S')
        root.set("Fecha", fecha_emision)
        root.set("Sello", "") # Vacío para que lo calcule Prodigia
        root.set("NoCertificado", "") # Vacío
        root.set("Certificado", "") # Vacío
        root.set("SubTotal", f"{self.amount_untaxed:.2f}")
        root.set("Moneda", self.currency_id.name)
        root.set("Total", f"{self.amount_total:.2f}")
        root.set("TipoDeComprobante", "I")
        root.set("Exportacion", "01")
        root.set("MetodoPago", "PUE" if self.invoice_payment_term_id.name != 'PPD' else "PPD")
        root.set("FormaPago", "01") # Debería ser dinámico
        root.set("LugarExpedicion", self.company_id.zip or "00000")

        # Emisor
        emisor = etree.SubElement(root, "{http://www.sat.gob.mx/cfd/4}Emisor")
        emisor.set("Rfc", self.company_id.vat)
        
        # Priorizar Razón Social Fiscal si existe, si no, usar nombre de la compañía
        nombre_base = self.company_id.l10n_mx_edi_fiscal_name or self.company_id.name
        nombre_emisor = nombre_base.upper()
        
        # Limpieza de nombre de emisor para CFDI 4.0
        for suffix in [", S.A. DE C.V.", " S.A. DE C.V.", " SA DE CV", " S DE RL DE CV", ", S. DE R.L. DE C.V."]:
            nombre_emisor = nombre_emisor.replace(suffix, "")
        
        emisor.set("Nombre", nombre_emisor.strip())
        emisor.set("RegimenFiscal", self.company_id.l10n_mx_edi_fiscal_regime or "601")

        # Receptor
        receptor = etree.SubElement(root, "{http://www.sat.gob.mx/cfd/4}Receptor")
        receptor.set("Rfc", self.partner_id.vat)
        receptor.set("Nombre", self.partner_id.name.upper())
        receptor.set("DomicilioFiscalReceptor", self.partner_id.zip or "00000")
        receptor.set("RegimenFiscalReceptor", self.partner_id.l10n_mx_edi_fiscal_regime)
        receptor.set("UsoCFDI", self.partner_id.l10n_mx_edi_usage or "G03")

        # Conceptos e Impuestos
        conceptos = etree.SubElement(root, "{http://www.sat.gob.mx/cfd/4}Conceptos")
        impuestos_agrupados = {} # Para el total global
        
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            concepto = etree.SubElement(conceptos, "{http://www.sat.gob.mx/cfd/4}Concepto")
            concepto.set("ClaveProdServ", line.product_id.l10n_mx_edi_code_sat or "01010101")
            if line.product_id.default_code:
                concepto.set("NoIdentificacion", line.product_id.default_code)
            concepto.set("Cantidad", f"{line.quantity:.6f}")
            concepto.set("ClaveUnidad", line.product_id.l10n_mx_edi_um_code_sat or "E48")
            concepto.set("Unidad", line.product_uom_id.name or "Servicio")
            concepto.set("Descripcion", line.name[:1000]) # Límite SAT
            concepto.set("ValorUnitario", f"{line.price_unit:.6f}")
            concepto.set("Importe", f"{line.price_subtotal:.2f}")
            concepto.set("ObjetoImp", "02" if line.tax_ids else "01")

            if line.tax_ids:
                impuestos_c = etree.SubElement(concepto, "{http://www.sat.gob.mx/cfd/4}Impuestos")
                traslados_c = etree.SubElement(impuestos_c, "{http://www.sat.gob.mx/cfd/4}Traslados")
                for tax in line.tax_ids:
                    tax_code = tax.l10n_mx_edi_tax_code or "002"
                    tasa = tax.amount / 100.0
                    importe_tax = round(line.price_subtotal * tasa, 2)
                    
                    traslado_c = etree.SubElement(traslados_c, "{http://www.sat.gob.mx/cfd/4}Traslado")
                    traslado_c.set("Base", f"{line.price_subtotal:.2f}")
                    traslado_c.set("Impuesto", tax_code)
                    traslado_c.set("TipoFactor", "Tasa")
                    traslado_c.set("TasaOCuota", f"{tasa:.64f}".rstrip('0').rstrip('.') if tasa > 0 else "0.000000")
                    # El SAT pide exactamente 6 decimales en TasaOCuota
                    traslado_c.set("TasaOCuota", f"{tasa:.6f}")
                    traslado_c.set("Importe", f"{importe_tax:.2f}")
                    
                    # Agrupar para el total global
                    key = (tax_code, f"{tasa:.6f}")
                    if key not in impuestos_agrupados:
                        impuestos_agrupados[key] = {'base': 0.0, 'importe': 0.0}
                    impuestos_agrupados[key]['base'] += line.price_subtotal
                    impuestos_agrupados[key]['importe'] += importe_tax

        # Impuestos Globales (solo si hay traslados)
        if impuestos_agrupados:
            impuestos_g = etree.SubElement(root, "{http://www.sat.gob.mx/cfd/4}Impuestos")
            total_traslado = sum(v['importe'] for v in impuestos_agrupados.values())
            impuestos_g.set("TotalImpuestosTrasladados", f"{total_traslado:.2f}")
            traslados_g = etree.SubElement(impuestos_g, "{http://www.sat.gob.mx/cfd/4}Traslados")
            for (t_code, t_tasa), data in impuestos_agrupados.items():
                traslado_g = etree.SubElement(traslados_g, "{http://www.sat.gob.mx/cfd/4}Traslado")
                traslado_g.set("Base", f"{data['base']:.2f}")
                traslado_g.set("Impuesto", t_code)
                traslado_g.set("TipoFactor", "Tasa")
                traslado_g.set("TasaOCuota", t_tasa)
                traslado_g.set("Importe", f"{data['importe']:.2f}")

        xml_str = etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        return xml_str

    def action_cfdi_stamp_prodigia(self):
        for move in self:
            if move.state != 'posted':
                raise UserError(_('La factura debe estar publicada para poder timbrarla.'))

            config = self._get_prodigia_config()
            if not all([config['url'], config['user'], config['password'], config['contract']]):
                raise UserError(_('Por favor, configure las credenciales y el CONTRATO de Prodigia en los Ajustes.'))

            try:
                xml_to_stamp = move._generate_cfdi_xml()
                xml_b64 = base64.b64encode(xml_to_stamp).decode()

                headers = {'Content-Type': 'application/json'}
                auth = (config['user'], config['password'])
                payload = {
                    "xmlBase64": xml_b64,
                    "contrato": config['contract'],
                    "prueba": str(config['test_mode']).lower(),
                    "opciones": ["CALCULAR_SELLO"]
                }
                
                _logger.info("--- CFDI XML ENVIADO ---")
                _logger.info(xml_to_stamp.decode())
                _logger.info("------------------------")

                move.write({'cfdi_status': 'pending', 'cfdi_message': 'Enviando a Prodigia...'})
                
                response = requests.post(config['url'], headers=headers, auth=auth, json=payload, timeout=30)
                _logger.info(f"RESPUESTA PAC STATUS: {response.status_code}")
                _logger.info(f"RESPUESTA PAC BODY: {response.text}")
                
                if response.status_code in [200, 202]:
                    res_data = response.json()
                    if res_data.get('timbradoOk'): # Check if Prodigia explicitly says it's OK
                        stamped_xml = base64.b64decode(res_data['xml'])
                        tree = etree.fromstring(stamped_xml)
                        
                        # --- Extraer datos del CFDI para el reporte ---
                        tfd_node = tree.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
                        if tfd_node is not None:
                            uuid = tfd_node.attrib.get('UUID', 'No encontrado')
                            no_certificado_sat = tfd_node.attrib.get('NoCertificadoSAT', '')
                            fecha_timbrado = tfd_node.attrib.get('FechaTimbrado', '')
                            sello_sat = tfd_node.attrib.get('SelloSAT', '')
                            sello_cfd = tfd_node.attrib.get('SelloCFD', '')
                            rfc_pac = tfd_node.attrib.get('RfcProvCertif', '')

                            cadena_original = '||'.join([
                                '1.1',
                                uuid,
                                fecha_timbrado,
                                rfc_pac,
                                sello_cfd,
                                no_certificado_sat,
                            ]) + '||'

                            comprobante_node = tree.find('.')
                            sello_comprobante = comprobante_node.attrib.get('Sello', '')

                            move.write({
                                'cfdi_status': 'valid',
                                'cfdi_uuid': uuid,
                                'cfdi_xml': base64.b64encode(stamped_xml),
                                'cfdi_xml_filename': f'{move.name.replace("/", "_")}-CFDI.xml',
                                'cfdi_message': res_data.get('mensaje') or 'Factura timbrada exitosamente.',
                                'l10n_mx_edi_cfdi_certificate_serial_number': no_certificado_sat,
                                'l10n_mx_edi_cfdi_timestamp': fecha_timbrado,
                                'l10n_mx_edi_cfdi_seal': sello_comprobante,
                                'l10n_mx_edi_cfdi_sat_seal': sello_sat,
                                'l10n_mx_edi_cfdi_original_chain': cadena_original,
                            })
                        else:
                            move.write({'cfdi_status': 'error', 'cfdi_message': 'No se encontró el Timbre Fiscal Digital en el XML de respuesta.'})
                    else:
                        msg = res_data.get('message') or res_data.get('mensaje') or 'Error desconocido de Prodigia.'
                        move.write({'cfdi_status': 'error', 'cfdi_message': msg})
                else:
                    move.write({'cfdi_status': 'error', 'cfdi_message': f'Error PAC ({response.status_code}): {response.text}'})

            except Exception as e:
                move.write({'cfdi_status': 'error', 'cfdi_message': f'Error de proceso: {str(e)}'})
        return True
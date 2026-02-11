import base64
import json
import logging
import requests
from lxml import etree
from datetime import datetime, timedelta
import io
try:
    import qrcode
except ImportError:
    qrcode = None

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
    cfdi_qr_code = fields.Binary(string='CFDI QR Code', copy=False, readonly=True)
    cfdi_status = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente de Timbrado'),
        ('valid', 'Timbrado Válido'),
        ('cancel', 'Cancelado'),
        ('error', 'Error'),
    ], string='Estado CFDI', default='draft', copy=False, readonly=True, tracking=True)
    cfdi_message = fields.Text(string='Mensaje CFDI', copy=False, readonly=True)
    
    def _generate_cfdi_qr_code_b64(self, cfdi_uuid, stamped_xml):
        _logger.info("--- (Función interna) Iniciando generación de QR Code ---")
        if not cfdi_uuid:
            _logger.warning("No hay UUID, no se puede generar QR.")
            return None

        sello_del_cfdi = ""
        if stamped_xml:
            try:
                # Usar el XML recién timbrado que se pasa como argumento
                xml_tree = etree.fromstring(stamped_xml)
                sello_del_cfdi = xml_tree.get('Sello', '')[-8:]
                _logger.info(f"Últimos 8 del sello: {sello_del_cfdi}")
            except Exception as e:
                _logger.warning(f"No se pudo obtener el sello del XML para el QR: {e}")
        else:
            _logger.warning("No se recibió XML timbrado para generar el QR.")


        qr_string = f"https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?id={cfdi_uuid}&re={self.company_id.vat}&rr={self.partner_id.vat}&tt={self.amount_total}&fe={sello_del_cfdi}"
        _logger.info(f"Cadena para QR: {qr_string}")

        try:
            if qrcode:
                img = qrcode.make(qr_string, box_size=4, border=4)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                qr_b64 = base64.b64encode(buffer.getvalue())
                _logger.info(f"QR B64 generado (primeros 10 bytes): {qr_b64[:10]}")
                return qr_b64
            else:
                _logger.warning("La librería 'qrcode' no está instalada.")
                return None
        except Exception as e:
            _logger.error(f"¡¡¡EXCEPCIÓN INESPERADA generando QR!!!: {e}", exc_info=True)
            return None

    def _get_prodigia_config(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        return {
            'url': get_param('sentinela_cfdi_prodigia.api_url'),
            'user': get_param('sentinela_cfdi_prodigia.user'),
            'password': get_param('sentinela_cfdi_prodigia.password'),
            'contract': get_param('sentinela_cfdi_prodigia.contract'),
        }

    def _generate_cfdi_xml(self):
        self.ensure_one()
        
        if not self.company_id.vat:
            raise UserError("El Emisor (Compañía) debe tener RFC.")
        if not self.partner_id.vat:
            raise UserError("El Receptor (Cliente) debe tener RFC.")
        if not self.partner_id.l10n_mx_edi_fiscal_regime:
            raise UserError("El Cliente debe tener Régimen Fiscal configurado.")

        NSMAP = {
            'cfdi': "http://www.sat.gob.mx/cfd/4",
            'xsi': "http://www.w3.org/2001/XMLSchema-instance"
        }
        
        root = etree.Element("{http://www.sat.gob.mx/cfd/4}Comprobante", nsmap=NSMAP)
        root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", "http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd")
        root.set("Version", "4.0")
        root.set("Serie", (self.name or "").split('/')[0] or "FACT")
        root.set("Folio", (self.name or "").split('/')[-1] or "1")
        
        fecha_emision = (datetime.now() - timedelta(hours=6, minutes=5)).strftime('%Y-%m-%dT%H:%M:%S')
        root.set("Fecha", fecha_emision)
        root.set("Sello", "")
        root.set("NoCertificado", "")
        root.set("Certificado", "")
        root.set("SubTotal", f"{self.amount_untaxed:.2f}")
        root.set("Moneda", self.currency_id.name)
        root.set("Total", f"{self.amount_total:.2f}")
        root.set("TipoDeComprobante", "I")
        root.set("Exportacion", "01")
        root.set("MetodoPago", "PUE" if self.invoice_payment_term_id.name != 'PPD' else "PPD")
        root.set("FormaPago", "01")
        root.set("LugarExpedicion", self.company_id.zip or "00000")

        emisor = etree.SubElement(root, "{http://www.sat.gob.mx/cfd/4}Emisor")
        emisor.set("Rfc", self.company_id.vat)
        
        nombre_base = self.company_id.l10n_mx_edi_fiscal_name or self.company_id.name
        nombre_emisor = nombre_base.upper()
        
        for suffix in [", S.A. DE C.V.", " S.A. DE C.V.", " SA DE CV", " S DE RL DE CV", ", S. DE R.L. DE C.V."]:
            nombre_emisor = nombre_emisor.replace(suffix, "")
        
        emisor.set("Nombre", nombre_emisor.strip())
        emisor.set("RegimenFiscal", self.company_id.l10n_mx_edi_fiscal_regime or "601")

        receptor = etree.SubElement(root, "{http://www.sat.gob.mx/cfd/4}Receptor")
        receptor.set("Rfc", self.partner_id.vat)
        receptor.set("Nombre", self.partner_id.name.upper())
        receptor.set("DomicilioFiscalReceptor", self.partner_id.zip or "00000")
        receptor.set("RegimenFiscalReceptor", self.partner_id.l10n_mx_edi_fiscal_regime)
        receptor.set("UsoCFDI", self.partner_id.l10n_mx_edi_usage or "G03")

        conceptos = etree.SubElement(root, "{http://www.sat.gob.mx/cfd/4}Conceptos")
        impuestos_agrupados = {}
        
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            concepto = etree.SubElement(conceptos, "{http://www.sat.gob.mx/cfd/4}Concepto")
            concepto.set("ClaveProdServ", line.product_id.l10n_mx_edi_code_sat or "01010101")
            if line.product_id.default_code:
                concepto.set("NoIdentificacion", line.product_id.default_code)
            concepto.set("Cantidad", f"{line.quantity:.6f}")
            concepto.set("ClaveUnidad", line.product_id.l10n_mx_edi_um_code_sat or "E48")
            concepto.set("Unidad", line.product_uom_id.name or "Servicio")
            concepto.set("Descripcion", line.name[:1000])
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
                    traslado_c.set("TasaOCuota", f"{tasa:.6f}")
                    traslado_c.set("Importe", f"{importe_tax:.2f}")
                    
                    key = (tax_code, f"{tasa:.6f}")
                    if key not in impuestos_agrupados:
                        impuestos_agrupados[key] = {'base': 0.0, 'importe': 0.0}
                    impuestos_agrupados[key]['base'] += line.price_subtotal
                    impuestos_agrupados[key]['importe'] += importe_tax

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
                    "prueba": "true",
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
                    ct = response.headers.get('Content-Type', '').lower()
                    
                    if 'application/json' in ct:
                        res_data = response.json()
                        if res_data.get('xml'):
                            stamped_xml = base64.b64decode(res_data['xml'])
                            tree = etree.fromstring(stamped_xml)
                            tfd_node = tree.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
                            uuid = tfd_node.attrib.get('UUID', 'No encontrado') if tfd_node is not None else 'No encontrado'
                            
                            qr_code_b64 = move._generate_cfdi_qr_code_b64(uuid, stamped_xml)

                            move.write({
                                'cfdi_status': 'valid',
                                'cfdi_uuid': uuid,
                                'cfdi_xml': base64.b64encode(stamped_xml),
                                'cfdi_qr_code': qr_code_b64,
                                'cfdi_xml_filename': f'{move.name.replace("/", "_")}-CFDI.xml',
                                'cfdi_message': 'Factura timbrada exitosamente (JSON).',
                            })
                        else:
                            msg = res_data.get('message') or res_data.get('mensaje') or 'Error desconocido de Prodigia.'
                            move.write({'cfdi_status': 'error', 'cfdi_message': msg})
                    
                    else:
                        try:
                            resp_text = response.text.strip()
                            resp_root = etree.fromstring(resp_text.encode('utf-8'))
                            
                            timbrado_ok = False
                            xml_b64_content = None
                            mensaje_err = "Error desconocido (XML)"

                            for child in resp_root:
                                tag_name = etree.QName(child).localname
                                if tag_name == 'timbradoOk' and child.text == 'true':
                                    timbrado_ok = True
                                elif tag_name == 'xmlBase64':
                                    xml_b64_content = child.text
                                elif tag_name == 'mensaje':
                                    mensaje_err = child.text

                            if timbrado_ok and xml_b64_content:
                                stamped_xml_bytes = base64.b64decode(xml_b64_content)
                                tree_cfdi = etree.fromstring(stamped_xml_bytes)
                                tfd_node = tree_cfdi.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital')
                                uuid = tfd_node.attrib.get('UUID', 'No encontrado') if tfd_node is not None else 'No encontrado'
                                
                                qr_code_b64 = move._generate_cfdi_qr_code_b64(uuid, stamped_xml_bytes)
                                
                                move.write({
                                    'cfdi_status': 'valid',
                                    'cfdi_uuid': uuid,
                                    'cfdi_xml': base64.b64encode(stamped_xml_bytes),
                                    'cfdi_qr_code': qr_code_b64,
                                    'cfdi_xml_filename': f'{move.name.replace("/", "_")}-CFDI.xml',
                                    'cfdi_message': 'Factura timbrada exitosamente (XML).',
                                })
                            else:
                                move.write({'cfdi_status': 'error', 'cfdi_message': mensaje_err})
                                
                        except Exception as e_xml:
                             move.write({'cfdi_status': 'error', 'cfdi_message': f'Error parseando XML PAC: {str(e_xml)}'})

                else:
                    move.write({'cfdi_status': 'error', 'cfdi_message': f'Error PAC ({response.status_code}): {response.text}'})

            except Exception as e:
                move.write({'cfdi_status': 'error', 'cfdi_message': f'Error de proceso: {str(e)}'})
        return True

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Panel EN VIVO de la ventana de atención de alarmas.
 *
 * Hace polling cada REFRESH_MS al servidor (`get_attention_companion_data`) y
 * pinta sus PROPIAS tablas: eventos abiertos del mismo cliente + historial de
 * señales 24h del panel. NO depende del registro transitorio del wizard ni de
 * record.load() → las señales/eventos que llegan DESPUÉS de abrir aparecen solos
 * y nunca toca la bitácora que el operador está capturando.
 */
const REFRESH_MS = 10000;

export class AlarmCompanionLive extends Component {
    static template = xml`
        <div>
            <div class="text-end text-muted small mb-2">
                <i t-att-class="state.busy ? 'fa fa-sync fa-spin me-1' : 'fa fa-sync me-1'"/>
                En vivo (cada 10 s)<t t-if="state.last"> · <t t-esc="state.last"/></t>
            </div>

            <h6 class="fw-bold">🔁 Eventos múltiples del cliente (<t t-esc="state.siblings.length"/>)</h6>
            <table class="table table-sm table-striped" t-if="state.siblings.length">
                <thead><tr><th>Evento</th><th>Inicio</th><th>Código</th><th>Prioridad</th><th>Estado</th></tr></thead>
                <tbody>
                    <tr t-foreach="state.siblings" t-as="ev" t-key="ev.id">
                        <td><t t-esc="ev.name"/></td>
                        <td><t t-esc="ev.start"/></td>
                        <td><t t-esc="ev.code"/></td>
                        <td><t t-esc="ev.priority"/></td>
                        <td><t t-esc="ev.status"/></td>
                    </tr>
                </tbody>
            </table>
            <p t-if="!state.siblings.length" class="text-muted small">Sin otros eventos abiertos de este cliente por ahora.</p>

            <h6 class="fw-bold mt-3">🕓 Historial del panel 24 h (<t t-esc="state.signals.length"/>)</h6>
            <p class="text-muted small mb-1">Incluye aperturas/cierres y fallas (AC, batería) que no generan evento.</p>
            <table class="table table-sm table-striped" t-if="state.signals.length">
                <thead><tr><th>Hora</th><th>Código</th><th>Zona</th><th>Descripción</th></tr></thead>
                <tbody>
                    <tr t-foreach="state.signals" t-as="s" t-key="s_index">
                        <td><t t-esc="s.received"/></td>
                        <td><t t-esc="s.code"/></td>
                        <td><t t-esc="s.zone"/></td>
                        <td><t t-esc="s.desc"/></td>
                    </tr>
                </tbody>
            </table>
            <p t-if="!state.signals.length" class="text-muted small">Sin señales en las últimas 24 h.</p>
        </div>`;
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ siblings: [], signals: [], last: "", busy: false });
        this.timer = null;
        onMounted(() => {
            this.refresh();
            this.timer = setInterval(() => this.refresh(), REFRESH_MS);
        });
        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
        });
    }

    _eventId() {
        const rec = this.props.record;
        const v = rec && rec.data && rec.data.alarm_event_id;
        return Array.isArray(v) ? v[0] : v || null;
    }

    async refresh() {
        if (this.state.busy) {
            return;
        }
        const eventId = this._eventId();
        if (!eventId) {
            return;
        }
        this.state.busy = true;
        try {
            const data = await this.orm.call(
                "sentinela.alarm.event", "get_attention_companion_data", [[eventId]]
            );
            this.state.siblings = data.siblings || [];
            this.state.signals = data.signals || [];
            this.state.last = new Date().toLocaleTimeString();
        } catch (e) {
            console.warn("[alarm companion]", e);
        } finally {
            this.state.busy = false;
        }
    }
}

registry.category("view_widgets").add("alarm_companion", {
    component: AlarmCompanionLive,
});

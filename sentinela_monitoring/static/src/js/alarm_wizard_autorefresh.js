/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useState, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Auto-refresco del wizard de atención de alarmas.
 *
 * Las pestañas "Eventos Múltiples" e "Historial del panel (24h)" son una foto
 * del momento en que se abrió la ventana. Este widget vuelve a consultar cada
 * REFRESH_MS llamando a `action_refresh_related` (que re-escribe las listas en
 * el registro transitorio) y recarga el registro, para que las señales/eventos
 * que llegan DESPUÉS aparezcan solos.
 *
 * SEGURIDAD DE DATOS: no refresca si el operador está escribiendo (registro
 * "dirty" o foco en un input/textarea) → nunca pisa la bitácora a medio capturar.
 */
const REFRESH_MS = 10000;

export class AlarmWizardAutoRefresh extends Component {
    static template = xml`
        <span class="text-muted small d-inline-flex align-items-center">
            <i t-att-class="state.busy ? 'fa fa-sync fa-spin me-1' : 'fa fa-sync me-1'"/>
            Actualización automática activa
            <t t-if="state.last"> · última: <t t-esc="state.last"/></t>
            <button type="button" class="btn btn-sm btn-link p-0 ms-2" t-on-click="refreshNow">Refrescar ahora</button>
        </span>`;
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ last: "", busy: false });
        this.timer = null;
        onMounted(() => {
            this.timer = setInterval(() => this.tick(), REFRESH_MS);
        });
        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
        });
    }

    _operatorIsTyping() {
        const el = document.activeElement;
        if (!el) {
            return false;
        }
        const tag = (el.tagName || "").toLowerCase();
        return tag === "input" || tag === "textarea" || el.isContentEditable;
    }

    async _doRefresh() {
        const record = this.props.record;
        this.state.busy = true;
        try {
            await this.orm.call(record.resModel, "action_refresh_related", [[record.resId]]);
            await record.load();
            this.state.last = new Date().toLocaleTimeString();
        } catch (e) {
            // Silencioso: un fallo puntual no debe romper la ventana de atención.
            console.warn("[alarm autorefresh]", e);
        } finally {
            this.state.busy = false;
        }
    }

    async tick() {
        const record = this.props.record;
        if (!record || !record.resId || this.state.busy) {
            return;
        }
        // No interrumpir al operador: si hay cambios sin guardar o está escribiendo,
        // se salta este ciclo (lo intentará de nuevo en REFRESH_MS).
        if (record.isDirty || this._operatorIsTyping()) {
            return;
        }
        await this._doRefresh();
    }

    async refreshNow() {
        // Refresco manual del operador. Si hay cambios sin guardar (bitácora),
        // se persisten ANTES de recargar para no perderlos.
        const record = this.props.record;
        if (!record || !record.resId || this.state.busy) {
            return;
        }
        if (record.isDirty) {
            const ok = await record.save();
            if (!ok) {
                // La validación bloqueó el guardado → no recargamos, conservamos lo escrito.
                return;
            }
        }
        await this._doRefresh();
    }
}

registry.category("view_widgets").add("alarm_autorefresh", {
    component: AlarmWizardAutoRefresh,
});

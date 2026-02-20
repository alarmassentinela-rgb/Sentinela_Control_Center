/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

export class MonitoringDashboard extends Component {
    setup() {
        this.luxon = window.luxon || luxon || { DateTime: { now: () => new Date() } };
        this.state = useState({
            currentTab: 'alarms',
            events: [],
            signals: [],
            receiverStatus: 'offline', 
            lastHeartbeat: '---',
            priorities: {},
            now: this.luxon.DateTime.now(),
            alarmCount: 0,
            pendingCount: 0,
            isSounding: false,
        });
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = useService("bus_service");
        this.alarmSound = useService("sentinela_alarm_sound");
        
        onWillStart(async () => { 
            await this.loadPriorities();
            await this.loadData(); 
        });

        onMounted(() => {
            // Refresco de seguridad cada 10s por si falla el bus
            this.refreshInterval = setInterval(() => this.loadData(), 10000);
            this.timerInterval = setInterval(() => { 
                this.state.now = this.luxon.DateTime.now();
                this.state.isSounding = this.alarmSound.isSounding && this.alarmSound.isSounding();
            }, 1000);
            
            // ESCUCHAR EL BUS EN TIEMPO REAL
            this.busService.addChannel("sentinela_monitoring");
            this.busService.subscribe("sentinela_monitoring", (payload) => {
                console.log("SENTINELA: Señal de refresco recibida vía BUS", payload);
                this.loadData(); // Refresco INSTANTÁNEO
            });
        });

        onWillUnmount(() => {
            clearInterval(this.refreshInterval);
            clearInterval(this.timerInterval);
        });
    }

    async loadActiveEvents() {
        return this.loadData();
    }

    stopAllSounds() {
        if (this.alarmSound && this.alarmSound.stopAll) {
            this.alarmSound.stopAll();
        }
    }

    async viewHistory(account) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'sentinela.alarm.signal',
            name: `Historial de Cuenta ${account}`,
            view_mode: 'list,form',
            domain: [['device_id.name', 'ilike', account]],
            target: 'current'
        });
    }

    async loadPriorities() {
        const pData = await this.orm.searchRead("sentinela.alarm.priority", [], ["id", "name", "color_hex", "text_color_hex", "blink"]);
        pData.forEach(p => { this.state.priorities[p.id] = p; });
    }

    async setTab(tab) {
        this.state.currentTab = tab;
        await this.loadData();
    }

    async loadData() {
        try {
            // 1. CARGA DE CONTADORES GLOBALES (Independiente de la pestaña)
            const counts = await this.orm.call("sentinela.alarm.event", "read_group", [
                [["status", "in", ["active", "escalated", "paused", "in_progress"]]],
                ["status"],
                ["status"]
            ]);
            
            let active = 0;
            let pending = 0;
            counts.forEach(c => {
                if (c.status === 'active') active += c.status_count;
                else pending += c.status_count;
            });
            
            this.state.alarmCount = active;
            this.state.pendingCount = pending;

            // 2. Cargar Estado Receptor
            const status = await this.orm.call("sentinela.receiver.status", "get_status", []);
            this.state.receiverStatus = status.state;
            this.state.lastHeartbeat = status.last_seen;

            // 3. Cargar Datos de la Tabla
            let domain = [];
            if (this.state.currentTab === 'alarms') {
                domain = [["status", "=", "active"]];
            } else if (this.state.currentTab === 'pending') {
                domain = [["status", "in", ["in_progress", "paused", "escalated"]]];
            }
            
            if (domain.length > 0) {
                const rawEvents = await this.orm.searchRead("sentinela.alarm.event", domain, 
                    ["id", "status", "priority_id", "name", "device_id", "partner_id", "alarm_code_id", "description", "start_date", "zone"],
                    { order: "id desc", limit: 50 });

                this.state.events = rawEvents.map(e => {
                    const p = this.state.priorities[e.priority_id[0]] || {};
                    return {
                        id: e.id,
                        status: e.status,
                        account: e.device_id[1].split(' ')[0],
                        partner_name: e.partner_id ? e.partner_id[1] : 'Desconocido',
                        device_name: e.device_id[1],
                        style: `background-color: ${p.color_hex || '#fff'} !important; color: ${p.text_color_hex || '#000'} !important;`,
                        blink_class: p.blink ? 'fa-beat' : '',
                        priority_class: p.name ? p.name.toLowerCase() : 'normal',
                        time: e.start_date,
                        time_formatted: e.start_date,
                        code_display: e.alarm_code_id ? `[${e.alarm_code_id[1]}]` : '[---]',
                        description: e.description || '',
                        zone: e.zone || '000',
                        location: 'Ver Mapa'
                    };
                });
            } else if (this.state.currentTab === 'traffic') {
                const rawSignals = await this.orm.searchRead("sentinela.alarm.signal", [], 
                    ["id", "name", "device_id", "received_date", "signal_type", "description"],
                    { order: "id desc", limit: 50 });
                this.state.signals = rawSignals.map(s => ({
                    id: s.id,
                    account: s.device_id[1].split(' ')[0],
                    device_name: s.device_id[1],
                    time: s.received_date,
                    type: s.signal_type,
                    description: s.description || ''
                }));
            }
        } catch (e) { console.error("SENTINELA: Load Error", e); }
    }

    async handleAlarm(eventId) {
        this.alarmSound.stopAll();
        await this.orm.write("sentinela.alarm.event", [eventId], { status: 'in_progress' });
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'sentinela.alarm.handle.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: { 'default_alarm_event_id': eventId }
        }, { onClose: () => this.loadData() });
    }

    getRelativeTime(ts) {
        if (!ts) return '---';
        const date = this.luxon.DateTime.fromISO(ts.replace(' ', 'T'), { zone: 'utc' });
        const diff = this.state.now.toUTC().diff(date, ['minutes', 'seconds']);
        return `${Math.floor(Math.abs(diff.minutes))}m ${Math.floor(Math.abs(diff.seconds))}s`;
    }

    isOverdue(ts) {
        if (!ts) return false;
        const date = this.luxon.DateTime.fromISO(ts.replace(' ', 'T'), { zone: 'utc' });
        return this.state.now.toUTC().diff(date, 'minutes').minutes > 2;
    }
}

MonitoringDashboard.template = "sentinela_monitoring.MonitoringDashboard";
registry.category("actions").add("sentinela_monitoring.dashboard_client_action", MonitoringDashboard);

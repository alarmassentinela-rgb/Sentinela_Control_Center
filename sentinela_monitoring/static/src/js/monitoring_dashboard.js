/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

export class MonitoringDashboard extends Component {
    setup() {
        this.luxon = window.luxon || luxon;
        this.state = useState({
            currentTab: 'alarms',
            events: [],
            signals: [],
            receiverStatus: 'offline', 
            lastHeartbeat: '---',
            priorities: {},
            now: this.luxon.DateTime.now(),
        });
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = useService("bus_service");
        this.alarmSound = useService("sentinela_alarm_sound");
        
        onWillStart(async () => { await this.loadData(); });

        onMounted(() => {
            this.refreshInterval = setInterval(() => this.loadData(), 5000);
            this.timerInterval = setInterval(() => { this.state.now = this.luxon.DateTime.now(); }, 1000);
        });

        onWillUnmount(() => {
            clearInterval(this.refreshInterval);
            clearInterval(this.timerInterval);
        });
    }

    async setTab(tab) {
        this.state.currentTab = tab;
        await this.loadData();
    }

    async loadData() {
        try {
            // 1. Cargar Prioridades si no existen
            if (Object.keys(this.state.priorities).length === 0) {
                const pData = await this.orm.searchRead("sentinela.alarm.priority", [], ["id", "color_hex", "text_color_hex", "blink"]);
                pData.forEach(p => { this.state.priorities[p.id] = p; });
            }

            // 2. Cargar Estado Receptor
            const status = await this.orm.call("sentinela.receiver.status", "get_status", []);
            this.state.receiverStatus = status.state;
            this.state.lastHeartbeat = status.last_seen;

            // 3. Cargar Eventos (Sin filtros pesados)
            const domain = this.state.currentTab === 'alarms' ? 
                [["status", "in", ["active", "escalated"]]] : 
                [["status", "in", ["in_progress", "paused"]]];
            
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
                    time: e.start_date,
                    code_display: e.alarm_code_id ? `[${e.alarm_code_id[1]}]` : '[---]',
                    description: e.description || '',
                    zone: e.zone || '000'
                };
            });

            // 4. Cargar Tráfico
            if (this.state.currentTab === 'traffic') {
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

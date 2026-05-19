/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

export class MonitoringDashboard extends Component {
    setup() {
        this.state = useState({
            currentTab: 'alarms',
            trafficFilter: 'live',
            events: [],
            pendingEvents: [],
            signals: [],
            receiverStatus: 'offline', 
            lastHeartbeat: '---',
            alarmCount: 0,
            pendingCount: 0,
            loading: false,
            lastUpdate: new Date().toLocaleTimeString(),
            audioMuted: false,
        });
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = useService("bus_service");
        this.alarmSound = useService("sentinela_alarm_sound");
        
        onWillStart(async () => { 
            await this.loadData(); 
        });

        onMounted(() => {
            this.refreshInterval = setInterval(() => this.loadData(), 60000);
            this.busService.addChannel("sentinela_monitoring");
            this.busDebounce = null;
            
            this.busService.subscribe("notification", (notifications) => {
                if (!Array.isArray(notifications)) return;
                
                let found = false;
                for (const notif of notifications) {
                    if (notif.type === "sentinela_monitoring") {
                        found = true;
                        break;
                    }
                }

                if (found) {
                    if (this.busDebounce) clearTimeout(this.busDebounce);
                    // ACELERACIÓN: Solo 200ms de espera
                    this.busDebounce = setTimeout(() => {
                        if (!this.state.loading) this.loadData();
                    }, 200);
                }
            });
        });

        onWillUnmount(() => {
            clearInterval(this.refreshInterval);
            if (this.busDebounce) clearTimeout(this.busDebounce);
        });
    }

    async setTab(tab) {
        this.state.currentTab = tab;
        await this.loadData();
    }

    async setTrafficFilter(filter) {
        this.state.trafficFilter = filter;
        await this.loadData();
    }

    async loadData() {
        if (this.state.loading) return;
        this.state.loading = true;
        
        try {
            const data = await this.orm.call("sentinela.alarm.event", "get_dashboard_data", [], {
                current_tab: this.state.currentTab,
                traffic_filter: this.state.trafficFilter
            });
            if (!data) return;

            Object.assign(this.state, {
                receiverStatus: data.receiver ? data.receiver.state : 'offline',
                lastHeartbeat: data.receiver ? data.receiver.last_seen : '---',
                alarmCount: data.counts ? data.counts.alarms : 0,
                pendingCount: data.counts ? data.counts.pending : 0,
                events: (data.events || []).map(e => this._safeMap(e)),
                pendingEvents: (data.pending_events || []).map(e => this._safeMap(e)),
                signals: (data.signals || []),
                lastUpdate: new Date().toLocaleTimeString()
            });

            // F2.5 — re-evaluar audio con el estado fresco
            if (this.alarmSound) this.alarmSound.evaluate();

        } catch (e) {
            console.error("Dashboard Load Error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    toggleAudioMute() {
        if (!this.alarmSound) return;
        this.alarmSound.toggleMute();
        this.state.audioMuted = this.alarmSound.isMuted();
    }

    _safeMap(e) {
        return {
            id: e.id,
            partner_name: e.partner_name || 'Desconocido',
            account: e.account || '0000',
            code_display: e.code_display || '---',
            zone: e.zone || '000',
            status: e.status || 'active',
            is_blocked: e.is_blocked || false,
            start_date: e.start_date || '---'
        };
    }

    async handleAlarm(eventId) {
        if (!eventId) return;
        // F2.4: el wizard llama action_acknowledge en default_get para respetar
        // claim/SLA. NO escribir status='in_progress' aquí — eso saltaba el lock.
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'sentinela.alarm.handle.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: { 'default_alarm_event_id': eventId }
        }, { onClose: () => this.loadData() });
    }
}

MonitoringDashboard.template = "sentinela_monitoring.MonitoringDashboard";
registry.category("actions").add("sentinela_monitoring.dashboard_client_action", MonitoringDashboard);

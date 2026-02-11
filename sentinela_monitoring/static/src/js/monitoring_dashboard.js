/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

export class MonitoringDashboard extends Component {
    setup() {
        this.luxon = window.luxon || luxon;
        this.state = useState({
            currentTab: 'alarms', // 'alarms', 'traffic', 'pending'
            events: [],
            signals: [],
            receiverStatus: 'offline', 
            lastHeartbeat: 'Nunca',
            now: this.luxon.DateTime.now(),
            audioUnlocked: false,
            isSounding: false,
            isReminderPlaying: false
        });
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = useService("bus_service");
        
        this.audioPlayer = new Audio(); // Reproductor de Sirena
        this.audioPlayer.loop = true;

        this.reminderPlayer = new Audio("/sentinela_monitoring/static/src/audio/reminder.mp3"); // Reproductor Suave
        this.reminderPlayer.loop = false;
        
        this.refreshInterval = null;
        this.timerInterval = null;

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this.busService.addEventListener("notification", this.onNotification.bind(this));
            this.busService.addChannel("broadcast");
            this.refreshInterval = setInterval(() => { this.loadData(); this.checkReceiverStatus(); }, 5000);
            this.timerInterval = setInterval(() => { this.state.now = this.luxon.DateTime.now(); }, 1000);
        });

        onWillUnmount(() => {
            this.stopAllSounds();
            if (this.refreshInterval) clearInterval(this.refreshInterval);
            if (this.timerInterval) clearInterval(this.timerInterval);
        });
    }

    async setTab(tab) {
        this.state.currentTab = tab;
        await this.loadData();
    }

    async loadData() {
        await this.loadActiveEvents();
        if (this.state.currentTab === 'traffic') {
            await this.loadSignals();
        }
    }

    // --- AUDIO CONTROL ---
    async unlockAudio() {
        this.audioPlayer.src = "/sentinela_monitoring/static/src/audio/siren_high.mp3";
        this.audioPlayer.play().then(() => {
            this.state.audioUnlocked = true;
            this.audioPlayer.pause();
        });
    }

    stopAllSounds() {
        this.audioPlayer.pause();
        this.reminderPlayer.pause();
        this.state.isSounding = false;
        this.state.isReminderPlaying = false;
    }

    playSiren(priorityId) {
        if (!this.state.audioUnlocked) return;
        const url = `/web/content?model=sentinela.alarm.priority&id=${priorityId}&field=priority_sound`;
        if (this.state.isSounding && this.audioPlayer.src.includes(`id=${priorityId}`)) return;
        
        this.reminderPlayer.pause();
        this.audioPlayer.src = url;
        this.audioPlayer.loop = true;
        this.audioPlayer.play().then(() => { this.state.isSounding = true; });
    }

    playSoftReminder() {
        if (!this.state.audioUnlocked || this.state.isSounding) return;
        // Tocar un pequeño ping cada vez que se refresca si hay pendientes
        this.reminderPlayer.volume = 0.3;
        this.reminderPlayer.play().catch(e => {});
    }

    async loadActiveEvents() {
        try {
            const fields = ["id", "status", "priority_id", "name", "device_id", "account_number", "alarm_code_id", "description", "start_date", "location", "zone"];
            
            // Determinar dominio según pestaña o cargar todos para lógica de sonido
            const domain = [["status", "in", ["active", "in_progress", "paused", "escalated"]]];
            
            const events = await this.orm.searchRead(
                "sentinela.alarm.event",
                domain,
                fields,
                { order: "priority_id desc, start_date desc", limit: 100 }
            );
            
            // --- LOGICA DE SONIDO INTELIGENTE (Siempre corre basándose en todos los eventos) ---
            const inProgress = events.some(e => e.status === 'in_progress');
            const activeAlarms = events.filter(e => e.status === 'active');
            const pausedAlarms = events.filter(e => e.status === 'paused');

            if (inProgress) {
                this.stopAllSounds();
            } else if (activeAlarms.length > 0) {
                this.playSiren(activeAlarms[0].priority_id[0]);
            } else if (pausedAlarms.length > 0) {
                this.audioPlayer.pause();
                this.state.isSounding = false;
                this.playSoftReminder();
            } else {
                this.stopAllSounds();
            }

            // --- FILTRADO PARA LA VISTA ---
            let filteredEvents = events;
            if (this.state.currentTab === 'alarms') {
                filteredEvents = events.filter(e => e.status === 'active');
            } else if (this.state.currentTab === 'pending') {
                filteredEvents = events.filter(e => ['in_progress', 'paused', 'escalated'].includes(e.status));
            }

            this.state.events = filteredEvents.map(e => {
                let urgency = 'normal';
                let pName = e.priority_id ? e.priority_id[1].toLowerCase() : '';
                if (pName.includes('critica') || pName.includes('p1')) urgency = 'critical';
                else if (pName.includes('alta') || pName.includes('p2')) urgency = 'high';

                return {
                    id: e.id,
                    status: e.status,
                    account: e.account_number || '???',
                    device_name: e.device_id ? e.device_id[1] : 'Desconocido',
                    priority_class: urgency,
                    time: e.start_date,
                    time_formatted: e.start_date,
                    zone: e.zone,
                    code_display: e.alarm_code_id ? `[${e.alarm_code_id[1]}]` : 'CODE ???',
                    description: e.description || '',
                    location: e.location || 'Sin ubicación'
                };
            });
        } catch (e) { console.error(e); }
    }

    async loadSignals() {
        try {
            const signals = await this.orm.searchRead(
                "sentinela.alarm.signal",
                [],
                ["id", "name", "account_number", "device_id", "received_date", "signal_type", "description"],
                { order: "received_date desc", limit: 50 }
            );
            this.state.signals = signals.map(s => ({
                id: s.id,
                account: s.account_number || '???',
                device_name: s.device_id ? s.device_id[1] : 'Desconocido',
                time: s.received_date,
                type: s.signal_type,
                description: s.description || ''
            }));
        } catch (e) { console.error(e); }
    }

    async checkReceiverStatus() {
        try {
            const status = await this.orm.call("sentinela.receiver.status", "get_status", []);
            this.state.receiverStatus = status.state;
            this.state.lastHeartbeat = status.last_seen;
        } catch (e) {}
    }

    onNotification(notifications) { this.loadData(); }

    async handleAlarm(eventId) {
        this.stopAllSounds();
        try {
            await this.orm.write("sentinela.alarm.event", [eventId], { status: 'in_progress' });
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Atender Alarma',
                res_model: 'sentinela.alarm.handle.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: { 'default_alarm_event_id': eventId }
            }, { onClose: () => this.loadActiveEvents() });
            await this.loadActiveEvents();
        } catch (e) {}
    }

    async viewHistory(accountNumber) {
        if (!accountNumber) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: `Historial: ${accountNumber}`,
            res_model: 'sentinela.alarm.event',
            view_mode: 'list,form',
            domain: [['account_number', '=', accountNumber], ['status', '=', 'resolved']],
            target: 'current',
        });
    }

    getRelativeTime(timestamp) {
        if (!timestamp) return '---';
        try {
            // Odoo devuelve UTC. Convertimos a objeto DateTime de Luxon
            const date = this.luxon.DateTime.fromISO(timestamp.replace(' ', 'T'), { zone: 'utc' });
            const diff = this.state.now.toUTC().diff(date, ['minutes', 'seconds']);
            const mins = Math.floor(Math.abs(diff.minutes));
            const secs = Math.floor(Math.abs(diff.seconds));
            return `${mins}m ${secs}s`;
        } catch (e) {
            return 'err';
        }
    }

    isOverdue(timestamp) {
        if (!timestamp) return false;
        try {
            const date = this.luxon.DateTime.fromISO(timestamp.replace(' ', 'T'), { zone: 'utc' });
            const diff = this.state.now.toUTC().diff(date, 'minutes').minutes;
            return diff > 2; // Más de 2 minutos sin atender es crítico
        } catch (e) {
            return false;
        }
    }
}

MonitoringDashboard.template = "sentinela_monitoring.MonitoringDashboard";
registry.category("actions").add("sentinela_monitoring.dashboard_client_action", MonitoringDashboard);

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const alarmService = {
    dependencies: ["bus_service", "orm", "notification"],
    start(env, { bus_service, orm, notification }) {
        const audioPlayer = new Audio();
        let audioUnlocked = false;
        let isSirenPlaying = false;

        console.log("SENTINELA: Servicio de Alarma Iniciado");

        const unlock = () => {
            if (audioUnlocked) return;
            audioPlayer.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";
            audioPlayer.play().then(() => {
                audioUnlocked = true;
                console.log("SENTINELA: Audio Desbloqueado");
                document.removeEventListener('click', unlock);
            });
        };
        document.addEventListener('click', unlock);

        const playSiren = (priorityId) => {
            if (!audioUnlocked || !priorityId) return;
            const url = `/web/content?model=sentinela.alarm.priority&id=${priorityId}&field=priority_sound`;
            if (isSirenPlaying && audioPlayer.src.includes(`id=${priorityId}`)) return;
            
            audioPlayer.pause();
            audioPlayer.src = url;
            audioPlayer.loop = true;
            audioPlayer.play().then(() => { isSirenPlaying = true; });
        };

        const stopAll = () => {
            audioPlayer.pause();
            audioPlayer.src = "";
            isSirenPlaying = false;
        };

        const checkSystem = async () => {
            try {
                const events = await orm.searchRead("sentinela.alarm.event", 
                    [["status", "in", ["active", "escalated"]]], 
                    ["priority_id"], { order: "priority_id desc", limit: 1 });
                
                if (events.length > 0) {
                    playSiren(events[0].priority_id[0]);
                } else {
                    stopAll();
                }
            } catch (e) { console.error("SENTINELA: Check Error", e); }
        };

        // Escuchar el canal específico
        bus_service.addChannel("sentinela_monitoring");
        bus_service.subscribe("sentinela_monitoring", (payload) => {
            console.log("SENTINELA: Notificación recibida", payload);
            checkSystem();
        });

        setInterval(checkSystem, 10000);

        return { stopAll, checkSystem };
    },
};

registry.category("services").add("sentinela_alarm_sound", alarmService);

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const alarmService = {
    dependencies: ["bus_service", "orm"],
    start(env, { bus_service, orm }) {
        const audioPlayer = new Audio();
        let audioUnlocked = false;
        let isSirenPlaying = false;
        let currentMode = ""; // 'SIRENA' o 'REMINDER' o 'SILENCIO'

        console.log("SENTINELA: Cerebro de Sonido V5.0 (Estructura Simplificada) Activo");

        const unlock = () => {
            if (audioUnlocked) return;
            audioPlayer.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";
            audioPlayer.play().then(() => {
                audioUnlocked = true;
                console.log("SENTINELA: Audio listo para alertas.");
                document.removeEventListener('click', unlock);
                checkSystem();
            });
        };
        document.addEventListener('click', unlock);

        const applySound = async (mode, priorityId = null) => {
            if (!audioUnlocked || currentMode === mode) return;

            console.log(`SENTINELA: >>> CAMBIO DE ESTADO: ${currentMode} -> ${mode} <<<`);
            
            let audioData = "";
            if (mode === 'SIRENA' && priorityId) {
                // Leer audio de la prioridad desde Odoo
                const res = await orm.searchRead("sentinela.alarm.priority", [["id", "=", priorityId]], ["priority_sound"]);
                if (res.length > 0) audioData = res[0].priority_sound;
            } else if (mode === 'REMINDER') {
                // Leer audio global de recordatorio
                audioData = await orm.call("ir.config_parameter", "get_param", ["sentinela.global_alarm_sound"]);
            }

            if (audioData) {
                audioPlayer.pause();
                audioPlayer.src = "data:audio/wav;base64," + audioData;
                audioPlayer.loop = true;
                await audioPlayer.play();
                isSirenPlaying = true;
                currentMode = mode;
            } else {
                stopAll();
            }
        };

        const stopAll = () => {
            audioPlayer.pause();
            audioPlayer.src = "";
            isSirenPlaying = false;
            currentMode = "SILENCIO";
        };

        const checkSystem = async () => {
            try {
                // 1. Contar estados en una sola llamada
                const activeCount = await orm.searchCount("sentinela.alarm.event", [["status", "=", "active"]]);
                const pendingCount = await orm.searchCount("sentinela.alarm.event", [["status", "in", ["escalated", "paused", "in_progress"]]]);

                if (activeCount > 0) {
                    // Prioridad absoluta a la sirena. Buscamos el ID de la prioridad más alta de las activas.
                    const alarms = await orm.searchRead("sentinela.alarm.event", [["status", "=", "active"]], ["priority_id"], {order: "priority_id desc", limit: 1});
                    if (alarms.length > 0) {
                        await applySound('SIRENA', alarms[0].priority_id[0]);
                    }
                } else if (pendingCount > 0) {
                    // Solo si no hay sirenas, entra el recordatorio
                    await applySound('REMINDER');
                } else {
                    stopAll();
                }
            } catch (e) {
                console.error("SENTINELA: Error en monitor de sonido", e);
            }
        };

        // Escuchar refrescos del receptor
        bus_service.addChannel("sentinela_monitoring");
        bus_service.subscribe("sentinela_monitoring", () => { checkSystem(); });

        // Ciclo rápido de seguridad (2 segundos)
        setInterval(checkSystem, 2000);

        return { stopAll, checkSystem };
    },
};

registry.category("services").add("sentinela_alarm_sound", alarmService);

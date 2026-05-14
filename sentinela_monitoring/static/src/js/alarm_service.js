/** @odoo-module **/

import { registry } from "@web/core/registry";

export const alarmService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        // SERVICIO DESACTIVADO TEMPORALMENTE PARA RESTAURAR ESTABILIDAD
        console.log("SENTINELA: Servicio de Sonido en Modo Silencio (Rescate)");

        const stopAll = () => { console.log("Sonido detenido"); };
        const checkSystem = () => { /* No hacer nada */ };

        return { stopAll, checkSystem };
    },
};

registry.category("services").add("sentinela_alarm_sound", alarmService);

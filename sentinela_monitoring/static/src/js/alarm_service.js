/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Sentinela Alarm Audio Service (F2.5)
 *
 * Lee el estado de eventos vía sentinela.alarm.event.get_audio_state(),
 * elige la alarma de mayor prioridad NO claimed por el usuario actual,
 * y reproduce su sonido en loop. Si la prioridad tiene is_reminder=True,
 * reproduce una vez cada 30s en lugar de loop continuo.
 *
 * Buttons en el dashboard llaman a stopAll() o toggleMute() de este servicio.
 *
 * Autoplay note: la mayoría de browsers requieren un gesto de usuario antes
 * de reproducir audio. El dashboard se abre por click, eso suele bastar.
 * Si play() rechaza, lo logueamos y seguimos — el operador escuchará al
 * abrir el primer wizard manualmente.
 */
export const alarmService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const audioCache = new Map();      // priorityId -> HTMLAudioElement
        let currentPriorityId = null;
        let currentAudio = null;
        let reminderTimer = null;
        let mutedUntil = 0;                // epoch ms — mute con desactivación automática
        let lastEvaluatedAt = 0;

        const MUTE_DURATION_MS = 5 * 60 * 1000;       // 5 minutos por click de mute
        const REMINDER_INTERVAL_MS = 30 * 1000;       // recordatorios cada 30s
        // Sonido tenue para cuando el operador está atendiendo (hablando por
        // teléfono): las demás alarmas no gritan la sirena, solo recuerdan suave.
        const SOFT_URL = "/sentinela_monitoring/static/src/sounds/reminder.wav";
        const SOFT_VOLUME = 0.35;

        const stopCurrent = () => {
            if (currentAudio) {
                try {
                    currentAudio.pause();
                    currentAudio.currentTime = 0;
                } catch (e) { /* noop */ }
            }
            currentAudio = null;
            currentPriorityId = null;
            if (reminderTimer) {
                clearInterval(reminderTimer);
                reminderTimer = null;
            }
        };

        const getOrCreateAudio = (priorityId, soundUrl) => {
            if (audioCache.has(priorityId)) return audioCache.get(priorityId);
            const audio = new Audio(soundUrl);
            audio.preload = "auto";
            audioCache.set(priorityId, audio);
            return audio;
        };

        const playPriority = (target) => {
            const audio = getOrCreateAudio(target.priority_id, target.sound_url);
            const soft = Boolean(target.is_reminder);   // modo tenue (atendiendo)
            audio.loop = !soft;
            audio.volume = soft ? SOFT_VOLUME : 1.0;
            audio.currentTime = 0;
            const playPromise = audio.play();
            if (playPromise && playPromise.catch) {
                playPromise.catch((err) =>
                    console.warn("[sentinela-audio] play() bloqueado:", err.message));
            }
            currentAudio = audio;
            currentPriorityId = target.priority_id;

            if (soft) {
                reminderTimer = setInterval(() => {
                    try {
                        audio.currentTime = 0;
                        audio.play().catch(() => {});
                    } catch (e) { /* noop */ }
                }, REMINDER_INTERVAL_MS);
            }
        };

        const evaluate = async () => {
            lastEvaluatedAt = Date.now();
            if (Date.now() < mutedUntil) {
                stopCurrent();
                return;
            }
            let data;
            try {
                data = await orm.call("sentinela.alarm.event", "get_audio_state", []);
            } catch (e) {
                console.warn("[sentinela-audio] get_audio_state falló:", e);
                return;
            }
            const eligible = (data.active_alarms || []).filter(
                (a) => a.has_sound && !a.is_claimed_by_me
            );
            // menor priority_level primero (1 = la más importante / sirena)
            eligible.sort((a, b) => (a.priority_level || 999) - (b.priority_level || 999));
            const top = eligible[0];

            if (!top) {
                stopCurrent();
                return;
            }
            // Si el operador está atendiendo un evento (lo tomó), las DEMÁS alarmas
            // no gritan la sirena: suenan tenue (reminder, bajo y cada 30s) para que
            // pueda hablar por teléfono. Al cerrar/soltar su evento, vuelve la sirena.
            const target = data.attending
                ? { priority_id: "__soft__", sound_url: SOFT_URL, is_reminder: true }
                : top;
            // si ya estamos tocando lo mismo, no reiniciar
            if (currentPriorityId === target.priority_id && currentAudio) return;
            stopCurrent();
            playPriority(target);
        };

        const stopAll = () => {
            stopCurrent();
        };

        const toggleMute = () => {
            const now = Date.now();
            if (mutedUntil > now) {
                mutedUntil = 0;
                evaluate();
            } else {
                mutedUntil = now + MUTE_DURATION_MS;
                stopCurrent();
            }
            return mutedUntil > Date.now();
        };

        const isMuted = () => Date.now() < mutedUntil;

        const isPlaying = () => Boolean(currentAudio);

        return { evaluate, stopAll, toggleMute, isMuted, isPlaying };
    },
};

registry.category("services").add("sentinela_alarm_sound", alarmService);

/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class TrafficGraph extends Component {
    setup() {
        this.orm = useService("orm");
        this.canvasRef = useRef("canvas");
        this.chart = null;
        this.intervalId = null;

        this.state = useState({
            rx_speed: 0,
            tx_speed: 0,
            current_ip: "—",
            status: "Iniciando...",
        });

        // Carga Chart.js LOCAL de Odoo (no CDN externo)
        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
        });

        onMounted(() => {
            this.initChart();
            this.startPolling();
        });

        onWillUnmount(() => {
            if (this.intervalId) clearInterval(this.intervalId);
            if (this.chart) this.chart.destroy();
        });
    }

    initChart() {
        try {
            if (typeof Chart === "undefined") {
                this.state.status = "Error: Chart.js no cargó";
                return;
            }
            const ctx = this.canvasRef.el.getContext("2d");
            this.chart = new Chart(ctx, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [
                        { label: "⬇ Bajada Mbps", data: [], borderColor: "#28a745", backgroundColor: "rgba(40,167,69,.1)", tension: 0.3, fill: true },
                        { label: "⬆ Subida Mbps", data: [], borderColor: "#007bff", backgroundColor: "rgba(0,123,255,.1)", tension: 0.3, fill: true },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { boxWidth: 12, font: { size: 10 } } } },
                    scales: { y: { beginAtZero: true } },
                    animation: { duration: 0 },
                },
            });
        } catch (e) {
            this.state.status = "Error graficador";
        }
    }

    startPolling() {
        this.fetchData();
        this.intervalId = setInterval(() => this.fetchData(), 4000);
    }

    async fetchData() {
        const recId = this.props.record && this.props.record.resId;
        if (!recId) {
            this.state.status = "Guarda el registro primero";
            return;
        }
        try {
            const result = await this.orm.call("sentinela.subscription", "get_live_traffic", [[recId]]);
            this.state.rx_speed = result.rx;
            this.state.tx_speed = result.tx;
            this.state.current_ip = result.ip;
            this.state.status = result.status;
            if (!this.chart) {
                if (this.canvasRef.el) this.initChart();
                return;
            }
            const now = new Date().toLocaleTimeString();
            this.chart.data.labels.push(now);
            this.chart.data.datasets[0].data.push(result.rx);
            this.chart.data.datasets[1].data.push(result.tx);
            if (this.chart.data.labels.length > 20) {
                this.chart.data.labels.shift();
                this.chart.data.datasets[0].data.shift();
                this.chart.data.datasets[1].data.shift();
            }
            this.chart.update();
        } catch (error) {
            this.state.status = "Error de conexión";
        }
    }
}

TrafficGraph.template = "sentinela_subscriptions.TrafficGraph";

export const trafficGraphField = { component: TrafficGraph };
registry.category("fields").add("traffic_graph", trafficGraphField);

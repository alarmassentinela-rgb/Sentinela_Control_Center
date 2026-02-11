/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

export class TrafficGraph extends Component {
    setup() {
        this.orm = useService("orm");
        this.canvasRef = useRef("canvas");
        this.chart = null;
        this.intervalId = null;
        
        this.state = useState({
            rx_speed: 0,
            tx_speed: 0,
            current_ip: "Cargando...",
            status: "Iniciando...",
        });

        // Removed loadBundle as we use direct CDN script

        onMounted(() => {
            this.waitForChart();
        });

        onWillUnmount(() => {
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    waitForChart() {
        if (typeof Chart !== 'undefined') {
            this.initChart();
            this.startPolling();
        } else {
            // Retry every 100ms
            setTimeout(() => this.waitForChart(), 100);
        }
    }

    initChart() {
        try {
            const ctx = this.canvasRef.el.getContext("2d");
            
            // Safety check for Chart.js
            if (typeof Chart === 'undefined') {
                this.state.status = "Error: Chart.js no cargó";
                console.error("Chart.js is not defined in the global scope.");
                return;
            }

            this.chart = new Chart(ctx, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: "Bajada (Rx) Mbps",
                            data: [],
                            borderColor: "green",
                            tension: 0.3,
                            fill: false
                        },
                        {
                            label: "Subida (Tx) Mbps",
                            data: [],
                            borderColor: "blue",
                            tension: 0.3,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    animation: {
                        duration: 0 
                    }
                }
            });
        } catch (e) {
            console.error("Error initializing Chart:", e);
            this.state.status = "Error Graficador";
        }
    }

    startPolling() {
        // Initial Fetch
        this.fetchData();
        // Loop every 5 seconds
        this.intervalId = setInterval(() => this.fetchData(), 5000);
    }

    async fetchData() {
        try {
            // "this.props.record.resId" gives the Wizard ID
            const result = await this.orm.call(
                "sentinela.mikrotik.traffic",
                "fetch_traffic_stats",
                [this.props.record.resId]
            );
            
            console.log("Traffic Data:", result); // Debugging

            // Update State
            this.state.rx_speed = result.rx;
            this.state.tx_speed = result.tx;
            this.state.current_ip = result.ip;
            this.state.status = result.status; // Always show backend status

            // Safety Check: Chart might not be ready yet
            if (!this.chart) {
                console.warn("Chart not initialized yet, skipping draw.");
                // Try to init if canvas is available
                if (this.canvasRef.el) {
                     this.initChart();
                }
                return;
            }

            // Update Chart
            const now = new Date().toLocaleTimeString();
            this.chart.data.labels.push(now);
            this.chart.data.datasets[0].data.push(result.rx);
            this.chart.data.datasets[1].data.push(result.tx);

            // Keep only last 20 points
            if (this.chart.data.labels.length > 20) {
                this.chart.data.labels.shift();
                this.chart.data.datasets[0].data.shift();
                this.chart.data.datasets[1].data.shift();
            }

            this.chart.update();

        } catch (error) {
            console.error("Traffic Graph Error:", error);
            this.state.status = "Error JS: Ver consola";
        }
    }
}

TrafficGraph.template = "sentinela_subscriptions.TrafficGraph";

// Register as a field widget
export const trafficGraphField = {
    component: TrafficGraph,
};

registry.category("fields").add("traffic_graph", trafficGraphField);

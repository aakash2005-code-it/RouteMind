# RouteMind — Intelligent Self-Healing Network Routing Laboratory

RouteMind is a full-stack academic prototype with an HTML/CSS/JavaScript frontend, Python Flask REST backend, and a routing algorithm engine. It demonstrates adaptive path selection, link failures, congestion, transparent shortest-path comparison and reproducible packet-loss experiments.

## Quick start (Windows VS Code / PowerShell)

```powershell
cd RouteMind
py -m pip install -r requirements.txt
py run.py
```

Open http://127.0.0.1:5055 . This port is deliberately different from the NetPulse / ClosetOS 5000 port.

## Linux / macOS

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

## Tests

```powershell
py -m unittest discover -s tests -v
```

## Live demonstration sequence

1. Show A → B → D → F as the default minimum-latency route.
2. Click **Fail primary link** (disables B–D); watch the line turn red and the route recompute immediately.
3. Restore B–D. Click **Inject congestion** (raises utilization on A–B); adaptive path may change while latency-only routing stays the same.
4. Choose **Real-time / Video** or **Bulk Transfer** to show how the adaptive weights change optimization.
5. Use Link Inspector to alter latency, loss, utilization, capacity and connectivity; recalculate and review algorithm comparison.
6. Run the seeded packet delivery experiment with 500 packets, then vary loss on one link, rerun with the same seed, and compare results.
7. Show backend routes in app.py and algorithm in engine.py; show event timeline and unit tests.

## Algorithm

- **Minimum hops:** Dijkstra with unit cost for each operational link (same optimization goal as BFS).
- **Lowest latency:** Dijkstra minimizing sum of per-link latency.
- **Adaptive:** Dijkstra minimizing `w_delay * latency_ms + w_loss * loss_pct + w_congestion * 100 * (utilization_pct/100)^2` summed along the path. Weights depend on selected traffic profile and can be inspected in `engine.py`.
- Route loss approximates independent loss probabilities across hops; capacity is an estimated bottleneck of per-link residual bandwidth. These are **model assumptions**.
- Packet experiments sample independent drops with a specified pseudorandom seed and compute modeled delay, not OS packet forwarding.

## Source structure

- `app.py`: Flask REST endpoints, topology state and event timeline.
- `engine.py`: shortest-path routing and deterministic simulation.
- `templates/index.html`: complete dashboard layout.
- `static/app.js`: interactive topology, API requests, event displays and forms.
- `static/style.css`: responsive visual design.
- `tests/test_engine.py`: route correctness and recovery checks.

## REST API

- `GET /api/state`: all links, nodes, events and version.
- `POST /api/route`: body `{"source":"A","target":"F","algorithm":"adaptive","profile":"balanced"}`.
- `POST /api/link/BD`: body `{"up":false}` or e.g. `{"utilization":90}`.
- `POST /api/reset`: restore original topology.
- `POST /api/simulate`: body `{"source":"A","target":"F","algorithm":"adaptive","profile":"balanced","packets":500,"seed":42}`.

## Scope and academic honesty

The Python algorithms, API requests, link modifications, and routing decisions are **real working software**. Network links, packet drops, latency, and congestion are **modeled**, not read from physical routers. This release is a discrete routing/packet model and DOES NOT manipulate real routing tables, transmit IP packets between simulated routers, apply SDN rules, or reproduce physical network performance. To demonstrate actual Linux network traffic, extend the project with Mininet inside an Ubuntu VM and measure ping/iperf results separately.

## Novelty positioning

Adaptive routing and application-aware traffic steering already exist in commercial products (e.g., Cisco SD-WAN). RouteMind's defensible contribution as a course project is the integrated **explainable multi-metric cost model**, three verifiable algorithm baselines, interactive fault injection, deterministic trial reproduction, and readable Python implementations. Any claim of superior latency or resilience requires controlled benchmark evidence, not just choosing a different objective function.

## Safety

Runs locally on `127.0.0.1:5055`, does not require admin permissions or affect your machine's network settings. Development Flask server is not intended for production exposure.

## Version 2 — Advanced Engineering Lab

The **Advanced Lab** section extends the original interactive topology and packet model:

- **Explainable route scoring:** inspect the link-by-link objective costs and possible alternatives after removing an edge.
- **20-run benchmarks:** compare hop count, latency, and adaptive algorithms using paired, fixed random seeds. Adjust runs (1–100) and packets (1–2000). Download per-run results as CSV. Results represent independently modeled packet loss and delay, not observed IP traffic.
- **Single-link failure sweep:** disable each currently available edge in a temporary topology copy and report which destinations remain reachable. Does not disturb the displayed network.
- **Topology editor:** add up to 20 nodes, connect nodes with links, and delete nodes/links. Topology state is in process memory; restarting Flask restores the defaults.
- **Export buttons:** save topology JSON or event logs as CSV for reports and screenshots.

**Updated APIs:** `POST /api/explain`, `POST /api/benchmark`, `POST /api/resilience`, `POST /api/topology/node`, `POST /api/topology/edge`, `DELETE /api/topology/node/<id>`, `DELETE /api/topology/edge/<id>`, `GET /api/export/topology`, `GET /api/export/events`.

Run all tests with `py -m unittest discover -s tests -v` on Windows.

### Important scientific limitations

This is a controlled routing and packet-loss **model**, not real IP forwarding, Mininet emulation, or an installed commercial router controller. The latency and loss values are scenario inputs. Modeled experiments can demonstrate internal algorithm behavior but cannot establish superior real-world networking performance. A later independent Linux/Mininet integration would be required for real network measurements.

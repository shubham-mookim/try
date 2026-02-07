# Agent Compute Negotiation

Autonomous agents that negotiate with each other for compute resources (GPU time, memory, CPU cycles) through a decentralized protocol. No central authority — just agents making deals based on their needs, resources, and trust relationships.

## Quick Start

```bash
pip install matplotlib

# Run all experiments
python run_all.py

# Run individually
python run_all.py 1   # Basic Handshake
python run_all.py 2   # Scarcity Games
python run_all.py 3   # Trust Fall
```

## Project Structure

```
agents/
  protocol.py    - Message types (REQUEST, OFFER, COUNTER, ACCEPT, REJECT, ...)
  resource.py    - Abstract compute units (GPU hours, CPU hours, memory)
  agent.py       - Core Agent class with reputation tracking
  strategies.py  - Negotiation strategies (Greedy, Fair, Patient, Adaptive, Broker)
  simulator.py   - Simulation engine that runs negotiation rounds

experiments/
  exp1_handshake.py  - Two agents, one negotiation
  exp2_scarcity.py   - 5 agents competing for scarce resources
  exp3_trust.py      - Reputation and cheater detection
  visualize.py       - Matplotlib plots for results

run_all.py           - Run everything
```

## Experiments

### Experiment 1: The Basic Handshake

Two agents negotiate compute. Tests every strategy combination and tracks price convergence between adaptive agents.

**Key finding:** Fair and Adaptive strategies are the only ones that successfully close deals with each other. Greedy and Patient strategies deadlock — neither is willing to meet in the middle. Two Adaptive agents converge to a stable price within ~30 rounds (volatility drops to near zero).

### Experiment 2: Scarcity Games

5 agents (3 providers, 2 seekers) compete over 100 rounds. Includes a "rush hour" scenario where everyone suddenly needs compute, and a tournament ranking strategies by accumulated wealth.

**Key finding:** Fair providers dominate the tournament — they close the most deals and accumulate the most wealth. Greedy providers barely trade at all. The Adaptive seeker outperforms the Greedy seeker by learning market prices. During rush hour, deal success rate drops and prices spike.

### Experiment 3: Trust Fall

6 agents including one cheater. Tests whether the network can isolate dishonest actors using decentralized reputation tracking.

**Key finding:** Always-cheating agents get detected and isolated within 10-15 rounds. BUT they still profit short-term (higher final wealth from stolen resources). Subtle cheaters (5% cheat rate) fly under the radar — their reputation actually *improves* over time because successful deals outweigh occasional defaults. This is the interesting case.

## Strategies

| Strategy | Approach | When it wins |
|----------|----------|--------------|
| **Greedy** | Lowballs buyers, demands premium from sellers | Rarely — deadlocks too often |
| **Fair** | Targets market-rate prices, splits differences | Most situations — closes deals consistently |
| **Patient** | Waits for bargains, sells at premium | Low-demand environments |
| **Adaptive** | Learns price from deal history, adjusts beliefs | Markets with stable pricing |
| **Broker** | Middleman that takes a commission | When supply and demand are separated |

## What's Next

See the exploration doc for Phase 4 (Predictive Negotiation) and Phase 5 (Coalition & Coordination). Interesting next experiments:

- **LLM-powered agents** that negotiate in natural language
- **Coalition formation** — agents pooling resources and splitting profits
- **Compute futures** — agents trading rights to compute they don't own yet
- **Mixed intelligence** — what happens when an LLM agent negotiates with rule-based ones?

# Shor 9-Qubit QEC — Project Strategy

## What We're Building
A full implementation of Shor's 9-qubit quantum error correction code in Qiskit, ending
with noise model experiments that show the code's error suppression capability.

---

## Architecture

The Shor code is a concatenation of two repetition codes:

- **Inner layer (bit-flip protection):** each logical qubit becomes a 3-qubit repetition code
- **Outer layer (phase-flip protection):** that 3-qubit block is itself repeated 3× with a Hadamard basis change

Result: 1 logical qubit → 9 physical qubits. Corrects any single-qubit X, Z, or Y error.

Circuit shape:
```
encode() → [inject error] → syndrome_x_measurement() → syndrome_z_measurement()
        → correct(syndrome_bits) → verify
```

All syndrome measurement is classical postprocessing (not mid-circuit feedback). Syndrome
functions extend the circuit in-place via `add_register()`.

---

## Phase 1 — Encoding (DONE)

### `encode()` ✓
- Initialises q[0] to a random |ψ⟩ = α|0⟩ + β|1⟩ (random θ, φ)
- Outer phase-flip layer: CX(0→3), CX(0→6), then H on [0,3,6]
- Inner bit-flip layer: CX from each block head to its two companions
- Returns 9-qubit QuantumCircuit

---

## Phase 2 — Syndrome Measurement (DONE)

### `syndrome_x_measurement(qc)` ✓
Detects bit-flip (X) errors. Adds 6 ancilla qubits (a[0]–a[5]) and 6 classical bits.

| Ancilla | Checks | Detects |
|---------|--------|---------|
| a[0] | q0 ⊕ q1 | error in q0 or q1 |
| a[1] | q1 ⊕ q2 | error in q1 or q2 |
| a[2] | q3 ⊕ q4 | error in q3 or q4 |
| a[3] | q4 ⊕ q5 | error in q4 or q5 |
| a[4] | q6 ⊕ q7 | error in q6 or q7 |
| a[5] | q7 ⊕ q8 | error in q7 or q8 |

Syndrome decoding per block: `00`→no error, `10`→left qubit, `11`→middle qubit, `01`→right qubit.

### `syndrome_z_measurement(qc)` ✓
Detects phase-flip (Z) errors. Adds 2 ancilla qubits and 2 classical bits. Uses H-sandwich CX pattern.

| Ancilla | Checks |
|---------|--------|
| za[0] | block 0 vs block 1 |
| za[1] | block 1 vs block 2 |

Syndrome decoding: `00`→no error, `10`→block 0, `11`→block 1, `01`→block 2.

### Tests ✓
| Case | Expected syndrome | Status |
|------|-------------------|--------|
| No error | `00 000000` | Pass |
| X on q1 (mid block 0) | `00 000011` | Pass |
| Z on q3 (block 1) | `11 000000` | Pass |

---

## Phase 3 — Correction & Decode (DONE)

### `correct(syndrome_bits)`
Classical lookup: reads the 8-bit syndrome string, applies corrective gates.

X-syndrome lookup (per block, 2 bits each):
```
00 → no op
10 → X on left qubit of block
11 → X on middle qubit of block
01 → X on right qubit of block
```

Z-syndrome lookup (2 bits total):
```
00 → no op
10 → Z on any qubit in block 0
11 → Z on any qubit in block 1
01 → Z on any qubit in block 2
```
---

## File Structure

```
shor_qec.py              # shared library — all QEC functions
Shor-Code.ipynb          # Phase 1–3: circuit walkthrough, syndrome tests, correction demo
Noise-Experiments.ipynb  # Phase 4: noise sweeps, IBM hardware comparison, plots
Utilities.py             # wavefunc, QFT helpers
shor-code-strategy.md    # this file
```

`shor_qec.py` exports: `encode`, `syndrome_x_measurement`, `syndrome_z_measurement`,
`inject_error`, `correct_error`, `print_syndrome`, `run`.

Both notebooks do `from shor_qec import *`. This avoids copy-pasting functions and keeps
each notebook focused on its narrative.

---

## Phase 4 — Noise Model Experiments (Next)

### What noise models add
Current tests prove correctness against known single-qubit errors. Noise models prove
**usefulness** — errors are stochastic and applied after every gate across the full circuit
(all 9 data + 8 ancilla qubits). Shor code only corrects single-qubit errors, so:
- Low p: single errors dominate → Shor corrects → logical error rate << physical rate
- High p: multi-qubit errors likely → Shor fails → fidelity drops
- Threshold: the p where QEC curve crosses the no-QEC baseline — below it the code helps

### How to extend — minimal code change
`run()` already has the full pipeline. Just add `noise_model=None` parameter:
```python
def run(alpha, beta, error_block=None, error_position=None, error_type=None, noise_model=None):
    sim = AerSimulator(noise_model=noise_model)  # None = ideal, otherwise noisy
```
No inject_error needed for noise experiments — the noise model fires stochastically on
every gate. Pass `error_block=None, error_position=None, error_type=None` to skip injection.

### Noise models

**1. Depolarizing channel (primary)**
Applied after every gate. Each qubit independently gets X, Y, or Z with probability p/3.
```python
noise_model.add_all_qubit_quantum_error(depolarizing_error(p, 1), ['h', 'x', 'z'])
noise_model.add_all_qubit_quantum_error(depolarizing_error(p, 2), ['cx'])
```
Sweep: `p ∈ [0.001, 0.005, 0.01, 0.05, 0.1]`

**2. Bit-flip channel** — only X errors, isolates inner repetition code
**3. Phase-flip channel** — only Z errors, isolates outer repetition code

### New function: `noise_sweep(p_values, make_noise_model, n_trials=50)`
Loop over p values, call `run()` n_trials times per p with random |ψ⟩, average fidelity:
```python
logical_error_rate = mean(1 - fidelity) over n_trials
```
Baseline: same sweep but pass circuit through `AerSimulator(noise_model=...)` with no
QEC (just a single qubit with noise applied).

### Outputs
1. Log-log plot: logical error rate vs physical error rate — QEC curves + baseline
2. Threshold: where QEC curve crosses baseline
3. Mean ± std error bars per point

---

## Phase 5 — IBM Hardware Comparison (TODO)

Run the same circuit on a real IBM backend and compare against the AerSimulator results.

### What this shows
IBM publishes per-gate error rates for each backend (e.g. 0.1% single-qubit, 1% CX).
We can:
1. Run the Shor circuit on a real device (via `ibm_least_busy`)
2. Measure fidelity of corrected output vs ideal
3. Compare to what IBM's noise model predicts for that device

This gives a **three-way comparison**:
- Ideal (AerSimulator, no noise)
- Noisy simulation (depolarizing at IBM's published gate error rate)
- Real hardware

If noisy simulation ≈ hardware, the model is validated. Difference between hardware and
no-QEC baseline shows how much Shor actually helped on real qubits.

### Requirements
```python
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
service = QiskitRuntimeService()
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=17)
```
Need 17 qubits (9 data + 8 ancilla). Most IBM Eagle/Heron devices qualify.

---

## Implementation Order

| # | Task | Status |
|---|------|--------|
| 1 | `encode()` | Done |
| 2 | `syndrome_x_measurement()` | Done |
| 3 | `syndrome_z_measurement()` | Done |
| 4 | Syndrome tests (no/X/Z error) | Done |
| 5 | `inject_error(qc, block, position, error_type)` | Done |
| 6 | `correct_error(qc, syndrome_string)` | Done |
| 7 | `run()` — full pipeline, clean circuit statevector | Done |
| 8 | `test_error_correction()` + syndrome table display | Done |
| 9 | Fidelity = 1.0 verified for X, Y, Z errors | Done |
| 10 | Extract functions → `shor_qec.py`, split into two notebooks | Next |
| 11 | Depolarizing noise sweep (`Noise-Experiments.ipynb`) | TODO |
| 12 | Bit-flip + phase-flip sweeps | TODO |
| 13 | Plots and report figures | TODO |
| 14 | IBM hardware run + three-way comparison | TODO |

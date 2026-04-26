import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector, partial_trace, state_fidelity
from IPython.display import display
import Utilities as utils
from qiskit_aer.noise import (
    NoiseModel,
    depolarizing_error,
    thermal_relaxation_error,
    amplitude_damping_error,
)


def create_arbirtary_state():
     # this is of the form |ψ⟩ = cos(θ/2)|0⟩ + e^(iφ)sin(θ/2)|1⟩
    #print(f"|α|² + |β|² = {abs(alpha)**2 + abs(beta)**2:.6f}")  # should be 1.0
    theta = np.random.uniform(0, np.pi)
    phi = np.random.uniform(0, 2 * np.pi)
    alpha = np.cos(theta / 2)
    beta = np.exp(1j * phi) * np.sin(theta / 2)
    return alpha, beta


'''
encode (forward):
qc.initialize([alpha, beta], 0)
qc.cx(0, 3); qc.cx(0, 6)        # step 1: spread q0 → q3, q6
qc.h([0, 3, 6])                  # step 2: Hadamards on lead qubits
qc.cx(0, 1); qc.cx(0, 2)         # step 3: spread within block 0
qc.cx(3, 4); qc.cx(3, 5)         # step 3: block 1
qc.cx(6, 7); qc.cx(6, 8)         # step 3: block 2

decode (reverse — undoes step 3, then step 2, then step 1):
qc.cx(0, 1); qc.cx(0, 2)         # undo step 3, block 0
qc.cx(3, 4); qc.cx(3, 5)         # undo step 3, block 1
qc.cx(6, 7); qc.cx(6, 8)         # undo step 3, block 2
qc.h([0, 3, 6])                  # undo step 2 (H is its own inverse)
qc.cx(0, 3); qc.cx(0, 6)         # undo step 1
'''

def encode(alpha, beta):
    qc = QuantumCircuit(9)
    qc.initialize([alpha, beta], 0)
    qc.cx(0, 3)
    qc.cx(0, 6)
    qc.h([0, 3, 6])
    qc.barrier()
    qc.cx(0, 1); qc.cx(0, 2)
    qc.cx(3, 4); qc.cx(3, 5)
    qc.cx(6, 7); qc.cx(6, 8)
    return qc

def decode(qc):
    qc.cx(0, 1); qc.cx(0, 2)
    qc.cx(3, 4); qc.cx(3, 5)
    qc.cx(6, 7); qc.cx(6, 8)
    qc.h([0, 3, 6])
    qc.cx(0, 3); qc.cx(0, 6)
    return qc

##############################################################################

def syndrome_x_measurement(qc):
    a = QuantumRegister(6, 'a')
    c = ClassicalRegister(6, 'c')
    qc.add_register(a)
    qc.add_register(c)
    qc.barrier()
    qc.cx(0, a[0]); qc.cx(1, a[0])
    qc.cx(1, a[1]); qc.cx(2, a[1])
    qc.barrier()
    qc.cx(3, a[2]); qc.cx(4, a[2])
    qc.cx(4, a[3]); qc.cx(5, a[3])
    qc.barrier()
    qc.cx(6, a[4]); qc.cx(7, a[4])
    qc.cx(7, a[5]); qc.cx(8, a[5])
    qc.barrier()
    qc.measure(a, c)
    return qc


def syndrome_x_measurement_hw(qc):
    """
    Hardware-friendly X-syndrome measurement.
    Same parity checks as syndrome_x_measurement, but writes each block's
    2 syndrome bits into its own 2-bit ClassicalRegister (cx0, cx1, cx2).
    This lets correct_error_dynamic use flat register-equality if_test
    (no nesting, no switch) — required by ibm_fez's dynamic-circuit constraints.
    """
    a = QuantumRegister(6, 'a')
    cx0 = ClassicalRegister(2, 'cx0')
    cx1 = ClassicalRegister(2, 'cx1')
    cx2 = ClassicalRegister(2, 'cx2')
    qc.add_register(a)
    qc.add_register(cx0); qc.add_register(cx1); qc.add_register(cx2)
    qc.barrier()
    qc.cx(0, a[0]); qc.cx(1, a[0])
    qc.cx(1, a[1]); qc.cx(2, a[1])
    qc.barrier()
    qc.cx(3, a[2]); qc.cx(4, a[2])
    qc.cx(4, a[3]); qc.cx(5, a[3])
    qc.barrier()
    qc.cx(6, a[4]); qc.cx(7, a[4])
    qc.cx(7, a[5]); qc.cx(8, a[5])
    qc.barrier()
    qc.measure([a[0], a[1]], cx0)
    qc.measure([a[2], a[3]], cx1)
    qc.measure([a[4], a[5]], cx2)
    return qc


def syndrome_z_measurement(qc):
    a = QuantumRegister(2, 'za')
    c = ClassicalRegister(2, 'zc')
    qc.add_register(a)
    qc.add_register(c)
    qc.barrier()
    qc.h(a)
    qc.cx(a[0], 0); qc.cx(a[0], 1); qc.cx(a[0], 2)
    qc.cx(a[0], 3); qc.cx(a[0], 4); qc.cx(a[0], 5)
    qc.h(a[0])
    qc.barrier()
    qc.cx(a[1], 3); qc.cx(a[1], 4); qc.cx(a[1], 5)
    qc.cx(a[1], 6); qc.cx(a[1], 7); qc.cx(a[1], 8)
    qc.h(a[1])
    qc.barrier()
    qc.measure(a, c)
    return qc


def inject_error(qc, block_num, position, error_type):
    qubit_index = block_num * 3 + position
    if error_type == 'X':
        qc.x(qubit_index)
    elif error_type == 'Z':
        qc.z(qubit_index)
    elif error_type == 'Y':
        qc.y(qubit_index)
    else:
        raise ValueError("error_type must be 'X', 'Y', or 'Z'")
    return qc


def correct_error(qc, syndrome_string):
    z_syndromes, x_syndromes = syndrome_string.split(' ')
    x_syndromes = x_syndromes[::-1]
    z_syndromes = z_syndromes[::-1]

    for block in range(3):
        pair = x_syndromes[block*2: block*2+2]
        if pair == '11':
            qc.x(block*3 + 1)
        elif pair == '10':
            qc.x(block*3)
        elif pair == '01':
            qc.x(block*3 + 2)

    if z_syndromes == '10':
        qc.z(0)
    elif z_syndromes == '11':
        qc.z(3)
    elif z_syndromes == '01':
        qc.z(6)
    return qc


def print_syndrome(syndrome_string):
    z_raw, x_raw = syndrome_string.split(' ')
    x_bits = x_raw[::-1]
    z_bits = z_raw[::-1]

    x_table = {'10': 'left qubit', '11': 'middle qubit', '01': 'right qubit', '00': 'no error'}
    z_table = {'10': 'block 0', '11': 'block 1', '01': 'block 2', '00': 'no error'}

    print(f"┌─────────┬────────┬──────────────┐")
    print(f"│ Block 0 │  {x_bits[0:2]}    │ {x_table[x_bits[0:2]]:12} │")
    print(f"│ Block 1 │  {x_bits[2:4]}    │ {x_table[x_bits[2:4]]:12} │")
    print(f"│ Block 2 │  {x_bits[4:6]}    │ {x_table[x_bits[4:6]]:12} │")
    print(f"│ Z parity│  {z_bits}    │ {z_table[z_bits]:12} │")
    print(f"└─────────┴────────┴──────────────┘")

# This run is for simulator only
def run(alpha, beta, error_block=None, error_position=None, error_type=None,
        backend=None, show_circuit=True, shots=1024):
    encoded_qc = encode(alpha, beta)
    initial_sv = Statevector(encoded_qc)

    if error_type is not None:
        inject_error(encoded_qc, error_block, error_position, error_type)

    xsyndromeqc = syndrome_x_measurement(encoded_qc)
    zsyndromeqc = syndrome_z_measurement(xsyndromeqc)

    if show_circuit:
        display(zsyndromeqc.draw('mpl', style="Clifford"))

    sim = AerSimulator() if backend is None else backend
    counts = sim.run(zsyndromeqc, shots=1).result().get_counts()
    syndrome_string = list(counts.keys())[0]
    if show_circuit:
        print_syndrome(syndrome_string)

    correctedqc = correct_error(zsyndromeqc, syndrome_string)
    correctedqc.save_statevector()

    data = ClassicalRegister(9, 'data')
    correctedqc.add_register(data)
    correctedqc.measure(range(9), data)
    result = sim.run(correctedqc, shots=shots).result()
    full_sv = Statevector(result.get_statevector())
    data_state = partial_trace(full_sv, list(range(9, 17)))

    return initial_sv, data_state

# for real hardware we need to do the correction dynamically based on the syndrome measurement results, since we can't just run the whole circuit and measure at the end. This means we need to split the circuit into parts and run them sequentially, applying the correction after measuring the syndrome. We can use the qiskit runtime for this, which allows us to run circuits with mid-circuit measurements and conditional operations. Here's how we can implement that:
def correct_error_hw_dynamic(qc, c_x_list, zc):
    """
    Hardware-friendly correction. Uses flat register-equality if_test
    on per-block 2-bit registers (cx0, cx1, cx2) — no nesting, no switch.
    Required by ibm_fez's dynamic-circuit constraints.
    Bit ordering note (Qiskit, LSB first): for register c_x_block,
    integer value = c_x_block[1]*2 + c_x_block[0].
    """
    # X correction per block
    for block, cx in enumerate(c_x_list):
        q0, q1, q2 = block*3, block*3 + 1, block*3 + 2

        with qc.if_test((cx, 1)):    # 0b01 → c[0]=1, c[1]=0 → left  (q0) binary: 01
            qc.x(q0)
        with qc.if_test((cx, 3)):    # 0b11 → c[0]=1, c[1]=1 → middle (q1) binary: 10
            qc.x(q1)
        with qc.if_test((cx, 2)):    # 0b10 → c[0]=0, c[1]=1 → right (q2) b inary: 11
            qc.x(q2)

    # Z correction (single 2-bit zc register)
    with qc.if_test((zc, 1)):        # 0b01 → zc[0]=1, zc[1]=0 → block 0
        qc.z(0)
    with qc.if_test((zc, 3)):        # 0b11 → zc[0]=1, zc[1]=1 → block 1
        qc.z(3)
    with qc.if_test((zc, 2)):        # 0b10 → zc[0]=0, zc[1]=1 → block 2
        qc.z(6)

    return qc



def make_noise_model(noise_type, params, n_qubits):
    nm = NoiseModel()
    if noise_type == "depolarizing":
        error1q = depolarizing_error(params["input_prob"], 1)
        nm.add_all_qubit_quantum_error(error1q, "u3")
        if n_qubits > 1:
            error2q = depolarizing_error(params["input_prob"], 2)
            nm.add_all_qubit_quantum_error(error2q, "cx")
        # this line says everytime a cicruit has a single qubit 
        # gate (u3) or a two qubit gate (cx) apply the depolarizing error
        # u3 is the gate that every other single qubit gate compiles to
        # Λ(ρ) = r·ρ + (1−r)·I/d   params: {"input_prob": r}

    elif noise_type == "amplitude_damping":
        error1q = amplitude_damping_error(params["input_prob"])
        nm.add_all_qubit_quantum_error(error1q, ["u3"])
        if n_qubits > 1:
            error2q = error1q.expand(error1q)
            nm.add_all_qubit_quantum_error(error2q, ["cx"])
        # Λ: |1⟩ → |0⟩ with prob gamma   params: {"input_prob": gamma}
        #K₀ = [[1, 0], [0, √(1−γ)]] K₁ = [[0, √γ], [0, 0]]


    elif noise_type == "thermal_relaxation":
        '''
        Quick theory: Thermal relaxation — it models two physical decay processes on real hardware: 
        T1 — energy relaxation: excited qubit |1⟩ spontaneously decays to |0⟩ over time T1
        T2 — dephasing: qubit loses phase coherence (the X/Y components of the Bloch vector shrink) over time T2
        '''
        
        error1q = thermal_relaxation_error(params["T1"], params["T2"], params["tgate"])
        nm.add_all_qubit_quantum_error(error1q, ["u3"])
        if n_qubits > 1:
            error_cx = thermal_relaxation_error(params["T1"], params["T2"], params["tgate"] * 2)
            error2q = error_cx.expand(error_cx)
            nm.add_all_qubit_quantum_error(error2q, ["cx"])
        # Λ: T1 decay + T2 dephasing over gate time tgate, not this not the T gate. params: {"T1": ns, "T2": ns, "tgate": ns}  with T2 <= 2*T1
        #p1 = exp(−t/T1) — T1 decay factorp2 = exp(−t/T2) — T2 decay factor
        #K₀ = [[1, 0], [0, √p1]] K₁ = [[0, √(1−p1)], [0, 0]] K₂ = [[0, 0], [0, √(p2 − p1)]]  ← only exists when p2 > p1 K₀, K₁ — same as amplitude damping, capturing T1 decay K₂ — pure dephasing on top of T1, capturing the extra T2 decay

    return nm

'''
Here we apply a given noise model with diff params of p or T1, T2 to the whole syndrome measurement and correction process, and see how it affects the final fidelity. We can sweep over different noise strengths to see how the code performs under different noise levels.
'''

def noise_sweep(noise_type, p_values, n_qubits, n_trials=50, T1=100000, T2=80000,):
    results = []
    for p in p_values:
        if noise_type == "thermal_relaxation":
            params = {"T1": T1, "T2": T2, "tgate": p}
        else:
            params = {"input_prob": p}

        nm = make_noise_model(noise_type, params, n_qubits) 
        backend = AerSimulator(noise_model=nm)
        fidelities = []
        for _ in range(n_trials):
            alpha, beta = create_arbirtary_state()
            initial_state, final_state = run(alpha, beta, backend=backend, show_circuit=False, shots=1)
            fidelities.append(state_fidelity(initial_state, final_state))

        avg_fidelity = np.mean(fidelities)
        correction_error_rate = 1-avg_fidelity # logical error rate = 0.02  (2% of the time correction failed)
        fidelity_std = np.std(fidelities)
        results.append((p, avg_fidelity, correction_error_rate, fidelity_std))

    return results

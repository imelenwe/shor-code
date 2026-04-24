from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import Aer
# At the top of your utils file, add:
from qiskit.quantum_info import Statevector, DensityMatrix
import numpy as np
import math as m
from qiskit_aer import QasmSimulator


S_simulator = Aer.get_backend('statevector_simulator')
M_simulator = Aer.get_backend('qasm_simulator')

# now implement a generic QFT method for n qubits

def QFT(num_qubits):
    qreg = QuantumRegister(num_qubits)
    qc = QuantumCircuit(qreg)

    for i in range(num_qubits):
        qc.h(qreg[i])
        for j in range(i+1, num_qubits):
            qc.cp(2*m.pi/2**(j-i+1), qreg[j], qreg[i])
        qc.barrier()

    return qc


def QFT_dag(num_qubits):
    qreg = QuantumRegister(num_qubits)
    qc = QuantumCircuit(qreg)

    for i in range(num_qubits-1, -1, -1):
        for j in range(num_qubits-1, i, -1):
            qc.cp(-2*m.pi/2**(j-i+1), qreg[j], qreg[i])
        qc.h(qreg[i])
        qc.barrier()

    return qc

# implement a method to print the statevector in a nice format, with options for precision and bit order
# works for both qc or statevector objects
def wavefunc(obj, precision=5, top_to_bottom=False):
    if isinstance(obj, QuantumCircuit):
        sv = Statevector(obj).data
    elif isinstance(obj, DensityMatrix):
        vals, vecs = np.linalg.eigh(obj.data)
        sv = vecs[:, -1]   # 1D array, same shape as Statevector case
    elif isinstance(obj, Statevector):
        sv = obj.data
    else:
        sv = obj.data


    n = int(np.log2(len(sv)))
    terms = []

    for i, amp in enumerate(sv):
        amp = round(amp.real, precision) + round(amp.imag, precision) * 1j
        if amp == 0:
            continue

        bits = format(i, f'0{n}b')
        if not top_to_bottom:
            bits = bits[::-1]

        if amp.real != 0 and amp.imag != 0:
            amp_str = f"{amp.real}{amp.imag:+}j" #The :+ format spec forces an explicit sign, so positive gets + and negative gets -
        elif amp.imag != 0:
            amp_str = f"{amp.imag}j"
        else:
            amp_str = f"{amp.real}"
        #print(f"amp_str: {amp_str}")
        terms.append(f"{amp_str} |{bits}>")

    out = terms[0]
    for t in terms[1:]:
        out += (' ' if t.startswith('-') else ' + ') + t
    print(out)


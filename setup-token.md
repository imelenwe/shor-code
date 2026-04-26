# IBM Quantum Token Setup

Follow these steps before running `shor-code-qc.ipynb`. The other notebooks (`shor-code-sim.ipynb`) work without a token.

---

## Step 1 — Install dependencies

```bash
pip install qiskit==1.4.3 qiskit-aer==0.14.2 qiskit-ibm-runtime==0.40.0 python-dotenv==1.2.2 matplotlib numpy
```

---

## Step 2 — Get an IBM Quantum account

1. Go to [quantum.ibm.com](https://quantum.ibm.com) and sign up for a free account
2. After logging in, click your profile icon (top right) → **Account settings**
3. Under **API token**, copy your token — it looks like a long string starting with `eyJ...`

---

## Step 3 — Create your `.env` file

In the root of this repo, create a file named `.env` (it's already in `.gitignore` so it won't be committed):

```
IBM_TOKEN=paste_your_token_here
```

Do **not** add quotes around the token.

---

## Step 4 — Verify the setup

Run this in a Python shell or notebook cell:

```python
import os
from dotenv import load_dotenv
from qiskit_ibm_runtime import QiskitRuntimeService

load_dotenv()
service = QiskitRuntimeService(channel="ibm_quantum", token=os.getenv("IBM_TOKEN"))
print(service.backends())  # should print a list of IBM backends
```

If you see a list of backend names, you're ready to run `shor-code-qc.ipynb`.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `IBM_TOKEN is None` | Check `.env` exists in the repo root and has no quotes around the token |
| `AuthenticationError` | Token is wrong or expired — regenerate it from the IBM Quantum dashboard |
| `IBMNotAuthorizedError` | Free-tier accounts have limited backend access — make sure you're using `ibm_quantum` channel |
| `No backend found with >= 17 qubits` | IBM occasionally takes backends offline — re-run the backend selection cell to pick a new one |

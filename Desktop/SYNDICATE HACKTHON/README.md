# 🏛️ Autonomous CFO: Deep 3-Way Matching Engine

> **Track 2 Submission:** Autonomous Office of the CFO | Syndicate by Maximor Hackathon

An enterprise-grade AI financial controller that automates Accounts Payable (AP) workflows through strict **3-Way Matching** across Purchase Orders (POs), Goods Received Notes (GRNs), and Vendor Invoices. Built with TensorMux (`glm-4-7-flash`), Agent Orchestrator (AO), and a Human-in-the-Loop (HITL) exception dashboard.

---

## 🌟 Overview

Manual AP reconciliation costs enterprise finance teams $12–$15 per invoice, takes days to process, and frequently suffers from overpayments due to quantity shortages or unapproved price markups. 

**Autonomous CFO** replaces manual verification with a risk-aware AI agent that:
1. **Auto-approves** clean 3-way matches (achieving ~70% Straight-Through Processing) and posts balanced entries directly to the General Ledger (GL).
2. **Intercepts and categorizes** financial discrepancies into a structured **Accounting Exception Taxonomy**.
3. **Generates Audit Workpapers** and routes exceptions to a human controller for single-click approval or dispute.

---

## ✨ Key Features

* **Deep 3-Way Reconciliation:** Evaluates Purchase Orders (PO), Goods Received Notes (GRN), and Invoices simultaneously.
* **Accounting Exception Taxonomy:** Flags specific, real-world finance errors:
  * `QUANTITY_SHORTAGE`: Vendor billed for items not received in the warehouse.
  * `PRICE_VARIANCE`: Vendor unit price exceeds contracted PO terms.
  * `UNAPPROVED_FREIGHT`: Unexpected tax/shipping charges omitted from PO.
  * `BANK_DETAIL_MISMATCH`: Remittance detail changes flagged for potential fraud.
* **Human-in-the-Loop (HITL) Dashboard:** Streamlit UI allowing CFOs and controllers to override, adjust, or dispute flagged items in seconds.
* **Automated GL Posting:** Generates double-entry accounting journal entries (`Debit: COGS/Inventory`, `Credit: Accounts Payable`) for verified matches.
* **Audit Workpaper Generation:** Creates structured, human-readable audit notes detailing exact line-item discrepancies.

---

## 🛠️ Sponsor Stack & Tech Integrations

| Technology / Sponsor | Role in System |
| :--- | :--- |
| **TensorMux (`glm-4-7-flash`)** | Core reasoning engine for 3-way document auditing and exception classification. |
| **Agent Orchestrator (AO)** | Central state manager and execution router across ingestion, LLM evaluation, and decision pipelines. |
| **Streamlit** | Real-time Human-in-the-Loop exception dashboard and GL audit ledger. |
| **Neatlogs** | Prompt telemetry, decision logging, and execution tracing for complete auditability. |
| **Dodo Payments** | Automated payout webhook trigger upon invoice approval. |

---

## 📐 System Architecture

```text
+-----------------------------------------------------------------------------------+
|                                   DATA INPUTS                                     |
|             [ Purchase Order ]     [ Receiving Log (GRN) ]     [ Vendor Invoice ] |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            FRONTEND DASHBOARD (Streamlit)                         |
|                   - Batch File Upload & Processing Trigger                         |
|                   - Real-Time Exception Queue & Accounting Metrics                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        ORCHESTRATION LAYER (Agent Orchestrator)                   |
|                   - Workflow Chaining & State Machine Management                  |
|                   - Fallback Execution & Decision Routing Rules                   |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       REASONING ENGINE (TensorMux API)                            |
|                             Model: glm-4-7-flash                                  |
|                                                                                   |
|  * 3-Way Match Audit Logic                 * Exception Taxonomy Classifier        |
|    - Quantity Match (Invoiced vs GRN)        - QUANTITY_SHORTAGE                    |
|    - Unit Price Match (Invoiced vs PO)       - PRICE_VARIANCE                       |
|  * Confidence Score Calculation            * Audit Workpaper Generator            |
+-----------------------------------------+-----------------------------------------+
                                          |
                    +---------------------+---------------------+
                    |                                           |
         [ 3-Way Match Passed ]                       [ Exception Flagged ]
         (Confidence >= 0.85)                        (Shortage / Variance)
                    |                                           |
                    v                                           v
+---------------------------------------+   +---------------------------------------+
|        AUTO-APPROVAL PIPELINE         |   |       HUMAN-IN-THE-LOOP (HITL)        |
|  - Auto-Draft Balanced GL Entry       |   |  - Route to Streamlit Review Queue    |
|  - Trigger Dodo Payments Webhook      |   |  - Controller Manual Approve/Reject   |
+-------------------+-------------------+   +-------------------+-------------------+
                    |                                           |
                    +---------------------+---------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                             AUDIT & TRACING LAYER                                 |
|                       - Neatlogs Execution Trace & Prompt Telemetry               |
|                       - Immutable General Ledger (GL) Audit Trail                 |
+-----------------------------------------------------------------------------------+



## Getting Started (Run Locally)

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Clone the repository
git clone https://github.com/Dhruv2020-code/autonomous-cfo.git
cd autonomous-cfo

### 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

### 3. Install dependencies
pip install -r requirements.txt

### 4. Set up environment variables
Create a `.env` file in the project root and add:

TENSORMUX_API_KEY=your_api_key_here

(Get an API key from [wherever TensorMux/OpenAI key comes from])

### 5. Run the app
streamlit run app.py

The app will open at http://localhost:8501

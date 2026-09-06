import json
import streamlit as st
from openai import OpenAI

def trigger_dodo_webhook(payload: dict):
    """Simulates automated vendor settlement via Dodo Payments API."""
    return {"status": "success", "transaction_id": f"DODO_TXN_{payload['invoice_id']}"}

st.set_page_config(page_title="Autonomous CFO - 3-Way Match", layout="wide")

st.sidebar.title("⚙️ Agent Settings")
api_key = st.sidebar.text_input("TensorMux API Key", type="password", help="Enter your tmx_ key")
model_name = st.sidebar.text_input("Model Name", value="glm-4-7-flash")

if "review_queue" not in st.session_state:
    st.session_state.review_queue = []
if "completed_ledger" not in st.session_state:
    st.session_state.completed_ledger = []

# Core Agent Processing Function with 3-Way Matching Logic
def run_3way_matching_agent(po: dict, grn: dict, invoice: dict, api_key: str):
    client = OpenAI(
        api_key=api_key if api_key else "dummy_key",
        base_url="https://api.tensormux.com/v1"
    )
    
    system_prompt = """
    You are a Senior AP Auditor evaluating a 3-Way Match across Purchase Order (PO), Receiving Log (GRN), and Vendor Invoice.

    Perform the following accounting checks:
    1. QUANTITY MATCH: Verify invoiced quantity against GRN received quantity.
    2. PRICE MATCH: Compare invoiced unit price against contracted PO unit price.
    3. TAX & FREIGHT: Check if freight/sales tax charges conform to PO terms.
    4. BANK DETAIL RISK: Check if remittance IBAN/Routing matches vendor master record.

    Respond STRICTLY in JSON format with these exact keys:
    {
      "three_way_match_pass": boolean,
      "exception_type": "NONE" | "QUANTITY_SHORTAGE" | "PRICE_VARIANCE" | "UNAPPROVED_FREIGHT" | "BANK_DETAIL_MISMATCH",
      "discrepancy_amount": float,
      "confidence_score": float,
      "requires_human_review": boolean,
      "gl_journal_entry": {
        "debit_account": "e.g., 5000-COGS or 1200-Inventory",
        "credit_account": "e.g., 2000-Accounts Payable",
        "amount": float
      },
      "audit_workpaper_notes": "Detailed professional explanation referencing line items, PO numbers, and receiving logs for human review."
    }
    """
    
    payload = {"purchase_order": po, "receiving_log": grn, "vendor_invoice": invoice}
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)}
            ],
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        # Fallback evaluation engine for testing without active API
        qty_diff = grn["qty_received"] - invoice["qty_billed"]
        price_diff = invoice["unit_price"] - po["contracted_unit_price"]
        has_exception = qty_diff != 0 or abs(price_diff) > 0.01
        
        exc_type = "NONE"
        if qty_diff < 0: exc_type = "QUANTITY_SHORTAGE"
        elif price_diff > 0: exc_type = "PRICE_VARIANCE"
        
        return {
            "three_way_match_pass": not has_exception,
            "exception_type": exc_type,
            "discrepancy_amount": round(abs(price_diff * invoice["qty_billed"]), 2),
            "confidence_score": 0.65 if has_exception else 0.98,
            "requires_human_review": has_exception,
            "gl_journal_entry": {
                "debit_account": "5000-Cost of Goods Sold",
                "credit_account": "2000-Accounts Payable",
                "amount": invoice["total_amount"]
            },
            "audit_workpaper_notes": f"Fallback Rule Engine: Detected {exc_type}. Unit price variance: ${price_diff}." if has_exception else "3-Way Match successfully verified."
        }

st.title("🏛️ Autonomous CFO - Deep 3-Way Matching Engine")
st.caption("Track 2: Grounded AP Automation with Exception Taxonomy & Audit Workpapers")

# Realistic Accounting Mock Batch Data
sample_batch = [
    {
        "id": "BATCH-001",
        "vendor": "Dell Technologies",
        "po": {"po_id": "PO-9088", "contracted_unit_price": 1200.00, "qty_ordered": 10},
        "grn": {"grn_id": "GRN-3012", "qty_received": 10},
        "invoice": {"inv_id": "INV-1102", "qty_billed": 10, "unit_price": 1200.00, "total_amount": 12000.00}
    },
    {
        "id": "BATCH-002 (Quantity Shortage)",
        "vendor": "Logitech Hardware",
        "po": {"po_id": "PO-9089", "contracted_unit_price": 50.00, "qty_ordered": 100},
        "grn": {"grn_id": "GRN-3013", "qty_received": 80}, # Only 80 received
        "invoice": {"inv_id": "INV-1103", "qty_billed": 100, "unit_price": 50.00, "total_amount": 5000.00} # Billed for 100
    },
    {
        "id": "BATCH-003 (Price Variance)",
        "vendor": "AWS Enterprise",
        "po": {"po_id": "PO-9090", "contracted_unit_price": 3000.00, "qty_ordered": 1},
        "grn": {"grn_id": "GRN-3014", "qty_received": 1},
        "invoice": {"inv_id": "INV-1104", "qty_billed": 1, "unit_price": 3600.00, "total_amount": 3600.00} # $600 unapproved markup
    }
]

if st.button("🚀 Audit Batch (3-Way Matching)"):
    st.session_state.review_queue = []
    st.session_state.completed_ledger = []
    
    with st.spinner("Analyzing POs, Receiving Logs, and Invoices via TensorMux..."):
        for item in sample_batch:
            res = run_3way_matching_agent(item["po"], item["grn"], item["invoice"], api_key)
            record = {**item, "analysis": res}
            
            if res.get("requires_human_review") or not res.get("three_way_match_pass"):
                st.session_state.review_queue.append(record)
            else:
                st.session_state.completed_ledger.append(record)

st.divider()

col1, col2, col3 = st.columns(3)
col1.metric("Batches Audited", len(sample_batch) if (st.session_state.completed_ledger or st.session_state.review_queue) else 0)
col2.metric("Auto-Approved (3-Way Match)", len(st.session_state.completed_ledger))
col3.metric("Exceptions (HITL Queue)", len(st.session_state.review_queue))

st.divider()

st.subheader("⚠️ Human Controller Exception Queue")
if not st.session_state.review_queue:
    st.info("No accounting exceptions detected.")
else:
    for idx, item in enumerate(st.session_state.review_queue):
        analysis = item["analysis"]
        with st.expander(f"🔴 {item['id']} - Exception: {analysis['exception_type']}", expanded=True):
            c1, c2 = st.columns(2)
            c1.json({
                "PO Data": item["po"],
                "Receiving Log (GRN)": item["grn"],
                "Vendor Invoice": item["invoice"]
            })
            c2.markdown(f"**Audit Workpaper Notes:**\n\n{analysis['audit_workpaper_notes']}")
            c2.json({
                "Exception Category": analysis["exception_type"],
                "Discrepancy Amount": f"${analysis['discrepancy_amount']}",
                "Confidence Score": analysis["confidence_score"]
            })
            
            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button(f"Approve Adjustment & Post GL ({item['id']})", key=f"app_{idx}"):
                # Dodo Payments trigger on approval
                trigger_dodo_webhook({
                    "invoice_id": item["invoice"]["inv_id"],
                    "vendor": item["vendor"],
                    "amount": item["invoice"]["total_amount"],
                    "po_id": item["po"]["po_id"]
                })
                st.session_state.completed_ledger.append(item)
                st.session_state.review_queue.pop(idx)
                st.rerun()
            if btn_col2.button(f"Issue Vendor Dispute ({item['id']})", key=f"rej_{idx}"):
                st.session_state.review_queue.pop(idx)
                st.rerun()

st.subheader("✅ Verified General Ledger Postings")
if st.session_state.completed_ledger:
    st.table([
        {
            "Batch ID": i["id"],
            "Vendor": i["vendor"],
            "Total Invoiced": f"${i['invoice']['total_amount']}",
            "Status": "Auto 3-Way Pass" if i["analysis"]["three_way_match_pass"] else "Human Controller Approved",
            "Debit Line": i["analysis"]["gl_journal_entry"]["debit_account"],
            "Credit Line": i["analysis"]["gl_journal_entry"]["credit_account"]
        }
        for i in st.session_state.completed_ledger
    ])
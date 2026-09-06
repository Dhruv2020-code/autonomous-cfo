"""
Updated app.py - FIXED VERSION
Integrated with Agent Orchestrator and Neatlogs
Complete AP automation with full audit trail
"""

import json
import streamlit as st
from openai import OpenAI
from datetime import datetime
from orchestrator import AgentOrchestrator, InvoiceStatus
from neatlogs_integration import NeatLogger


# ============================================================================
# PAGE SETUP
# ============================================================================

st.set_page_config(page_title="Autonomous CFO - 3-Way Match", layout="wide")

st.sidebar.title("⚙️ Agent Settings")
api_key = st.sidebar.text_input("TensorMux API Key", type="password", help="Enter your tmx_ key")
model_name = st.sidebar.text_input("Model Name", value="glm-4-7-flash")

# Initialize session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = AgentOrchestrator(api_key, model_name)

if "neat_logger" not in st.session_state:
    st.session_state.neat_logger = NeatLogger()

orchestrator = st.session_state.orchestrator
neat_logger = st.session_state.neat_logger


# ============================================================================
# CORE 3-WAY MATCHING AGENT
# ============================================================================

def run_3way_matching_agent(po: dict, grn: dict, invoice: dict, api_key: str, model_name: str):
    """
    AI-powered 3-way matching using TensorMux
    
    Args:
        po: Purchase Order data
        grn: Goods Received Notes data
        invoice: Vendor Invoice data
        api_key: TensorMux API key (tmx_...)
        model_name: Model name (glm-4-7-flash)
    
    Returns:
        Analysis result with matching decision
    """
    
    # Create OpenAI client pointed to TensorMux
    client = OpenAI(
        api_key=api_key if api_key else "dummy_key",
        base_url="https://api.tensormux.com/v1"  # TensorMux endpoint
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
        # Call TensorMux API with your credentials
        response = client.chat.completions.create(
            model=model_name,  # This is glm-4-7-flash or another TensorMux model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)}
            ],
            temperature=0.1  # Low temperature for consistent decisions
        )
        
        # Parse AI response
        result = json.loads(response.choices[0].message.content)
        
        # Log to Neatlogs: Successful AI analysis
        neat_logger.log_event(
            event_type="ai_analysis_success",
            model_used=model_name,
            exception_detected=result.get("exception_type") != "NONE",
            confidence=result.get("confidence_score")
        )
        
        return result
        
    except Exception as e:
        # Log to Neatlogs: AI analysis failed, using fallback
        neat_logger.log_error(
            invoice_id="unknown",
            error_message=str(e),
            error_type="tensormux_api_failed"
        )
        
        print(f"⚠️  TensorMux API failed: {str(e)}")
        print("📋 Using fallback rule engine...")
        
        # Fallback evaluation engine for testing without active API
        qty_diff = grn["qty_received"] - invoice["qty_billed"]
        price_diff = invoice["unit_price"] - po["contracted_unit_price"]
        has_exception = qty_diff != 0 or abs(price_diff) > 0.01
        
        exc_type = "NONE"
        if qty_diff < 0: 
            exc_type = "QUANTITY_SHORTAGE"
        elif price_diff > 0: 
            exc_type = "PRICE_VARIANCE"
        
        result = {
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
        
        # Log to Neatlogs: Fallback used
        neat_logger.log_event(
            event_type="fallback_engine_used",
            reason="tensormux_unavailable",
            exception_type=exc_type,
            confidence=result["confidence_score"]
        )
        
        return result


# ============================================================================
# SAMPLE DATA
# ============================================================================

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
        "grn": {"grn_id": "GRN-3013", "qty_received": 80},
        "invoice": {"inv_id": "INV-1103", "qty_billed": 100, "unit_price": 50.00, "total_amount": 5000.00}
    },
    {
        "id": "BATCH-003 (Price Variance)",
        "vendor": "AWS Enterprise",
        "po": {"po_id": "PO-9090", "contracted_unit_price": 3000.00, "qty_ordered": 1},
        "grn": {"grn_id": "GRN-3014", "qty_received": 1},
        "invoice": {"inv_id": "INV-1104", "qty_billed": 1, "unit_price": 3600.00, "total_amount": 3600.00}
    }
]


# ============================================================================
# PAGE TITLE & HEADER
# ============================================================================

st.title("🏛️ Autonomous CFO - Deep 3-Way Matching Engine")
st.caption("Track 2: Grounded AP Automation with Exception Taxonomy & Audit Workpapers")

st.divider()


# ============================================================================
# AUDIT BATCH BUTTON
# ============================================================================

if st.button("🚀 Audit Batch (3-Way Matching with Orchestrator & Neatlogs)"):
    
    # CREATE BATCH IN ORCHESTRATOR
    batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    orchestrator.create_batch(batch_id, sample_batch)
    
    # LOG TO NEATLOGS: Batch started
    neat_logger.log_event(
        event_type="batch_audit_started",
        batch_id=batch_id,
        total_invoices=len(sample_batch),
        timestamp=datetime.now().isoformat()
    )
    
    with st.spinner("Analyzing POs, Receiving Logs, and Invoices via TensorMux..."):
        
        # PROCESS ENTIRE BATCH using Orchestrator
        summary = orchestrator.process_batch(
            lambda po, grn, inv, key: run_3way_matching_agent(po, grn, inv, key, model_name)
        )
        
        # LOG TO NEATLOGS: Batch processing complete
        neat_logger.log_event(
            event_type="batch_audit_completed",
            batch_id=batch_id,
            auto_approved=summary.get("auto_approved"),
            exceptions_flagged=summary.get("exceptions_flagged"),
            timestamp=datetime.now().isoformat()
        )
        
        st.success(f"✅ Batch {batch_id} processed!")
        st.json(summary)


st.divider()


# ============================================================================
# METRICS & STATISTICS
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

batch_summary = orchestrator.get_batch_summary()

col1.metric("Batches Processed", orchestrator.stats["total_processed"] // max(len(sample_batch), 1))
col2.metric("Auto-Approved ✅", orchestrator.stats["auto_approved"])
col3.metric("Exceptions Flagged ⚠️", orchestrator.stats["exceptions_flagged"])
col4.metric("GL Posted 📕", orchestrator.stats["gl_posted"])

st.divider()


# ============================================================================
# HUMAN-IN-THE-LOOP DASHBOARD (Exception Review Queue)
# ============================================================================

st.subheader("⚠️ Human Controller Exception Queue (HITL Dashboard)")

review_queue = orchestrator.get_review_queue()

if not review_queue:
    st.info("✅ No accounting exceptions detected. All invoices passed 3-way match!")
else:
    st.warning(f"🔴 {len(review_queue)} invoices require human review")
    
    for idx, item in enumerate(review_queue):
        invoice_id = item["invoice_id"]
        
        with st.expander(
            f"🔴 {invoice_id} - {item['vendor']} | Exception: {item['exception_type']} | Severity: {item['severity'].upper()}",
            expanded=True
        ):
            
            # LEFT COLUMN: Document comparison
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("**📋 Document Comparison:**")
                st.json({
                    "PO Data": item["po"],
                    "Receiving Log (GRN)": item["grn"],
                    "Vendor Invoice": item["invoice"]
                })
            
            # RIGHT COLUMN: Audit workpaper & decision
            with c2:
                st.markdown("**📝 Audit Workpaper Notes:**")
                st.text(item["audit_notes"])
                
                st.markdown("**Analysis Details:**")
                st.json({
                    "Exception Category": item["exception_type"],
                    "Discrepancy Amount": f"${item['discrepancy_amount']}",
                    "Confidence Score": f"{item['confidence_score']:.2%}",
                    "Severity": item['severity']
                })
            
            # APPROVAL BUTTONS
            st.markdown("---")
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            
            approver_name = st.text_input(f"Your name (for {invoice_id})", key=f"approver_{idx}")
            
            with btn_col1:
                if st.button(f"✅ Approve & Post GL", key=f"app_{idx}"):
                    if not approver_name:
                        st.error("Please enter your name")
                    else:
                        # ORCHESTRATOR: Approve invoice
                        orchestrator.approve_invoice(invoice_id, approver_name)
                        
                        # ORCHESTRATOR: Post GL entry
                        orchestrator.post_gl_entry(invoice_id)
                        
                        # ORCHESTRATOR: Trigger payment
                        vendor_bank = {"iban": "DE89370400440532013000", "swift": "COBADEFFXXX"}
                        orchestrator.trigger_payment(invoice_id, vendor_bank)
                        
                        # LOG TO NEATLOGS: Complete approval workflow
                        neat_logger.log_approval(
                            invoice_id=invoice_id,
                            approver=approver_name,
                            approval_type="approved",
                            comments="Approved via HITL dashboard"
                        )
                        neat_logger.log_gl_posting(
                            invoice_id=invoice_id,
                            debit_account=orchestrator.invoices[invoice_id].gl_entry.get("debit_account"),
                            credit_account=orchestrator.invoices[invoice_id].gl_entry.get("credit_account"),
                            amount=orchestrator.invoices[invoice_id].invoice.get("total_amount")
                        )
                        neat_logger.log_payment_trigger(
                            invoice_id=invoice_id,
                            amount=orchestrator.invoices[invoice_id].invoice.get("total_amount"),
                            vendor_name=item["vendor"]
                        )
                        
                        st.success(f"✅ Invoice approved and GL posted!")
                        st.rerun()
            
            with btn_col2:
                if st.button(f"❌ Reject & Dispute", key=f"rej_{idx}"):
                    if not approver_name:
                        st.error("Please enter your name")
                    else:
                        reason = st.text_input(f"Rejection reason", key=f"reason_{idx}")
                        
                        # ORCHESTRATOR: Reject invoice
                        orchestrator.reject_invoice(invoice_id, approver_name, reason)
                        
                        # LOG TO NEATLOGS: Rejection
                        neat_logger.log_approval(
                            invoice_id=invoice_id,
                            approver=approver_name,
                            approval_type="rejected",
                            comments=reason
                        )
                        
                        st.info(f"❌ Invoice rejected with reason: {reason}")
                        st.rerun()
            
            with btn_col3:
                if st.button(f"📧 Send to Vendor", key=f"vendor_{idx}"):
                    # LOG TO NEATLOGS: Vendor communication
                    neat_logger.log_event(
                        event_type="vendor_dispute_sent",
                        invoice_id=invoice_id,
                        vendor=item["vendor"],
                        exception_type=item["exception_type"],
                        discrepancy_amount=item["discrepancy_amount"]
                    )
                    st.info(f"📧 Dispute sent to {item['vendor']}")


st.divider()


# ============================================================================
# VERIFIED GENERAL LEDGER POSTINGS
# ============================================================================

st.subheader("✅ Verified General Ledger Postings")

approved_invoices = [
    invoice for invoice in orchestrator.invoices.values()
    if invoice.status in [InvoiceStatus.AUTO_APPROVED.value, InvoiceStatus.GL_POSTED.value, InvoiceStatus.PAYMENT_TRIGGERED.value]
]

if approved_invoices:
    gl_table_data = [
        {
            "Invoice ID": inv.invoice_id,
            "Vendor": inv.vendor_name,
            "Amount": f"${inv.invoice.get('total_amount', 0):,.2f}",
            "Status": inv.status.replace("_", " ").title(),
            "Debit Account": inv.gl_entry.get("debit_account") if inv.gl_entry else "N/A",
            "Credit Account": inv.gl_entry.get("credit_account") if inv.gl_entry else "N/A",
            "Approver": inv.approver_name or "System (Auto)"
        }
        for inv in approved_invoices
    ]
    st.table(gl_table_data)
else:
    st.info("No GL postings yet.")


st.divider()


# ============================================================================
# AUDIT TRAIL & COMPLIANCE
# ============================================================================

st.subheader("📊 Audit Trail & Compliance (Neatlogs)")

tab1, tab2, tab3 = st.tabs(["Audit Trail", "Compliance Report", "Export Logs"])

with tab1:
    st.markdown("**Complete event log of all operations:**")
    audit_logs = neat_logger.get_audit_trail()
    
    if audit_logs:
        for log in audit_logs:
            st.json(log)
    else:
        st.info("No logs yet. Run an audit batch first.")

with tab2:
    st.markdown("**Compliance & Statistics Report:**")
    compliance_report = neat_logger.generate_compliance_report()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Events", compliance_report["total_events"])
    col2.metric("Invoices Processed", len(compliance_report["invoices_processed"]))
    col3.metric("Errors", compliance_report["errors"])
    
    # FIXED: Use correct key names from neatlogs_integration.py
    st.json({
        "Auto-Approved": compliance_report["invoices_auto_approved"],  # ← FIXED!
        "Exceptions Flagged": compliance_report["exceptions_flagged"],
        "Human Approved": compliance_report["invoices_approved"],      # ← FIXED!
        "Human Rejected": compliance_report["invoices_rejected"],      # ← FIXED!
        "GL Postings": compliance_report["gl_postings"],
        "Payments Triggered": compliance_report["payments_triggered"],
        "Error Rate": f"{compliance_report['error_rate']}%",
        "Avg Confidence": f"{compliance_report['average_confidence_score']:.2%}",
        "Total Amount": f"${compliance_report['total_amount_processed']:,.2f}",
        "Event Breakdown": compliance_report["event_breakdown"]
    })

with tab3:
    export_format = st.radio("Export Format", ["JSON", "CSV"])
    
    if st.button("📥 Generate Export"):
        export_data = neat_logger.export_logs(format=export_format.lower())
        
        st.download_button(
            label=f"Download {export_format}",
            data=export_data,
            file_name=f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format.lower()}",
            mime=f"application/{export_format.lower()}"
        )


st.divider()

# Print to console for verification
print("\n" + "="*80)
orchestrator.print_statistics()
neat_logger.print_summary()
print("="*80)

"""
Agent Orchestrator (AO)
- Manages workflow and state machine
- Routes decisions (Auto-Approval vs Human Review)
- Handles fallback execution
- Tracks batch processing
"""

import time
from enum import Enum
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass
from neatlogs_integration import NeatLogger

class InvoiceStatus(Enum):
    """Invoice processing states"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    AUTO_APPROVED = "auto_approved"
    EXCEPTION_FLAGGED = "exception_flagged"
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"
    GL_POSTED = "gl_posted"
    PAYMENT_TRIGGERED = "payment_triggered"


class ExceptionSeverity(Enum):
    """Exception severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InvoiceRecord:
    """Invoice processing record"""
    batch_id: str
    invoice_id: str
    vendor_name: str
    po: Dict[str, Any]
    grn: Dict[str, Any]
    invoice: Dict[str, Any]
    status: str
    analysis_result: Dict[str, Any] = None
    exception_type: str = None
    severity: str = None
    confidence_score: float = 0.0
    discrepancy_amount: float = 0.0
    created_at: str = None
    analyzed_at: str = None
    approved_at: str = None
    gl_entry: Dict[str, Any] = None
    audit_notes: str = ""
    approver_name: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class AgentOrchestrator:
    """
    Central state manager and execution router for AP automation workflow
    """

    def __init__(self, api_key: str, model_name: str = "glm-4-7-flash"):
        """
        Initialize the orchestrator
        
        Args:
            api_key: tmx_9b7f59a75246ad90f0355ffcf941dbce
            model_name: glm-4-7-flash 
        """
        self.api_key = api_key
        self.model_name = model_name
        self.neat_logger = NeatLogger()
        
        # State tracking
        self.batches = {}  # batch_id -> batch info
        self.invoices = {}  # invoice_id -> InvoiceRecord
        self.current_batch_id = None
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "auto_approved": 0,
            "exceptions_flagged": 0,
            "human_approved": 0,
            "human_rejected": 0,
            "gl_posted": 0,
            "total_amount_processed": 0.0,
            "avg_confidence_score": 0.0,
        }

    def create_batch(self, batch_id: str, invoices_data: List[Dict]) -> str:
        """
        Create a new batch of invoices for processing
        
        Args:
            batch_id: Unique batch identifier
            invoices_data: List of invoice data with po, grn, invoice
            
        Returns:
            batch_id
        """
        self.current_batch_id = batch_id
        self.batches[batch_id] = {
            "batch_id": batch_id,
            "created_at": datetime.now().isoformat(),
            "total_invoices": len(invoices_data),
            "status": "created",
            "invoices": []
        }
        
        # Create invoice records
        for idx, item in enumerate(invoices_data):
            invoice_id = f"{batch_id}-INV-{idx+1}"
            record = InvoiceRecord(
                batch_id=batch_id,
                invoice_id=invoice_id,
                vendor_name=item.get("vendor", "Unknown"),
                po=item.get("po", {}),
                grn=item.get("grn", {}),
                invoice=item.get("invoice", {}),
                status=InvoiceStatus.PENDING.value
            )
            self.invoices[invoice_id] = record
            self.batches[batch_id]["invoices"].append(invoice_id)
        
        # Log batch creation
        self.neat_logger.log_event(
            event_type="batch_created",
            batch_id=batch_id,
            total_invoices=len(invoices_data),
            timestamp=datetime.now().isoformat()
        )
        
        print(f"✅ Batch {batch_id} created with {len(invoices_data)} invoices")
        return batch_id

    def analyze_invoice(self, invoice_id: str, analysis_func) -> Dict[str, Any]:
        """
        Analyze a single invoice using the 3-way matching agent
        
        Args:
            invoice_id: Invoice to analyze
            analysis_func: Function that performs 3-way matching
            
        Returns:
            Analysis result
        """
        record = self.invoices[invoice_id]
        record.status = InvoiceStatus.ANALYZING.value
        
        start_time = time.time()
        
        try:
            # Call the AI analysis function
            result = analysis_func(record.po, record.grn, record.invoice, self.api_key)
            execution_time = time.time() - start_time
            
            # Update record with analysis
            record.analysis_result = result
            record.confidence_score = result.get("confidence_score", 0.0)
            record.discrepancy_amount = result.get("discrepancy_amount", 0.0)
            record.exception_type = result.get("exception_type", "NONE")
            record.audit_notes = result.get("audit_workpaper_notes", "")
            record.analyzed_at = datetime.now().isoformat()
            record.gl_entry = result.get("gl_journal_entry", {})
            
            # Log analysis
            self.neat_logger.log_analysis(
                invoice_id=invoice_id,
                batch_id=record.batch_id,
                analysis_result=result,
                execution_time=execution_time
            )
            
            print(f"📊 Analysis complete for {invoice_id} (Confidence: {record.confidence_score:.2%})")
            return result
            
        except Exception as e:
            # Log error
            self.neat_logger.log_error(
                invoice_id=invoice_id,
                error_message=str(e),
                error_type="analysis_failed"
            )
            print(f"❌ Analysis failed for {invoice_id}: {str(e)}")
            raise

    def route_decision(self, invoice_id: str) -> str:
        """
        Route invoice to auto-approval or human review
        
        Args:
            invoice_id: Invoice to route
            
        Returns:
            Route decision (auto_approve | human_review)
        """
        record = self.invoices[invoice_id]
        result = record.analysis_result
        
        if result is None:
            return "human_review"
        
        # Decision logic
        confidence = record.confidence_score
        requires_review = result.get("requires_human_review", False)
        
        # Auto-approve if high confidence and no exceptions
        if confidence >= 0.85 and not requires_review:
            record.status = InvoiceStatus.AUTO_APPROVED.value
            self.stats["auto_approved"] += 1
            decision = "auto_approve"
            severity = ExceptionSeverity.LOW.value
            
        # Flag for human review
        else:
            record.status = InvoiceStatus.EXCEPTION_FLAGGED.value
            self.stats["exceptions_flagged"] += 1
            decision = "human_review"
            
            # Determine severity
            if record.discrepancy_amount > 5000:
                severity = ExceptionSeverity.CRITICAL.value
            elif record.discrepancy_amount > 2000:
                severity = ExceptionSeverity.HIGH.value
            elif record.discrepancy_amount > 500:
                severity = ExceptionSeverity.MEDIUM.value
            else:
                severity = ExceptionSeverity.LOW.value
            
            record.severity = severity
        
        # Log routing decision
        self.neat_logger.log_routing_decision(
            invoice_id=invoice_id,
            decision=decision,
            confidence=confidence,
            exception_type=record.exception_type,
            severity=record.severity or "low"
        )
        
        print(f"🔀 Invoice {invoice_id} routed to: {decision.upper()}")
        return decision

    def approve_invoice(self, invoice_id: str, approver_name: str, comments: str = "") -> bool:
        """
        Human approval of exception invoice
        
        Args:
            invoice_id: Invoice to approve
            approver_name: Name of approver
            comments: Approval comments
            
        Returns:
            Success status
        """
        record = self.invoices[invoice_id]
        record.status = InvoiceStatus.HUMAN_APPROVED.value
        record.approved_at = datetime.now().isoformat()
        record.approver_name = approver_name
        
        self.stats["human_approved"] += 1
        
        # Log approval
        self.neat_logger.log_approval(
            invoice_id=invoice_id,
            approver=approver_name,
            approval_type="approved",
            comments=comments
        )
        
        print(f"✅ Invoice {invoice_id} approved by {approver_name}")
        return True

    def reject_invoice(self, invoice_id: str, approver_name: str, reason: str) -> bool:
        """
        Reject exception invoice
        
        Args:
            invoice_id: Invoice to reject
            approver_name: Name of rejector
            reason: Rejection reason
            
        Returns:
            Success status
        """
        record = self.invoices[invoice_id]
        record.status = InvoiceStatus.HUMAN_REJECTED.value
        record.approved_at = datetime.now().isoformat()
        record.approver_name = approver_name
        
        self.stats["human_rejected"] += 1
        
        # Log rejection
        self.neat_logger.log_approval(
            invoice_id=invoice_id,
            approver=approver_name,
            approval_type="rejected",
            comments=reason
        )
        
        print(f"❌ Invoice {invoice_id} rejected by {approver_name}. Reason: {reason}")
        return True

    def post_gl_entry(self, invoice_id: str) -> bool:
        """
        Post GL journal entry for approved invoice
        
        Args:
            invoice_id: Invoice to post
            
        Returns:
            Success status
        """
        record = self.invoices[invoice_id]
        
        if not record.gl_entry:
            print(f"⚠️  No GL entry for {invoice_id}")
            return False
        
        gl_entry = record.gl_entry
        record.status = InvoiceStatus.GL_POSTED.value
        self.stats["gl_posted"] += 1
        
        # Log GL posting
        self.neat_logger.log_gl_posting(
            invoice_id=invoice_id,
            debit_account=gl_entry.get("debit_account"),
            credit_account=gl_entry.get("credit_account"),
            amount=gl_entry.get("amount", 0.0)
        )
        
        print(f"📕 GL Entry posted for {invoice_id}")
        return True

    def trigger_payment(self, invoice_id: str, vendor_bank_details: Dict) -> bool:
        """
        Trigger Dodo Payments webhook for payment processing
        
        Args:
            invoice_id: Invoice to pay
            vendor_bank_details: Vendor bank information
            
        Returns:
            Success status
        """
        record = self.invoices[invoice_id]
        
        # This would call Dodo Payments API
        # For now, just log the intent
        record.status = InvoiceStatus.PAYMENT_TRIGGERED.value
        
        dodo_payload = {
            "invoice_id": record.invoice["inv_id"],
            "vendor_name": record.vendor_name,
            "amount": record.invoice.get("total_amount", 0.0),
            "po_id": record.po.get("po_id"),
            "bank_details": vendor_bank_details,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log payment trigger
        self.neat_logger.log_payment_trigger(
            invoice_id=invoice_id,
            amount=dodo_payload["amount"],
            vendor_name=record.vendor_name
        )
        
        print(f"💳 Payment triggered for {invoice_id} - Amount: ${dodo_payload['amount']}")
        return True

    def process_batch(self, analysis_func) -> Dict[str, Any]:
        """
        Process entire batch of invoices
        
        Args:
            analysis_func: Function that performs 3-way matching
            
        Returns:
            Batch processing summary
        """
        if not self.current_batch_id:
            print("❌ No batch to process")
            return {}
        
        batch_id = self.current_batch_id
        batch = self.batches[batch_id]
        invoice_ids = batch["invoices"]
        
        print(f"\n🚀 Processing Batch {batch_id} ({len(invoice_ids)} invoices)...")
        
        auto_approved = []
        exceptions = []
        
        for invoice_id in invoice_ids:
            try:
                # Step 1: Analyze
                self.analyze_invoice(invoice_id, analysis_func)
                
                # Step 2: Route decision
                decision = self.route_decision(invoice_id)
                
                # Step 3: Sort by decision
                if decision == "auto_approve":
                    record = self.invoices[invoice_id]
                    self.post_gl_entry(invoice_id)  # Auto-post GL
                    auto_approved.append(invoice_id)
                else:
                    exceptions.append(invoice_id)
                    
            except Exception as e:
                print(f"❌ Error processing {invoice_id}: {str(e)}")
                exceptions.append(invoice_id)
        
        # Update statistics
        self.stats["total_processed"] += len(invoice_ids)
        
        summary = {
            "batch_id": batch_id,
            "total_invoices": len(invoice_ids),
            "auto_approved": len(auto_approved),
            "exceptions_flagged": len(exceptions),
            "auto_approved_ids": auto_approved,
            "exception_ids": exceptions,
            "processed_at": datetime.now().isoformat()
        }
        
        # Log batch completion
        self.neat_logger.log_batch_completion(summary)
        
        return summary

    def get_batch_summary(self, batch_id: str = None) -> Dict[str, Any]:
        """
        Get summary of batch processing
        
        Args:
            batch_id: Batch to summarize (uses current if None)
            
        Returns:
            Batch summary
        """
        batch_id = batch_id or self.current_batch_id
        if not batch_id or batch_id not in self.batches:
            return {}
        
        batch = self.batches[batch_id]
        invoice_ids = batch["invoices"]
        
        status_breakdown = {
            "pending": 0,
            "analyzing": 0,
            "auto_approved": 0,
            "exception_flagged": 0,
            "human_approved": 0,
            "human_rejected": 0,
            "gl_posted": 0,
            "payment_triggered": 0
        }
        
        total_amount = 0.0
        
        for invoice_id in invoice_ids:
            record = self.invoices[invoice_id]
            status_breakdown[record.status] += 1
            total_amount += record.invoice.get("total_amount", 0.0)
        
        return {
            "batch_id": batch_id,
            "created_at": batch["created_at"],
            "total_invoices": batch["total_invoices"],
            "status_breakdown": status_breakdown,
            "total_amount_processed": total_amount,
            "statistics": self.stats
        }

    def export_audit_trail(self, batch_id: str = None) -> List[Dict]:
        """
        Export audit trail for batch
        
        Args:
            batch_id: Batch to export
            
        Returns:
            List of audit records
        """
        batch_id = batch_id or self.current_batch_id
        if not batch_id or batch_id not in self.batches:
            return []
        
        batch = self.batches[batch_id]
        invoice_ids = batch["invoices"]
        
        audit_records = []
        for invoice_id in invoice_ids:
            record = self.invoices[invoice_id]
            audit_records.append({
                "invoice_id": invoice_id,
                "vendor": record.vendor_name,
                "status": record.status,
                "exception_type": record.exception_type,
                "confidence_score": record.confidence_score,
                "discrepancy_amount": record.discrepancy_amount,
                "created_at": record.created_at,
                "analyzed_at": record.analyzed_at,
                "approved_at": record.approved_at,
                "approver": record.approver_name,
                "audit_notes": record.audit_notes
            })
        
        return audit_records

    def get_review_queue(self, batch_id: str = None) -> List[Dict]:
        """
        Get invoices pending human review
        
        Args:
            batch_id: Filter by batch
            
        Returns:
            List of exception invoices
        """
        batch_id = batch_id or self.current_batch_id
        
        queue = []
        for invoice_id, record in self.invoices.items():
            if batch_id and record.batch_id != batch_id:
                continue
            
            if record.status == InvoiceStatus.EXCEPTION_FLAGGED.value:
                queue.append({
                    "invoice_id": invoice_id,
                    "vendor": record.vendor_name,
                    "exception_type": record.exception_type,
                    "severity": record.severity,
                    "confidence_score": record.confidence_score,
                    "discrepancy_amount": record.discrepancy_amount,
                    "audit_notes": record.audit_notes,
                    "po": record.po,
                    "grn": record.grn,
                    "invoice": record.invoice
                })
        
        return queue

    def print_statistics(self):
        """Print processing statistics"""
        print("\n" + "="*60)
        print("📊 PROCESSING STATISTICS")
        print("="*60)
        print(f"Total Invoices Processed:  {self.stats['total_processed']}")
        print(f"Auto-Approved:             {self.stats['auto_approved']}")
        print(f"Exceptions Flagged:        {self.stats['exceptions_flagged']}")
        print(f"Human Approved:            {self.stats['human_approved']}")
        print(f"Human Rejected:            {self.stats['human_rejected']}")
        print(f"GL Entries Posted:         {self.stats['gl_posted']}")
        print(f"Total Amount Processed:    ${self.stats['total_amount_processed']:,.2f}")
        print("="*60 + "\n")

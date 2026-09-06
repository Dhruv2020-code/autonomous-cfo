"""
Neatlogs Integration Module
- Complete audit logging and telemetry tracking
- Compliance and audit trail generation
- Decision logging for all AP operations
"""

import json
import csv
from datetime import datetime
from typing import Dict, Any, List
from io import StringIO


class NeatLogger:
    """
    Enterprise-grade logging system for complete auditability
    Tracks: decisions, analyses, approvals, GL postings, payments
    Generates audit trails and compliance reports
    """
    
    def __init__(self, log_file: str = "audit_logs.jsonl"):
        """
        Initialize Neatlogs
        
        Args:
            log_file: File path to write logs (JSONL format)
        """
        self.log_file = log_file
        self.logs = []  # In-memory storage
        self.log_index = {}  # Fast lookup by invoice_id
        
        print(f"🔍 Neatlogs initialized - Logs will be written to: {log_file}")
    
    def _write_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Write log entry to file and memory
        Internal method - automatically called by all log methods
        
        Args:
            log_entry: Log record to write
        """
        # Ensure timestamp exists
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = datetime.now().isoformat()
        
        # Add log ID for tracing
        log_entry["log_id"] = f"LOG-{len(self.logs)+1:06d}"
        
        # Store in memory
        self.logs.append(log_entry)
        
        # Index by invoice_id for fast lookup
        if "invoice_id" in log_entry:
            invoice_id = log_entry["invoice_id"]
            if invoice_id not in self.log_index:
                self.log_index[invoice_id] = []
            self.log_index[invoice_id].append(log_entry)
        
        # Write to file
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"⚠️  Failed to write log to file: {str(e)}")
    
    # ========================================================================
    # CORE LOGGING METHODS
    # ========================================================================
    
    def log_event(self, event_type: str, **kwargs) -> None:
        """
        Log a general event
        Use this for batch creation, batch completion, misc events
        
        Args:
            event_type: Type of event (e.g., "batch_created", "batch_completed")
            **kwargs: Additional event data
        
        Example:
            neat_logger.log_event(
                event_type="batch_created",
                batch_id="BATCH-20240906",
                total_invoices=5
            )
        """
        log_entry = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self._write_log(log_entry)
    
    def log_analysis(self, invoice_id: str, batch_id: str, 
                     analysis_result: Dict[str, Any], execution_time: float) -> None:
        """
        Log AI analysis results from TensorMux model
        Call this immediately after run_3way_matching_agent() completes
        
        Args:
            invoice_id: Unique invoice identifier (e.g., "BATCH-001-INV-1")
            batch_id: Batch identifier (e.g., "BATCH-20240906")
            analysis_result: Complete output from TensorMux AI (includes all keys)
            execution_time: Time taken for analysis in seconds
        
        Example:
            result = run_3way_matching_agent(po, grn, invoice, api_key)
            neat_logger.log_analysis(
                invoice_id="BATCH-001-INV-1",
                batch_id="BATCH-001",
                analysis_result=result,
                execution_time=2.34
            )
        """
        log_entry = {
            "event_type": "analysis_completed",
            "log_category": "analysis",
            "invoice_id": invoice_id,
            "batch_id": batch_id,
            
            # Analysis results
            "three_way_match_pass": analysis_result.get("three_way_match_pass"),
            "exception_type": analysis_result.get("exception_type"),
            "confidence_score": analysis_result.get("confidence_score"),
            "discrepancy_amount": analysis_result.get("discrepancy_amount"),
            "requires_human_review": analysis_result.get("requires_human_review"),
            
            # GL and audit information
            "gl_journal_entry": analysis_result.get("gl_journal_entry"),
            "audit_workpaper_notes": analysis_result.get("audit_workpaper_notes"),
            
            # Performance metrics
            "execution_time_seconds": execution_time,
            "timestamp": datetime.now().isoformat(),
            
            # Source tracking
            "source_system": "tensormux_api",
            "model_used": "glm-4-7-flash"
        }
        self._write_log(log_entry)
        print(f"📊 [NEATLOGS] Analysis logged for {invoice_id}")
    
    def log_routing_decision(self, invoice_id: str, decision: str, 
                            confidence: float, exception_type: str, 
                            severity: str) -> None:
        """
        Log the routing decision (auto-approve vs human review)
        Call this after orchestrator.route_decision()
        
        Args:
            invoice_id: Invoice identifier
            decision: "auto_approve" or "human_review"
            confidence: Confidence score (0.0 to 1.0)
            exception_type: Type of exception detected (e.g., "QUANTITY_SHORTAGE")
            severity: Severity level ("low", "medium", "high", "critical")
        
        Example:
            neat_logger.log_routing_decision(
                invoice_id="BATCH-001-INV-1",
                decision="auto_approve",
                confidence=0.95,
                exception_type="NONE",
                severity="low"
            )
        """
        log_entry = {
            "event_type": "routing_decision",
            "log_category": "decision",
            "invoice_id": invoice_id,
            
            # Decision details
            "decision": decision,
            "confidence_score": confidence,
            "exception_type": exception_type,
            "severity": severity,
            
            # Decision logic
            "decision_threshold": 0.85,  # Confidence threshold for auto-approval
            "meets_auto_approval_criteria": decision == "auto_approve",
            
            "timestamp": datetime.now().isoformat(),
            "decision_engine": "agent_orchestrator"
        }
        self._write_log(log_entry)
        print(f"🔀 [NEATLOGS] Routing decision logged: {invoice_id} -> {decision}")
    
    def log_approval(self, invoice_id: str, approver: str, 
                    approval_type: str, comments: str = "") -> None:
        """
        Log human approval or rejection decision
        Call this when user clicks approve/reject in HITL dashboard
        
        Args:
            invoice_id: Invoice identifier
            approver: Name of the person approving/rejecting
            approval_type: "approved" or "rejected"
            comments: Optional approval/rejection comments or reasons
        
        Example:
            neat_logger.log_approval(
                invoice_id="BATCH-001-INV-2",
                approver="John Smith",
                approval_type="approved",
                comments="Approved - contacted vendor for clarification"
            )
        """
        log_entry = {
            "event_type": "human_approval",
            "log_category": "approval",
            "invoice_id": invoice_id,
            
            # Approval details
            "approval_type": approval_type,
            "approver_name": approver,
            "approver_timestamp": datetime.now().isoformat(),
            "comments": comments,
            
            # Method tracking
            "approval_method": "streamlit_hitl_dashboard",
            "approval_source": "human_controller",
            
            "timestamp": datetime.now().isoformat()
        }
        self._write_log(log_entry)
        print(f"✅ [NEATLOGS] Approval logged: {invoice_id} - {approval_type} by {approver}")
    
    def log_gl_posting(self, invoice_id: str, debit_account: str, 
                      credit_account: str, amount: float) -> None:
        """
        Log GL journal entry posting
        Call this when GL entry is posted (auto or after human approval)
        
        Args:
            invoice_id: Invoice identifier
            debit_account: Debit account code (e.g., "5000-COGS")
            credit_account: Credit account code (e.g., "2000-AP")
            amount: Amount posted (should match invoice total)
        
        Example:
            neat_logger.log_gl_posting(
                invoice_id="BATCH-001-INV-1",
                debit_account="5000-Cost of Goods Sold",
                credit_account="2000-Accounts Payable",
                amount=12000.00
            )
        """
        log_entry = {
            "event_type": "gl_posting",
            "log_category": "accounting",
            "invoice_id": invoice_id,
            
            # GL details (double-entry bookkeeping)
            "debit_account": debit_account,
            "credit_account": credit_account,
            "amount": amount,
            
            # Posting details
            "posting_timestamp": datetime.now().isoformat(),
            "system": "general_ledger",
            "status": "posted",
            "posting_method": "automated_system",
            
            "timestamp": datetime.now().isoformat()
        }
        self._write_log(log_entry)
        print(f"📕 [NEATLOGS] GL posting logged: {invoice_id} - ${amount:,.2f}")
    
    def log_payment_trigger(self, invoice_id: str, amount: float, 
                           vendor_name: str, vendor_bank: Dict = None) -> None:
        """
        Log payment trigger to Dodo Payments webhook
        Call this when payment is initiated
        
        Args:
            invoice_id: Invoice identifier
            amount: Payment amount
            vendor_name: Name of vendor being paid
            vendor_bank: Optional vendor bank details (IBAN, SWIFT, etc.)
        
        Example:
            neat_logger.log_payment_trigger(
                invoice_id="BATCH-001-INV-1",
                amount=12000.00,
                vendor_name="Dell Technologies",
                vendor_bank={"iban": "DE89370400440532013000", "swift": "COBADEFFXXX"}
            )
        """
        log_entry = {
            "event_type": "payment_triggered",
            "log_category": "payment",
            "invoice_id": invoice_id,
            
            # Payment details
            "amount": amount,
            "vendor_name": vendor_name,
            "vendor_bank_details": vendor_bank or {},
            
            # Payment system
            "payment_system": "dodo_payments",
            "webhook_triggered": True,
            "payment_timestamp": datetime.now().isoformat(),
            "payment_status": "initiated",
            
            "timestamp": datetime.now().isoformat()
        }
        self._write_log(log_entry)
        print(f"💳 [NEATLOGS] Payment trigger logged: {invoice_id} - ${amount:,.2f} to {vendor_name}")
    
    def log_batch_completion(self, summary: Dict[str, Any]) -> None:
        """
        Log batch processing completion
        Call this after orchestrator.process_batch() finishes
        
        Args:
            summary: Batch summary dictionary from orchestrator
        
        Example:
            summary = orchestrator.process_batch(analysis_func)
            neat_logger.log_batch_completion(summary)
        """
        log_entry = {
            "event_type": "batch_completion",
            "log_category": "batch",
            
            # Batch details
            "batch_id": summary.get("batch_id"),
            "total_invoices": summary.get("total_invoices"),
            "auto_approved": summary.get("auto_approved"),
            "exceptions_flagged": summary.get("exceptions_flagged"),
            
            # Invoice lists
            "auto_approved_ids": summary.get("auto_approved_ids", []),
            "exception_ids": summary.get("exception_ids", []),
            
            "timestamp": datetime.now().isoformat(),
            "completion_status": "completed"
        }
        self._write_log(log_entry)
        print(f"✅ [NEATLOGS] Batch completion logged: {summary.get('batch_id')}")
    
    def log_error(self, invoice_id: str, error_message: str, 
                 error_type: str, traceback: str = "") -> None:
        """
        Log errors and exceptions
        Call this in exception handlers
        
        Args:
            invoice_id: Invoice identifier (or "unknown" if not available)
            error_message: Error message/description
            error_type: Type of error (e.g., "tensormux_api_failed", "analysis_failed")
            traceback: Optional full traceback
        
        Example:
            try:
                result = run_3way_matching_agent(po, grn, invoice, api_key)
            except Exception as e:
                neat_logger.log_error(
                    invoice_id="BATCH-001-INV-1",
                    error_message=str(e),
                    error_type="tensormux_api_failed"
                )
        """
        log_entry = {
            "event_type": "error",
            "log_category": "error",
            "invoice_id": invoice_id,
            
            # Error details
            "error_type": error_type,
            "error_message": error_message,
            "error_traceback": traceback,
            
            # Error severity
            "severity": "high",
            "requires_attention": True,
            
            "timestamp": datetime.now().isoformat()
        }
        self._write_log(log_entry)
        print(f"❌ [NEATLOGS] Error logged: {invoice_id} - {error_type}: {error_message}")
    
    # ========================================================================
    # AUDIT TRAIL & REPORTING
    # ========================================================================
    
    def get_audit_trail(self, invoice_id: str = None, 
                       event_type: str = None, 
                       days: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail with optional filters
        
        Args:
            invoice_id: Filter by specific invoice
            event_type: Filter by event type (e.g., "analysis_completed")
            days: Filter by last N days
            
        Returns:
            List of log entries matching filters
        
        Example:
            # Get all logs for one invoice
            logs = neat_logger.get_audit_trail(invoice_id="BATCH-001-INV-1")
            
            # Get all approvals in last 7 days
            approvals = neat_logger.get_audit_trail(
                event_type="human_approval",
                days=7
            )
        """
        results = self.logs.copy()
        
        # Filter by invoice ID
        if invoice_id:
            results = [log for log in results 
                      if log.get("invoice_id") == invoice_id]
        
        # Filter by event type
        if event_type:
            results = [log for log in results 
                      if log.get("event_type") == event_type]
        
        # Filter by days
        if days:
            cutoff_timestamp = datetime.now().timestamp() - (days * 86400)
            results = [log for log in results 
                      if datetime.fromisoformat(log.get("timestamp", "")).timestamp() > cutoff_timestamp]
        
        return results
    
    def get_invoice_history(self, invoice_id: str) -> List[Dict[str, Any]]:
        """
        Get complete history for a single invoice
        Shows all events from creation through payment
        
        Args:
            invoice_id: Invoice identifier
            
        Returns:
            Chronological list of all events for this invoice
        
        Example:
            history = neat_logger.get_invoice_history("BATCH-001-INV-1")
            for event in history:
                print(f"{event['timestamp']}: {event['event_type']}")
        """
        return self.log_index.get(invoice_id, [])
    
    def generate_compliance_report(self, batch_id: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive compliance and audit report
        
        Args:
            batch_id: Optional filter by batch
            
        Returns:
            Compliance report with statistics and breakdown
        
        Example:
            report = neat_logger.generate_compliance_report(batch_id="BATCH-001")
            print(f"Total invoices: {report['total_invoices']}")
            print(f"Error rate: {report['error_rate']}%")
        """
        logs = self.logs
        
        # Filter by batch if specified
        if batch_id:
            logs = [log for log in logs if log.get("batch_id") == batch_id]
        
        # Initialize counters
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_events": len(logs),
            "event_breakdown": {},
            "invoices_processed": set(),
            "invoices_approved": 0,
            "invoices_rejected": 0,
            "invoices_auto_approved": 0,
            "exceptions_flagged": 0,
            "gl_postings": 0,
            "payments_triggered": 0,
            "errors": 0,
            "error_rate": 0.0,
            "total_amount_processed": 0.0,
            "average_confidence_score": 0.0,
            "event_types": [],
            "approval_methods": set(),
            "error_types": set()
        }
        
        # Process logs
        confidence_scores = []
        
        for log in logs:
            event_type = log.get("event_type", "unknown")
            
            # Count events by type
            if event_type not in report["event_breakdown"]:
                report["event_breakdown"][event_type] = 0
            report["event_breakdown"][event_type] += 1
            
            # Track invoice IDs
            if "invoice_id" in log and log["invoice_id"] != "unknown":
                report["invoices_processed"].add(log["invoice_id"])
            
            # Count by event type
            if event_type == "analysis_completed":
                if log.get("three_way_match_pass"):
                    report["invoices_auto_approved"] += 1
                else:
                    report["exceptions_flagged"] += 1
                
                # Collect confidence scores
                if log.get("confidence_score"):
                    confidence_scores.append(log["confidence_score"])
                
                # Sum amounts
                if log.get("discrepancy_amount"):
                    report["total_amount_processed"] += log.get("discrepancy_amount", 0)
            
            elif event_type == "human_approval":
                if log.get("approval_type") == "approved":
                    report["invoices_approved"] += 1
                else:
                    report["invoices_rejected"] += 1
                
                report["approval_methods"].add(log.get("approval_method", "unknown"))
            
            elif event_type == "gl_posting":
                report["gl_postings"] += 1
                report["total_amount_processed"] += log.get("amount", 0)
            
            elif event_type == "payment_triggered":
                report["payments_triggered"] += 1
            
            elif event_type == "error":
                report["errors"] += 1
                report["error_types"].add(log.get("error_type", "unknown"))
        
        # Calculate averages
        if confidence_scores:
            report["average_confidence_score"] = sum(confidence_scores) / len(confidence_scores)
        
        if report["invoices_processed"]:
            total_invoices = len(report["invoices_processed"])
            report["error_rate"] = round((report["errors"] / total_invoices) * 100, 2)
        
        # Convert sets to lists
        report["invoices_processed"] = sorted(list(report["invoices_processed"]))
        report["approval_methods"] = sorted(list(report["approval_methods"]))
        report["error_types"] = sorted(list(report["error_types"]))
        report["event_types"] = sorted(list(report["event_breakdown"].keys()))
        
        return report
    
    def export_logs(self, format: str = "json", batch_id: str = None) -> str:
        """
        Export logs in specified format
        
        Args:
            format: "json" or "csv"
            batch_id: Optional filter by batch
            
        Returns:
            Formatted export string
        
        Example:
            # Export to JSON
            json_data = neat_logger.export_logs(format="json")
            
            # Export to CSV
            csv_data = neat_logger.export_logs(format="csv", batch_id="BATCH-001")
        """
        logs = self.logs
        
        if batch_id:
            logs = [log for log in logs if log.get("batch_id") == batch_id]
        
        if format.lower() == "json":
            return json.dumps(logs, indent=2, default=str)
        
        elif format.lower() == "csv":
            if not logs:
                return "No logs to export"
            
            # Get all unique keys
            all_keys = set()
            for log in logs:
                all_keys.update(log.keys())
            
            keys = sorted(list(all_keys))
            
            # Create CSV
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=keys)
            writer.writeheader()
            
            for log in logs:
                # Convert complex objects to JSON strings
                row = {}
                for key in keys:
                    value = log.get(key, "")
                    if isinstance(value, (dict, list)):
                        row[key] = json.dumps(value)
                    else:
                        row[key] = str(value)
                writer.writerow(row)
            
            return output.getvalue()
        
        return "Unsupported format"
    
    def print_summary(self) -> None:
        """
        Print audit summary to console
        Useful for debugging and verification
        
        Example:
            neat_logger.print_summary()
        """
        report = self.generate_compliance_report()
        
        print("\n" + "="*70)
        print("📊 NEATLOGS AUDIT SUMMARY")
        print("="*70)
        print(f"Generated At:           {report['generated_at']}")
        print(f"Total Events Logged:    {report['total_events']}")
        print(f"Invoices Processed:     {len(report['invoices_processed'])}")
        print(f"Auto-Approved:          {report['invoices_auto_approved']}")
        print(f"Exceptions Flagged:     {report['exceptions_flagged']}")
        print(f"Human Approved:         {report['invoices_approved']}")
        print(f"Human Rejected:         {report['invoices_rejected']}")
        print(f"GL Postings:            {report['gl_postings']}")
        print(f"Payments Triggered:     {report['payments_triggered']}")
        print(f"Errors:                 {report['errors']}")
        print(f"Error Rate:             {report['error_rate']}%")
        print(f"Avg Confidence Score:   {report['average_confidence_score']:.2%}")
        print(f"Total Amount Processed: ${report['total_amount_processed']:,.2f}")
        
        if report["event_breakdown"]:
            print("\n📋 Event Breakdown:")
            for event_type, count in sorted(report["event_breakdown"].items()):
                print(f"  - {event_type:25} {count:5} events")
        
        if report["error_types"]:
            print("\n⚠️  Error Types:")
            for error_type in report["error_types"]:
                print(f"  - {error_type}")
        
        print("="*70 + "\n")

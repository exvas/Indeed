# Indeed Integration Monitoring Script

import frappe
from frappe.utils import now_datetime, add_days

def monitor_indeed_integration():
    """Daily monitoring script for Indeed integration"""
    
    # Check for failed job postings
    failed_jobs = frappe.get_all(
        "Indeed Job Integration",
        filters={"status": "Failed", "creation": (">=", add_days(now_datetime(), -1))},
        fields=["name", "job_opening", "error_message"]
    )
    
    if failed_jobs:
        # Send alert email to HR team
        frappe.sendmail(
            recipients=["hr@yourcompany.com"],
            subject="Indeed Integration: Failed Job Postings",
            message=f"Failed jobs in last 24hrs: {len(failed_jobs)}"
        )
    
    # Check XML feed health
    try:
        from indeed.indeed.utils import regenerate_xml_feed
        result = regenerate_xml_feed()
        print(f"XML feed health check: {result}")
    except Exception as e:
        frappe.log_error(f"XML feed health check failed: {str(e)}", "Indeed Integration")

# Schedule this to run daily
# Add to hooks.py: scheduler_events = {"daily": ["your_app.monitoring.monitor_indeed_integration"]}
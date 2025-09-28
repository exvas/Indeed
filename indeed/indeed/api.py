import frappe
from frappe import _
from indeed.indeed.utils import post_job_to_indeed, regenerate_xml_feed


@frappe.whitelist()
def manual_post_job_to_indeed(job_opening_name):
	"""Manually post a job opening to Indeed"""
	
	if not frappe.has_permission("Job Opening", "write"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		job_opening = frappe.get_doc("Job Opening", job_opening_name)
		
		# Check if already posted
		existing = frappe.db.exists("Indeed Job Integration", {"job_opening": job_opening_name})
		if existing:
			return {
				"success": False,
				"message": "Job already posted to Indeed",
				"integration_id": existing
			}
		
		# Post to Indeed
		success = post_job_to_indeed(job_opening)
		
		if success:
			integration = frappe.db.get_value(
				"Indeed Job Integration",
				{"job_opening": job_opening_name},
				["name", "status", "indeed_job_id"]
			)
			
			return {
				"success": True,
				"message": "Job posted to Indeed successfully",
				"integration_id": integration[0] if integration else None,
				"status": integration[1] if integration else None,
				"indeed_job_id": integration[2] if integration else None
			}
		else:
			return {
				"success": False,
				"message": "Failed to post job to Indeed. Check error logs for details."
			}
			
	except Exception as e:
		frappe.log_error(f"Manual job posting failed: {str(e)}", "Indeed Integration")
		return {
			"success": False,
			"message": f"Error: {str(e)}"
		}


@frappe.whitelist()
def get_indeed_integration_status(job_opening_name):
	"""Get the Indeed integration status for a job opening"""
	
	if not frappe.has_permission("Job Opening", "read"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		integration = frappe.db.get_value(
			"Indeed Job Integration",
			{"job_opening": job_opening_name},
			[
				"name", "status", "indeed_job_id", "posted_date", 
				"job_url", "error_message", "last_sync_date", "xml_feed_included"
			],
			as_dict=True
		)
		
		if integration:
			return {
				"success": True,
				"posted": True,
				"integration": integration
			}
		else:
			return {
				"success": True,
				"posted": False,
				"message": "Job not posted to Indeed"
			}
			
	except Exception as e:
		frappe.log_error(f"Status check failed: {str(e)}", "Indeed Integration")
		return {
			"success": False,
			"message": f"Error: {str(e)}"
		}


@frappe.whitelist()
def regenerate_indeed_xml_feed():
	"""Manually regenerate the Indeed XML feed"""
	
	if not frappe.has_permission("Indeed Integration Settings", "write"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		result = regenerate_xml_feed()
		return result
		
	except Exception as e:
		frappe.log_error(f"XML feed regeneration failed: {str(e)}", "Indeed Integration")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def test_indeed_webhook():
	"""Test the Indeed webhook endpoint with sample data"""
	
	if not frappe.has_permission("Indeed Integration Settings", "write"):
		frappe.throw(_("Insufficient permissions"))
	
	# Sample webhook data for testing
	test_data = {
		"application_id": "TEST_APP_123",
		"job_id": "TEST_JOB_456", 
		"external_id": frappe.db.get_value("Job Opening", {}, "name"),  # Get any job opening
		"candidate_name": "Test Candidate",
		"candidate_email": "test@example.com",
		"candidate_phone": "+1234567890",
		"job_title": "Test Position",
		"application_date": frappe.utils.now(),
		"screening_answers": [
			{
				"question": "Are you authorized to work in this country?",
				"answer": "Yes"
			},
			{
				"question": "What is your expected salary?", 
				"answer": "$50,000 - $60,000"
			}
		]
	}
	
	try:
		from indeed.indeed.utils import create_job_applicant_from_indeed
		result = create_job_applicant_from_indeed(test_data)
		
		return {
			"success": True,
			"message": "Webhook test completed",
			"result": result
		}
		
	except Exception as e:
		frappe.log_error(f"Webhook test failed: {str(e)}", "Indeed Integration")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_integration_stats():
	"""Get Indeed integration statistics"""
	
	if not frappe.has_permission("Indeed Integration Settings", "read"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		# Get job posting stats
		posted_jobs = frappe.db.count("Indeed Job Integration", {"status": ["in", ["Posted", "Active"]]})
		failed_jobs = frappe.db.count("Indeed Job Integration", {"status": "Error"})
		total_jobs = frappe.db.count("Indeed Job Integration")
		
		# Get applicant stats
		indeed_applicants = frappe.db.count("Job Applicant", {"source": "Indeed"})
		
		# Get recent activity
		recent_jobs = frappe.get_all(
			"Indeed Job Integration",
			fields=["job_opening", "status", "posted_date", "indeed_job_id"],
			order_by="creation desc",
			limit=5
		)
		
		recent_applicants = frappe.get_all(
			"Job Applicant", 
			filters={"source": "Indeed"},
			fields=["applicant_name", "job_title", "creation"],
			order_by="creation desc",
			limit=5
		)
		
		return {
			"success": True,
			"stats": {
				"posted_jobs": posted_jobs,
				"failed_jobs": failed_jobs,
				"total_jobs": total_jobs,
				"indeed_applicants": indeed_applicants,
				"recent_jobs": recent_jobs,
				"recent_applicants": recent_applicants
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Stats retrieval failed: {str(e)}", "Indeed Integration")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def sync_job_status_with_indeed(job_opening_name):
	"""Sync job status with Indeed (placeholder for API integration)"""
	
	if not frappe.has_permission("Job Opening", "write"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		integration = frappe.get_doc("Indeed Job Integration", {"job_opening": job_opening_name})
		
		if not integration.indeed_job_id:
			return {
				"success": False,
				"message": "No Indeed Job ID found for this posting"
			}
		
		# TODO: Implement actual status sync with Indeed API
		# For now, just update the last sync date
		integration.last_sync_date = frappe.utils.now()
		integration.save()
		
		return {
			"success": True,
			"message": "Status sync completed",
			"last_sync": integration.last_sync_date
		}
		
	except Exception as e:
		frappe.log_error(f"Status sync failed: {str(e)}", "Indeed Integration")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def test_xml_feed_quick():
	"""Quick test for XML feed functionality"""
	
	if not frappe.has_permission("Indeed Integration Settings", "read"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		import requests
		import xml.etree.ElementTree as ET
		from frappe.utils import get_url
		
		feed_url = f"{get_url()}/files/indeed_jobs.xml"
		
		# Test accessibility
		response = requests.get(feed_url, timeout=10)
		
		if response.status_code != 200:
			return {
				"success": False,
				"message": f"XML feed not accessible (HTTP {response.status_code})",
				"feed_url": feed_url
			}
		
		# Test XML parsing
		try:
			root = ET.fromstring(response.content)
			jobs_count = len(root.findall("job"))
			
			return {
				"success": True,
				"message": f"XML feed working! Found {jobs_count} jobs",
				"feed_url": feed_url,
				"jobs_count": jobs_count,
				"file_size": len(response.content)
			}
		except ET.ParseError as e:
			return {
				"success": False,
				"message": f"XML parsing error: {str(e)}",
				"feed_url": feed_url
			}
			
	except Exception as e:
		return {
			"success": False,
			"message": f"Test failed: {str(e)}"
		}


@frappe.whitelist()
def create_test_job():
	"""Create a test job opening for XML feed testing"""
	
	if not frappe.has_permission("Job Opening", "create"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		# Create test job
		job = frappe.new_doc("Job Opening")
		job.update({
			"job_title": f"Test Job - {frappe.utils.now()}",
			"company": frappe.defaults.get_global_default("company") or frappe.get_all("Company", limit=1)[0].name,
			"city": "Test City",
			"state": "Test State", 
			"country": "United States",
			"employment_type": "Full-time",
			"lower_range": 50000,
			"upper_range": 80000,
			"currency": "USD",
			"description": "This is a test job created for XML feed testing purposes.",
			"custom_post_to_indeed": 1
		})
		job.insert()
		frappe.db.commit()
		
		# Check if integration record was created
		integration = frappe.db.get_value(
			"Indeed Job Integration",
			{"job_opening": job.name},
			["name", "status"],
			as_dict=True
		)
		
		return {
			"success": True,
			"message": "Test job created successfully",
			"job_name": job.name,
			"job_title": job.job_title,
			"integration": integration
		}
		
	except Exception as e:
		return {
			"success": False,
			"message": f"Failed to create test job: {str(e)}"
		}


@frappe.whitelist()  
def validate_xml_feed_structure():
	"""Validate XML feed structure against Indeed requirements"""
	
	if not frappe.has_permission("Indeed Integration Settings", "read"):
		frappe.throw(_("Insufficient permissions"))
	
	try:
		import requests
		import xml.etree.ElementTree as ET
		from frappe.utils import get_url
		
		feed_url = f"{get_url()}/files/indeed_jobs.xml"
		response = requests.get(feed_url, timeout=10)
		
		if response.status_code != 200:
			return {
				"success": False,
				"message": "XML feed not accessible"
			}
		
		root = ET.fromstring(response.content)
		
		# Required elements check
		required_elements = {
			"Root element 'source'": root.tag == "source",
			"Publisher element": root.find("publisher") is not None,
			"Publisher URL": root.find("publisherurl") is not None,
			"Last build date": root.find("lastBuildDate") is not None
		}
		
		# Job elements validation
		jobs = root.findall("job")
		job_validation = {
			"Jobs exist": len(jobs) > 0
		}
		
		if jobs:
			first_job = jobs[0]
			required_job_fields = [
				"title", "date", "referencenumber", "url", 
				"company", "city", "description"
			]
			
			for field in required_job_fields:
				job_validation[f"Job has {field}"] = first_job.find(field) is not None
		
		all_checks = {**required_elements, **job_validation}
		
		return {
			"success": all(all_checks.values()),
			"message": f"Validation complete. {sum(all_checks.values())}/{len(all_checks)} checks passed",
			"checks": all_checks,
			"jobs_count": len(jobs),
			"feed_url": feed_url
		}
		
	except Exception as e:
		return {
			"success": False,
			"message": f"Validation failed: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook_job_application():
	"""Webhook endpoint to receive job applications from Indeed - API wrapper"""
	from indeed.indeed.utils import indeed_application_webhook
	return indeed_application_webhook()


@frappe.whitelist(allow_guest=True, methods=["POST"])
def test_webhook_job_application():
	"""Test webhook endpoint without signature validation"""
	try:
		# Get webhook data
		data = frappe.local.form_dict
		
		# Skip signature validation for testing
		
		# Find the job opening
		job_opening = None
		if data.get("job_reference"):
			job_opening = frappe.db.get_value("Job Opening", data.get("job_reference"))
		
		if not job_opening:
			return {
				"status": "error", 
				"message": f"Job opening {data.get('job_reference')} not found"
			}
		
		# Ensure "Indeed" source exists in Job Applicant Source
		if not frappe.db.exists("Job Applicant Source", "Indeed"):
			source = frappe.new_doc("Job Applicant Source")
			source.source_name = "Indeed"
			source.insert(ignore_permissions=True)
		
		# Create job applicant
		applicant = frappe.new_doc("Job Applicant")
		applicant.applicant_name = data.get("applicant_name", "Unknown Applicant")
		applicant.email_id = data.get("applicant_email")
		applicant.job_title = job_opening
		applicant.source = "Indeed"  # Link to Job Applicant Source
		applicant.application_date = data.get("application_date")
		applicant.insert(ignore_permissions=True)
		
		# Log the application
		frappe.log_error(f"Indeed application received: {applicant.name}", "Indeed Integration")
		
		return {
			"status": "success",
			"message": "Application received successfully",
			"applicant_id": applicant.name
		}
		
	except Exception as e:
		frappe.log_error(f"Test webhook error: {str(e)}", "Indeed Integration")
		return {
			"status": "error",
			"message": f"Processing failed: {str(e)}"
		}
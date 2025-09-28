import frappe
import requests
from frappe import _
from frappe.utils import now_datetime, get_url, cstr
import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import hashlib
import hmac


def get_integration_settings():
	"""Get Indeed integration settings"""
	settings = frappe.cache().get_value("indeed_integration_settings")
	if not settings:
		settings = frappe.get_single("Indeed Integration Settings")
		frappe.cache().set_value("indeed_integration_settings", settings, expires_in_sec=300)
	return settings


def on_job_opening_save(doc, method):
	"""Hook function triggered when Job Opening is saved"""
	
	# Skip if this is a data import or if integration is disabled
	if frappe.flags.in_import or frappe.flags.in_patch:
		return
	
	# Check if the custom field exists and is enabled
	if not doc.get("custom_post_to_indeed"):
		return
	
	# Post to Indeed
	frappe.enqueue(
		"indeed.indeed.utils.post_job_to_indeed",
		queue="default",
		timeout=300,
		job_opening=doc,
		is_async=True
	)


def post_job_to_indeed(job_opening):
	"""Post job opening to Indeed via configured method"""
	
	settings = get_integration_settings()
	
	if not settings.enable_auto_posting:
		frappe.log_error("Indeed auto-posting is disabled", "Indeed Integration")
		return False
	
	try:
		# Check if already posted
		existing = frappe.db.exists("Indeed Job Integration", {"job_opening": job_opening.name})
		if existing:
			frappe.log_error(f"Job {job_opening.name} already posted to Indeed", "Indeed Integration")
			return False
		
		# Create Indeed Job Integration record
		indeed_job = frappe.new_doc("Indeed Job Integration")
		indeed_job.job_opening = job_opening.name
		indeed_job.integration_method = settings.integration_method
		indeed_job.status = "Draft"
		indeed_job.insert()
		
		# Prepare job data
		job_data = prepare_job_data(job_opening, settings)
		
		# Post based on integration method
		if settings.integration_method == "API":
			response = post_via_indeed_api(job_data, settings, indeed_job)
		elif settings.integration_method == "XML_FEED":
			response = add_to_xml_feed(job_data, indeed_job)
		elif settings.integration_method == "THIRD_PARTY":
			response = post_via_third_party(job_data, settings, indeed_job)
		else:
			response = {"success": False, "error": "Invalid integration method"}
		
		# Update Indeed Job Integration record
		if response.get("success"):
			indeed_job.status = "Posted"
			indeed_job.posted_date = now_datetime()
			indeed_job.indeed_job_id = response.get("job_id")
			indeed_job.job_url = response.get("job_url")
			if settings.integration_method == "XML_FEED":
				indeed_job.xml_feed_included = 1
		else:
			indeed_job.status = "Error"
			indeed_job.error_message = response.get("error", "Unknown error")
		
		indeed_job.last_sync_date = now_datetime()
		indeed_job.save()
		frappe.db.commit()
		
		return response.get("success", False)
		
	except Exception as e:
		frappe.log_error(f"Indeed posting failed: {str(e)}", "Indeed Integration")
		return False


def prepare_job_data(job_opening, settings):
	"""Prepare job data for Indeed posting"""
	
	# Get location string
	location_parts = []
	if job_opening.get("city"):
		location_parts.append(job_opening.city)
	if job_opening.get("state"):
		location_parts.append(job_opening.state)
	if job_opening.get("country"):
		location_parts.append(job_opening.country)
	
	location = ", ".join(location_parts) if location_parts else ""
	
	# Get company info
	company_name = job_opening.company
	if settings.company_url:
		company_url = settings.company_url
	else:
		company_url = get_url()
	
	return {
		"title": job_opening.job_title,
		"description": job_opening.description or "",
		"location": location,
		"company": company_name,
		"company_url": company_url,
		"employment_type": job_opening.get("employment_type", "Full-time"),
		"experience_level": job_opening.get("experience", ""),
		"salary_min": job_opening.get("lower_range"),
		"salary_max": job_opening.get("upper_range"),
		"currency": job_opening.get("currency", "USD"),
		"application_url": f"{get_url()}/jobs/{job_opening.name}",
		"external_id": job_opening.name,
		"posting_date": job_opening.creation.strftime('%Y-%m-%d'),
		"department": job_opening.get("department", ""),
		"job_category": job_opening.get("designation", "")
	}


def post_via_indeed_api(job_data, settings, indeed_job):
	"""Post job using Indeed's Job Sync API (requires partner status)"""
	
	if not settings.access_token:
		return {"success": False, "error": "Access token not configured"}
	
	# OAuth authentication for Indeed API
	auth_headers = {
		"Authorization": f"Bearer {settings.access_token}",
		"Content-Type": "application/json"
	}
	
	# GraphQL mutation for job creation
	mutation = """
	mutation CreateJob($input: JobInput!) {
		createJob(input: $input) {
			job {
				id
				sourcedPostingId
				status
				jobUrl
			}
			errors {
				message
				field
			}
		}
	}
	"""
	
	variables = {
		"input": {
			"title": job_data["title"],
			"description": job_data["description"],
			"location": job_data["location"],
			"employmentType": map_employment_type(job_data["employment_type"]),
			"applicationUrl": job_data["application_url"],
			"externalId": job_data["external_id"],
			"companyName": job_data["company"]
		}
	}
	
	# Add salary if available
	if job_data.get("salary_min") and job_data.get("salary_max"):
		variables["input"]["salary"] = {
			"min": job_data["salary_min"],
			"max": job_data["salary_max"],
			"currency": job_data["currency"]
		}
	
	try:
		response = requests.post(
			"https://api.indeed.com/graphql",
			json={"query": mutation, "variables": variables},
			headers=auth_headers,
			timeout=30
		)
		
		if response.status_code == 200:
			result = response.json()
			job_result = result.get("data", {}).get("createJob", {})
			
			if not job_result.get("errors"):
				job_info = job_result.get("job", {})
				return {
					"success": True,
					"job_id": job_info.get("sourcedPostingId"),
					"job_url": job_info.get("jobUrl")
				}
			else:
				errors = job_result.get("errors", [])
				error_msg = "; ".join([err.get("message", "") for err in errors])
				return {"success": False, "error": error_msg}
		else:
			return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
		
	except Exception as e:
		return {"success": False, "error": str(e)}


def add_to_xml_feed(job_data, indeed_job):
	"""Add job to XML feed for Indeed crawler"""
	
	try:
		# Get the XML feed file path
		site_path = frappe.utils.get_site_path()
		xml_file_path = os.path.join(site_path, "public", "files", "indeed_jobs.xml")
		
		# Create directory if it doesn't exist
		os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)
		
		# Load existing XML or create new
		if os.path.exists(xml_file_path):
			tree = ET.parse(xml_file_path)
			root = tree.getroot()
		else:
			root = ET.Element("source")
			
			# Add publisher info
			publisher = ET.SubElement(root, "publisher")
			publisher.text = job_data["company"]
			
			publisherurl = ET.SubElement(root, "publisherurl")
			publisherurl.text = job_data["company_url"]
			
			tree = ET.ElementTree(root)
		
		# Update lastBuildDate
		lastbuild = root.find("lastBuildDate")
		if lastbuild is None:
			lastbuild = ET.SubElement(root, "lastBuildDate")
		lastbuild.text = now_datetime().strftime('%a, %d %b %Y %H:%M:%S GMT')
		
		# Create job element
		job = ET.SubElement(root, "job")
		
		# Add job fields
		job_fields = {
			"title": job_data["title"],
			"date": now_datetime().strftime('%a, %d %b %Y %H:%M:%S GMT'),
			"referencenumber": job_data["external_id"],
			"url": job_data["application_url"],
			"company": job_data["company"],
			"city": job_data["location"],
			"description": job_data["description"],
			"jobtype": job_data["employment_type"]
		}
		
		# Add salary if available
		if job_data.get("salary_min") and job_data.get("salary_max"):
			job_fields["salary"] = f"{job_data['salary_min']}-{job_data['salary_max']}"
		
		# Add category if available
		if job_data.get("job_category"):
			job_fields["category"] = job_data["job_category"]
		
		# Add experience if available
		if job_data.get("experience_level"):
			job_fields["experience"] = job_data["experience_level"]
		
		for field, value in job_fields.items():
			elem = ET.SubElement(job, field)
			if field in ["title", "company", "city", "description"]:
				elem.text = f"<![CDATA[{cstr(value)}]]>"
			else:
				elem.text = cstr(value)
		
		# Format and save XML
		rough_string = ET.tostring(root, 'utf-8')
		reparsed = minidom.parseString(rough_string)
		pretty_xml = reparsed.toprettyxml(indent="  ")
		
		# Remove extra blank lines
		pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
		
		with open(xml_file_path, 'w', encoding='utf-8') as f:
			f.write(pretty_xml)
		
		return {
			"success": True,
			"job_id": job_data["external_id"],
			"job_url": f"{get_url()}/files/indeed_jobs.xml",
			"method": "XML_FEED"
		}
		
	except Exception as e:
		return {"success": False, "error": str(e)}


def post_via_third_party(job_data, settings, indeed_job):
	"""Post job via third-party job board aggregator"""
	
	# This would depend on the specific third-party service
	# Placeholder implementation
	
	return {"success": False, "error": "Third-party integration not implemented"}


def map_employment_type(employment_type):
	"""Map ERPNext employment types to Indeed format"""
	
	mapping = {
		"Full-time": "FULL_TIME",
		"Part-time": "PART_TIME", 
		"Contract": "CONTRACT",
		"Temporary": "TEMPORARY",
		"Internship": "INTERNSHIP"
	}
	
	return mapping.get(employment_type, "FULL_TIME")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def indeed_application_webhook():
	"""Webhook endpoint to receive job applications from Indeed"""
	
	try:
		# Get webhook data
		data = frappe.local.form_dict
		
		# Validate webhook signature
		if not validate_indeed_webhook(data):
			frappe.local.response.http_status_code = 401
			return {"status": "error", "message": "Invalid webhook signature"}
		
		# Process the application
		result = create_job_applicant_from_indeed(data)
		
		if result.get("success"):
			return {"status": "success", "message": "Application processed", "applicant_id": result.get("applicant_id")}
		else:
			frappe.local.response.http_status_code = 400
			return {"status": "error", "message": result.get("error", "Processing failed")}
		
	except Exception as e:
		frappe.log_error(f"Indeed webhook error: {str(e)}", "Indeed Integration")
		frappe.local.response.http_status_code = 500
		return {"status": "error", "message": "Internal server error"}


def validate_indeed_webhook(data):
	"""Validate Indeed webhook signature for security"""
	
	settings = get_integration_settings()
	
	if not settings.webhook_secret:
		# If no secret is configured, skip validation (not recommended for production)
		return True
	
	# Get signature from headers
	signature = frappe.get_request_header("X-Indeed-Signature")
	if not signature:
		return False
	
	# Calculate expected signature
	payload = frappe.request.get_data()
	expected_signature = hmac.new(
		settings.webhook_secret.encode(),
		payload,
		hashlib.sha256
	).hexdigest()
	
	return hmac.compare_digest(f"sha256={expected_signature}", signature)


def create_job_applicant_from_indeed(application_data):
	"""Create ERPNext Job Applicant from Indeed application"""
	
	try:
		# Find the corresponding job opening
		indeed_job_id = application_data.get("job_id")
		job_opening = None
		
		if indeed_job_id:
			# Try to find by Indeed Job ID
			indeed_job = frappe.db.get_value(
				"Indeed Job Integration", 
				{"indeed_job_id": indeed_job_id}, 
				"job_opening"
			)
			if indeed_job:
				job_opening = indeed_job
		
		if not job_opening:
			# Try to find by external ID (job opening name)
			external_id = application_data.get("external_id")
			if external_id and frappe.db.exists("Job Opening", external_id):
				job_opening = external_id
		
		if not job_opening:
			return {"success": False, "error": "Could not find corresponding job opening"}
		
		# Check for duplicate application
		existing = frappe.db.exists("Job Applicant", {
			"email_id": application_data.get("candidate_email"),
			"job_title": application_data.get("job_title", "")
		})
		
		if existing:
			return {"success": False, "error": "Duplicate application"}
		
		# Create Job Applicant
		applicant = frappe.new_doc("Job Applicant")
		
		applicant.update({
			"applicant_name": application_data.get("candidate_name", "Unknown"),
			"email_id": application_data.get("candidate_email"),
			"phone_number": application_data.get("candidate_phone"),
			"job_title": application_data.get("job_title"),
			"source": "Indeed",
			"status": "Open",
			"notes": f"Applied via Indeed on {application_data.get('application_date', now_datetime())}",
			"custom_indeed_application_id": application_data.get("application_id")
		})
		
		# Handle resume/CV if provided
		if application_data.get("resume_url"):
			try:
				resume_file = download_indeed_resume(
					application_data["resume_url"],
					application_data.get("candidate_name", "candidate")
				)
				if resume_file:
					applicant.resume_attachment = resume_file
			except Exception as e:
				frappe.log_error(f"Resume download failed: {str(e)}", "Indeed Integration")
		
		# Handle screening questions
		if application_data.get("screening_answers"):
			applicant.cover_letter = format_screening_answers(
				application_data["screening_answers"]
			)
		
		applicant.insert(ignore_permissions=True)
		frappe.db.commit()
		
		# Send notification to HR team
		send_new_applicant_notification(applicant)
		
		return {"success": True, "applicant_id": applicant.name}
		
	except Exception as e:
		frappe.log_error(f"Job applicant creation failed: {str(e)}", "Indeed Integration")
		return {"success": False, "error": str(e)}


def download_indeed_resume(resume_url, candidate_name):
	"""Download resume from Indeed and attach to ERPNext"""
	
	try:
		response = requests.get(resume_url, timeout=30)
		response.raise_for_status()
		
		# Determine file extension
		content_type = response.headers.get('content-type', '')
		if 'pdf' in content_type:
			extension = 'pdf'
		elif 'doc' in content_type:
			extension = 'doc'
		else:
			extension = 'pdf'  # Default to PDF
		
		# Create safe filename
		safe_name = "".join(c for c in candidate_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
		file_name = f"{safe_name}_resume.{extension}"
		
		# Save file to ERPNext
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": file_name,
			"content": response.content,
			"is_private": 1,
			"folder": "Home/Attachments"
		})
		file_doc.insert(ignore_permissions=True)
		
		return file_doc.file_url
		
	except Exception as e:
		frappe.log_error(f"Resume download failed: {str(e)}", "Indeed Integration")
		return None


def format_screening_answers(answers):
	"""Format Indeed screening question answers"""
	
	if not answers or not isinstance(answers, list):
		return ""
	
	formatted = "Screening Questions & Answers:\n\n"
	
	for i, qa in enumerate(answers, 1):
		question = qa.get('question', f'Question {i}')
		answer = qa.get('answer', 'No answer provided')
		
		formatted += f"Q{i}: {question}\n"
		formatted += f"A{i}: {answer}\n\n"
	
	return formatted


def send_new_applicant_notification(applicant):
	"""Send notification to HR team about new applicant"""
	
	try:
		settings = get_integration_settings()
		
		# Determine recipients
		recipients = []
		if settings.contact_email:
			recipients.append(settings.contact_email)
		
		# Add HR Manager and HR User roles
		hr_users = frappe.get_all("Has Role", 
			filters={"role": ["in", ["HR Manager", "HR User"]], "parenttype": "User"},
			fields=["parent"]
		)
		
		for user in hr_users:
			user_email = frappe.db.get_value("User", user.parent, "email")
			if user_email and user_email not in recipients:
				recipients.append(user_email)
		
		if not recipients:
			return
		
		# Send email notification
		subject = f"New Job Application: {applicant.applicant_name}"
		
		message = f"""
		<h3>New Job Application Received</h3>
		<p>A new job application has been received from Indeed:</p>
		
		<table style="border-collapse: collapse; width: 100%;">
			<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Candidate:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{applicant.applicant_name}</td></tr>
			<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Email:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{applicant.email_id or 'Not provided'}</td></tr>
			<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Phone:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{applicant.phone_number or 'Not provided'}</td></tr>
			<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Position:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{applicant.job_title}</td></tr>
			<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Source:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{applicant.source}</td></tr>
		</table>
		
		<p><a href="{get_url()}/app/job-applicant/{applicant.name}" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px;">Review Application in ERPNext</a></p>
		"""
		
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			reference_doctype="Job Applicant",
			reference_name=applicant.name
		)
		
	except Exception as e:
		frappe.log_error(f"Notification failed: {str(e)}", "Indeed Integration")


@frappe.whitelist()
def regenerate_xml_feed():
	"""Regenerate complete XML feed from all active Indeed job integrations"""
	
	try:
		# Get all active job integrations
		job_integrations = frappe.get_all(
			"Indeed Job Integration",
			filters={"status": ["in", ["Posted", "Active"]]},
			fields=["job_opening", "name"]
		)
		
		if not job_integrations:
			return {"success": True, "message": "No active jobs to include in feed"}
		
		# Get XML file path
		site_path = frappe.utils.get_site_path()
		xml_file_path = os.path.join(site_path, "public", "files", "indeed_jobs.xml")
		
		# Create root element
		root = ET.Element("source")
		
		# Get settings for company info
		settings = get_integration_settings()
		
		# Add publisher info
		company_name = settings.company or "Company"
		publisher = ET.SubElement(root, "publisher")
		publisher.text = company_name
		
		publisherurl = ET.SubElement(root, "publisherurl")
		publisherurl.text = settings.company_url or get_url()
		
		lastbuild = ET.SubElement(root, "lastBuildDate")
		lastbuild.text = now_datetime().strftime('%a, %d %b %Y %H:%M:%S GMT')
		
		# Add jobs
		for integration in job_integrations:
			job_opening = frappe.get_doc("Job Opening", integration.job_opening)
			job_data = prepare_job_data(job_opening, settings)
			
			# Create job element
			job = ET.SubElement(root, "job")
			
			# Add job fields
			job_fields = {
				"title": job_data["title"],
				"date": job_opening.creation.strftime('%a, %d %b %Y %H:%M:%S GMT'),
				"referencenumber": job_data["external_id"],
				"url": job_data["application_url"],
				"company": job_data["company"],
				"city": job_data["location"],
				"description": job_data["description"],
				"jobtype": job_data["employment_type"]
			}
			
			# Add salary if available
			if job_data.get("salary_min") and job_data.get("salary_max"):
				job_fields["salary"] = f"{job_data['salary_min']}-{job_data['salary_max']}"
			
			for field, value in job_fields.items():
				elem = ET.SubElement(job, field)
				if field in ["title", "company", "city", "description"]:
					elem.text = f"<![CDATA[{cstr(value)}]]>"
				else:
					elem.text = cstr(value)
			
			# Update integration record
			frappe.db.set_value("Indeed Job Integration", integration.name, "xml_feed_included", 1)
		
		# Format and save XML
		rough_string = ET.tostring(root, 'utf-8')
		reparsed = minidom.parseString(rough_string)
		pretty_xml = reparsed.toprettyxml(indent="  ")
		
		# Remove extra blank lines
		pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
		
		with open(xml_file_path, 'w', encoding='utf-8') as f:
			f.write(pretty_xml)
		
		frappe.db.commit()
		
		return {
			"success": True, 
			"message": f"XML feed regenerated with {len(job_integrations)} jobs",
			"feed_url": f"{get_url()}/files/indeed_jobs.xml"
		}
		
	except Exception as e:
		frappe.log_error(f"XML feed regeneration failed: {str(e)}", "Indeed Integration")
		return {"success": False, "error": str(e)}
import frappe
from frappe import _
from frappe.utils import now_datetime, cstr
import json


@frappe.whitelist()
def execute_bulk_operation(job_names, operation, new_status=None, indeed_action=None):
	"""Execute bulk operations on selected jobs"""
	
	if isinstance(job_names, str):
		job_names = json.loads(job_names)
	
	results = []
	success_count = 0
	error_count = 0
	
	for job_name in job_names:
		try:
			result = process_single_job(job_name, operation, new_status, indeed_action)
			results.append(result)
			
			if result["success"]:
				success_count += 1
			else:
				error_count += 1
				
		except Exception as e:
			error_result = {
				"job": job_name,
				"success": False,
				"message": f"Error: {str(e)}"
			}
			results.append(error_result)
			error_count += 1
	
	# Commit all changes
	frappe.db.commit()
	
	# Prepare summary
	summary = f"Operation completed: {success_count} successful, {error_count} errors"
	
	# Format results for display
	results_text = "\n".join([
		f"• {r['job']}: {r['message']}" for r in results
	])
	
	return {
		"success": error_count == 0,
		"summary": summary,
		"results": results_text,
		"details": results
	}


def process_single_job(job_name, operation, new_status=None, indeed_action=None):
	"""Process a single job with the specified operation"""
	
	job = frappe.get_doc("Job Opening", job_name)
	
	if operation == "Update Job Status":
		if not new_status:
			return {"job": job_name, "success": False, "message": "New status required"}
		
		old_status = job.status
		job.status = new_status
		job.save()
		
		return {
			"job": job_name,
			"success": True,
			"message": f"Status updated from {old_status} to {new_status}"
		}
	
	elif operation == "Post to Indeed":
		if indeed_action == "Enable Indeed Posting":
			job.custom_post_to_indeed = 1
			job.save()
			
			# Trigger Indeed posting
			from indeed.indeed.utils import post_job_to_indeed
			success = post_job_to_indeed(job)
			
			if success:
				return {"job": job_name, "success": True, "message": "Enabled and posted to Indeed"}
			else:
				return {"job": job_name, "success": False, "message": "Enabled but posting failed"}
		
		elif indeed_action == "Disable Indeed Posting":
			job.custom_post_to_indeed = 0
			job.save()
			
			# Remove from Indeed feed
			remove_from_indeed_feed(job_name)
			
			return {"job": job_name, "success": True, "message": "Disabled Indeed posting"}
		
		elif indeed_action == "Force Refresh":
			# Force regenerate XML feed
			from indeed.indeed.utils import regenerate_xml_feed
			regenerate_xml_feed()
			
			return {"job": job_name, "success": True, "message": "XML feed refreshed"}
	
	elif operation == "Remove from Indeed":
		# Remove job from Indeed integration
		remove_from_indeed_feed(job_name)
		job.custom_post_to_indeed = 0
		job.save()
		
		return {"job": job_name, "success": True, "message": "Removed from Indeed feed"}
	
	elif operation == "Export Selected":
		# This would typically generate a file download
		return {"job": job_name, "success": True, "message": "Included in export"}
	
	else:
		return {"job": job_name, "success": False, "message": f"Unknown operation: {operation}"}


def remove_from_indeed_feed(job_name):
	"""Remove job from Indeed integration"""
	
	# Find and update Indeed job integration record
	integration = frappe.db.get_value(
		"Indeed Job Integration",
		{"job_opening": job_name},
		["name"]
	)
	
	if integration:
		integration_doc = frappe.get_doc("Indeed Job Integration", integration)
		integration_doc.status = "Removed"
		integration_doc.save()


@frappe.whitelist()
def export_integration_report(from_date=None, to_date=None):
	"""Export comprehensive integration report"""
	
	from frappe.utils import get_url
	import csv
	import os
	
	# Set default dates
	if not from_date:
		from_date = frappe.utils.add_days(frappe.utils.now_datetime(), -30)
	if not to_date:
		to_date = frappe.utils.now_datetime()
	
	# Get comprehensive data
	data = frappe.db.sql("""
		SELECT 
			jo.name as job_id,
			jo.job_title,
			jo.company,
			jo.department,
			jo.status as job_status,
			jo.creation as job_created,
			iji.status as indeed_status,
			iji.creation as indeed_posted,
			iji.posted_date,
			iji.error_message,
			COUNT(ja.name) as applications,
			COUNT(CASE WHEN ja.source = 'Indeed' THEN 1 END) as indeed_applications
		FROM `tabJob Opening` jo
		LEFT JOIN `tabIndeed Job Integration` iji ON iji.job_opening = jo.name
		LEFT JOIN `tabJob Applicant` ja ON ja.job_title = jo.name
		WHERE jo.creation BETWEEN %s AND %s
		GROUP BY jo.name, jo.job_title, jo.company, jo.department, 
				 jo.status, jo.creation, iji.status, iji.creation, 
				 iji.posted_date, iji.error_message
		ORDER BY jo.creation DESC
	""", [from_date, to_date], as_dict=True)
	
	# Create CSV file
	filename = f"indeed_integration_report_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
	filepath = os.path.join(frappe.utils.get_site_path(), "public", "files", filename)
	
	with open(filepath, 'w', newline='') as csvfile:
		if data:
			fieldnames = data[0].keys()
			writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
			writer.writeheader()
			writer.writerows(data)
	
	# Return download URL
	download_url = get_url() + f"/files/{filename}"
	
	return {
		"success": True,
		"download_url": download_url,
		"filename": filename,
		"record_count": len(data)
	}
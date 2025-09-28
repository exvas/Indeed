import frappe
from frappe import _


def after_install():
	"""Post-installation setup for Indeed Integration"""
	
	try:
		# Create custom fields
		create_custom_fields()
		
		# Create integration settings
		create_integration_settings()
		
		# Create sample data (optional)
		# create_sample_data()
		
		frappe.db.commit()
		
		print("Indeed Integration app installed successfully!")
		print("Please configure Indeed Integration Settings to start using the integration.")
		
	except Exception as e:
		frappe.log_error(f"Indeed Integration installation failed: {str(e)}", "Installation Error")
		print(f"Installation error: {str(e)}")


def create_custom_fields():
	"""Create custom fields for Indeed integration"""
	
	custom_fields = [
		{
			"doctype": "Job Opening",
			"fieldname": "custom_indeed_job_id",
			"label": "Indeed Job ID",
			"fieldtype": "Data",
			"read_only": 1,
			"insert_after": "job_title",
			"description": "Auto-generated ID when job is posted to Indeed"
		},
		{
			"doctype": "Job Opening",
			"fieldname": "custom_post_to_indeed",
			"label": "Post to Indeed",
			"fieldtype": "Check",
			"default": "1",
			"insert_after": "publish",
			"description": "Automatically post this job to Indeed when saved"
		},
		{
			"doctype": "Job Applicant",
			"fieldname": "custom_indeed_application_id",
			"label": "Indeed Application ID",
			"fieldtype": "Data",
			"read_only": 1,
			"insert_after": "source",
			"description": "Application ID from Indeed"
		},
		{
			"doctype": "Job Applicant",
			"fieldname": "custom_indeed_profile_url",
			"label": "Indeed Profile URL",
			"fieldtype": "Data",
			"read_only": 1,
			"insert_after": "custom_indeed_application_id",
			"description": "Link to candidate's Indeed profile"
		}
	]
	
	for field in custom_fields:
		if not frappe.db.exists("Custom Field", {"dt": field["doctype"], "fieldname": field["fieldname"]}):
			try:
				custom_field = frappe.get_doc({
					"doctype": "Custom Field",
					"dt": field["doctype"],
					"fieldname": field["fieldname"],
					"label": field["label"],
					"fieldtype": field["fieldtype"],
					"read_only": field.get("read_only", 0),
					"insert_after": field.get("insert_after"),
					"description": field.get("description", ""),
					"default": field.get("default")
				})
				custom_field.insert(ignore_permissions=True)
				print(f"Created custom field: {field['fieldname']} in {field['doctype']}")
			except Exception as e:
				print(f"Error creating custom field {field['fieldname']}: {str(e)}")


def create_integration_settings():
	"""Create Indeed Integration Settings document"""
	
	if not frappe.db.exists("Indeed Integration Settings", "Indeed Integration Settings"):
		try:
			settings = frappe.get_doc({
				"doctype": "Indeed Integration Settings",
				"name": "Indeed Integration Settings",
				"enable_auto_posting": 0,
				"integration_method": "XML_FEED",
				"xml_feed_url": "/files/indeed_jobs.xml",
				"company": frappe.defaults.get_global_default("company") or None
			})
			settings.insert(ignore_permissions=True)
			print("Created Indeed Integration Settings")
		except Exception as e:
			print(f"Error creating integration settings: {str(e)}")


def create_sample_data():
	"""Create sample data for testing (optional)"""
	
	# This is optional - you can create sample job openings for testing
	pass


def setup_website_settings():
	"""Configure website settings for webhook endpoints"""
	
	try:
		# Ensure website is enabled for webhook access
		website_settings = frappe.get_single("Website Settings")
		if not website_settings.enable_website:
			website_settings.enable_website = 1
			website_settings.save(ignore_permissions=True)
			print("Enabled website for webhook access")
	except Exception as e:
		print(f"Error configuring website settings: {str(e)}")


def add_permissions():
	"""Add custom permissions for Indeed Integration"""
	
	try:
		# Add permissions for Indeed Job Integration
		permissions = [
			{
				"role": "HR Manager",
				"doctype": "Indeed Job Integration",
				"permlevel": 0,
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 0,
				"cancel": 0,
				"amend": 0
			},
			{
				"role": "HR User",
				"doctype": "Indeed Job Integration", 
				"permlevel": 0,
				"read": 1,
				"write": 0,
				"create": 0,
				"delete": 0,
				"submit": 0,
				"cancel": 0,
				"amend": 0
			}
		]
		
		for perm in permissions:
			if not frappe.db.exists("Custom DocPerm", {"role": perm["role"], "parent": perm["doctype"]}):
				custom_perm = frappe.get_doc({
					"doctype": "Custom DocPerm",
					"role": perm["role"],
					"parent": perm["doctype"],
					"parenttype": "DocType",
					"parentfield": "permissions",
					"permlevel": perm["permlevel"],
					"read": perm["read"],
					"write": perm["write"],
					"create": perm["create"],
					"delete": perm["delete"]
				})
				custom_perm.insert(ignore_permissions=True)
		
		print("Added custom permissions")
		
	except Exception as e:
		print(f"Error adding permissions: {str(e)}")


def create_notification_templates():
	"""Create email notification templates"""
	
	try:
		# Email Template for new job applicant
		if not frappe.db.exists("Email Template", "Indeed New Application"):
			email_template = frappe.get_doc({
				"doctype": "Email Template",
				"name": "Indeed New Application",
				"subject": "New Job Application from Indeed: {{ doc.applicant_name }}",
				"response": """
<h3>New Job Application Received</h3>

<p>A new job application has been received from Indeed:</p>

<table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
	<tr>
		<td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Candidate Name:</td>
		<td style="padding: 8px; border: 1px solid #ddd;">{{ doc.applicant_name }}</td>
	</tr>
	<tr>
		<td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Email:</td>
		<td style="padding: 8px; border: 1px solid #ddd;">{{ doc.email_id or 'Not provided' }}</td>
	</tr>
	<tr>
		<td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Phone:</td>
		<td style="padding: 8px; border: 1px solid #ddd;">{{ doc.phone_number or 'Not provided' }}</td>
	</tr>
	<tr>
		<td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Position:</td>
		<td style="padding: 8px; border: 1px solid #ddd;">{{ doc.job_title }}</td>
	</tr>
	<tr>
		<td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Source:</td>
		<td style="padding: 8px; border: 1px solid #ddd;">{{ doc.source }}</td>
	</tr>
</table>

<p><a href="{{ frappe.utils.get_url() }}/app/job-applicant/{{ doc.name }}" 
   style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px;">
   Review Application in ERPNext
</a></p>

<p>Best regards,<br>ERPNext HR System</p>
				""",
				"use_html": 1
			})
			email_template.insert(ignore_permissions=True)
			print("Created email template for new applications")
			
	except Exception as e:
		print(f"Error creating email templates: {str(e)}")
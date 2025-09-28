import frappe
from frappe import _
from frappe.model.document import Document


class IndeedJobIntegration(Document):
	"""Custom DocType to manage Indeed job postings"""
	
	def before_insert(self):
		"""Set location and salary range from job opening"""
		if self.job_opening:
			job_opening = frappe.get_doc("Job Opening", self.job_opening)
			
			# Set location
			location_parts = []
			if job_opening.get("city"):
				location_parts.append(job_opening.city)
			if job_opening.get("state"):
				location_parts.append(job_opening.state)
			if job_opening.get("country"):
				location_parts.append(job_opening.country)
			
			self.location = ", ".join(location_parts)
			
			# Set salary range
			if job_opening.get("lower_range") and job_opening.get("upper_range"):
				currency_symbol = frappe.db.get_value("Currency", job_opening.currency, "symbol") or ""
				self.salary_range = f"{currency_symbol}{job_opening.lower_range} - {currency_symbol}{job_opening.upper_range}"
			
			# Set application URL
			self.application_url = f"{frappe.utils.get_url()}/jobs/{job_opening.name}"
	
	def validate(self):
		"""Validate the document"""
		if not frappe.db.exists("Job Opening", self.job_opening):
			frappe.throw(_("Invalid Job Opening selected"))
	
	def on_update(self):
		"""Update job opening with indeed job id if available"""
		if self.indeed_job_id and self.job_opening:
			frappe.db.set_value("Job Opening", self.job_opening, "custom_indeed_job_id", self.indeed_job_id)
import frappe
from frappe import _
from frappe.model.document import Document


class IndeedIntegrationSettings(Document):
	"""Settings for Indeed integration"""
	
	def onload(self):
		"""Set webhook URL automatically"""
		from frappe.utils import get_url
		self.webhook_url = get_url() + "/api/method/indeed.indeed.api.webhook_job_application"
	
	def validate(self):
		if self.enable_auto_posting and self.integration_method == "API" and not self.api_key:
			frappe.throw(_("API Key is required when auto-posting is enabled with API method"))
		
		if self.enable_auto_posting and not self.company:
			frappe.throw(_("Default Company is required when auto-posting is enabled"))
	
	def on_update(self):
		"""Clear cache when settings are updated"""
		frappe.cache().delete_key("indeed_integration_settings")
	

import frappe


def boot_session(bootinfo):
	"""Add Indeed Integration settings to boot session"""
	
	if frappe.session.user != "Guest":
		try:
			# Add Indeed integration status to boot info
			settings = frappe.get_single("Indeed Integration Settings")
			bootinfo.indeed_integration = {
				"enabled": settings.enable_auto_posting,
				"method": settings.integration_method,
				"webhook_url": f"{frappe.utils.get_url()}/api/method/indeed.indeed_integration.utils.indeed_application_webhook"
			}
		except Exception:
			# If settings don't exist yet (e.g., during installation)
			bootinfo.indeed_integration = {
				"enabled": False,
				"method": "XML_FEED",
				"webhook_url": f"{frappe.utils.get_url()}/api/method/indeed.indeed_integration.utils.indeed_application_webhook"
			}
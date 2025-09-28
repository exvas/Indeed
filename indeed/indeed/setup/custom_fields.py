# Custom Fields for Job Opening to support A/B Testing

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def add_custom_fields():
	"""Add custom fields to Job Opening for A/B testing support"""
	
	custom_fields = {
		"Job Opening": [
			{
				"fieldname": "custom_ab_test_campaign",
				"label": "A/B Test Campaign",
				"fieldtype": "Link",
				"options": "AB Test Campaign",
				"insert_after": "custom_post_to_indeed",
				"read_only": 1,
				"description": "Associated A/B test campaign if this is a test variant"
			},
			{
				"fieldname": "custom_ab_test_variant",
				"label": "A/B Test Variant",
				"fieldtype": "Data",
				"insert_after": "custom_ab_test_campaign",
				"read_only": 1,
				"description": "Variant identifier (Variant A, Variant B)"
			}
		]
	}
	
	create_custom_fields(custom_fields)


def execute():
	"""Execute the custom field creation"""
	add_custom_fields()
	print("Custom fields for A/B testing added successfully!")
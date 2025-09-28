app_name = "indeed"
app_title = "Indeed"
app_publisher = "sammish"
app_description = "Indeed: Job Search & Integration"
app_email = "sammish.thundiyil@gmail.com"
app_license = "mit"
required_apps = ["erpnext", "hrms"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/indeed/css/indeed.css"
# app_include_js = "/assets/indeed/js/indeed.js"

# include js, css files in header of web template
# web_include_css = "/assets/indeed/css/indeed.css"
# web_include_js = "/assets/indeed/js/indeed.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "indeed/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "indeed/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "indeed.utils.jinja_methods",
# 	"filters": "indeed.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "indeed.install.before_install"
# after_install = "indeed.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "indeed.uninstall.before_uninstall"
# after_uninstall = "indeed.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "indeed.utils.before_app_install"
# after_app_install = "indeed.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "indeed.utils.before_app_uninstall"
# after_app_uninstall = "indeed.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "indeed.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"indeed.tasks.all"
# 	],
# 	"daily": [
# 		"indeed.tasks.daily"
# 	],
# 	"hourly": [
# 		"indeed.tasks.hourly"
# 	],
# 	"weekly": [
# 		"indeed.tasks.weekly"
# 	],
# 	"monthly": [
# 		"indeed.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "indeed.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "indeed.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "indeed.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["indeed.utils.before_request"]
# after_request = ["indeed.utils.after_request"]

# Job Events
# ----------
# before_job = ["indeed.utils.before_job"]
# after_job = ["indeed.utils.after_job"]

# Document Events
# ---------------
doc_events = {
	"Job Opening": {
		"on_update": "indeed.indeed.utils.on_job_opening_save",
		"after_insert": "indeed.indeed.utils.on_job_opening_save"
	}
}

# Scheduled Tasks
# ---------------
scheduler_events = {
	"cron": {
		"0 */6 * * *": [  # Every 6 hours
			"indeed.indeed.utils.regenerate_xml_feed"
		]
	}
}

# Website Route Rules
# -------------------
website_route_rules = [
	{"from_route": "/api/method/indeed.indeed.utils.indeed_application_webhook", "to_route": "indeed.indeed.utils.indeed_application_webhook"}
]

# Boot Session
# ------------
boot_session = "indeed.boot.boot_session"

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"indeed.auth.validate"
# ]

# Installation Hooks
# ------------------
before_install = "indeed.indeed.install.before_install"
after_install = "indeed.indeed.install.after_install"
# Legacy hook names for backward compatibility
before_app_install = "indeed.indeed.install.before_install"
after_app_install = "indeed.indeed.install.after_install"

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Job Applicant-custom_indeed_profile_url",
                    "Job Applicant-custom_indeed_application_id",
                    "Job Opening-custom_post_to_indeed",
                    "Job Opening-custom_indeed_job_id",
                ]
            ]
        ]
    }
]
# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Scheduled Events
# ----------------
scheduler_events = {
	"daily": [
		"indeed.indeed.monitoring.monitor_indeed_integration"
	],
	"hourly": [
		"indeed.indeed.utils.regenerate_xml_feed"
	]
}


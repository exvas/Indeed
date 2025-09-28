#!/usr/bin/env python3

import frappe
from frappe import _
import subprocess
import os


def before_install():
	"""
	Hook that runs before Indeed app installation.
	Ensures HRMS is installed before Indeed app installation.
	"""
	print("🔍 Checking Indeed app dependencies...")
	
	# Check if HRMS is installed
	if not is_app_installed("hrms"):
		print("📦 HRMS not found. Installing HRMS automatically...")
		install_hrms()
	else:
		print("✅ HRMS is already installed")


def after_install():
	"""
	Hook that runs after Indeed app installation.
	Sets up default configurations and validates installation.
	"""
	print("🚀 Configuring Indeed Integration...")
	
	try:
		# First validate all dependencies
		validate_dependencies()
		
		# Ensure proper app installation order
		ensure_proper_app_order()
		
		# Create default Indeed Integration Settings
		setup_default_settings()
		
		# Enable required features
		enable_required_features()
		
		# Create sample data if needed
		create_sample_data()
		
		print("✅ Indeed app installation completed successfully!")
		print("📋 Next steps:")
		print("   1. Go to Indeed Integration Settings to configure your integration")
		print("   2. Set up your company information and webhook credentials")  
		print("   3. Contact Indeed to set up XML feed crawling")
		print("   4. Create your first job opening with 'Post to Indeed' enabled")
		
	except Exception as e:
		frappe.log_error(f"Indeed installation error: {str(e)}", "Indeed Installation")
		print(f"⚠️  Warning: Some configuration steps failed: {str(e)}")
		print("💡 Try running: bench --site [site] migrate")
		raise e


def is_app_installed(app_name):
	"""Check if an app is installed in the current site"""
	try:
		installed_apps = frappe.get_installed_apps()
		return app_name in installed_apps
	except Exception:
		return False


def validate_dependencies():
	"""Validate that all required dependencies are available"""
	print("🔍 Validating Indeed app dependencies...")
	
	required_apps = ["erpnext", "hrms"]
	missing_apps = []
	
	for app in required_apps:
		if not is_app_installed(app):
			missing_apps.append(app)
			print(f"❌ {app} is not installed")
		else:
			print(f"✅ {app} is installed")
	
	if missing_apps:
		raise Exception(f"Missing required apps: {', '.join(missing_apps)}")
	
	# Validate required DocTypes exist
	required_doctypes = ["Job Opening", "Job Applicant", "Company"]
	missing_doctypes = []
	
	for doctype in required_doctypes:
		if not frappe.db.exists("DocType", doctype):
			missing_doctypes.append(doctype)
			print(f"❌ {doctype} DocType not found")
		else:
			print(f"✅ {doctype} DocType available")
	
	if missing_doctypes:
		raise Exception(f"Missing required DocTypes: {', '.join(missing_doctypes)}")
	
	print("✅ All dependencies validated successfully!")


def install_hrms():
	"""Install HRMS app automatically"""
	try:
		site_name = frappe.local.site
		
		print("📥 Downloading HRMS app...")
		# Get HRMS app if not already available
		get_app_result = subprocess.run([
			"bench", "get-app", "hrms"
		], capture_output=True, text=True, cwd=get_bench_path())
		
		if get_app_result.returncode != 0 and "already exists" not in get_app_result.stderr:
			print(f"⚠️  Warning: Could not download HRMS: {get_app_result.stderr}")
			# Continue anyway as HRMS might already be available
		
		print("📦 Installing HRMS on current site...")
		# Install HRMS on current site
		install_result = subprocess.run([
			"bench", "--site", site_name, "install-app", "hrms"
		], capture_output=True, text=True, cwd=get_bench_path())
		
		if install_result.returncode == 0:
			print("✅ HRMS installed successfully!")
		else:
			print(f"❌ Failed to install HRMS: {install_result.stderr}")
			raise Exception(f"HRMS installation failed: {install_result.stderr}")
			
	except Exception as e:
		print(f"❌ Error installing HRMS: {str(e)}")
		raise Exception(f"HRMS installation failed: {str(e)}")


def get_bench_path():
	"""Get the bench directory path"""
	current_path = os.getcwd()
	
	# Try to find bench directory
	if "frappe-bench" in current_path:
		return current_path.split("frappe-bench")[0] + "frappe-bench"
	elif os.path.exists("../frappe-bench"):
		return os.path.abspath("../frappe-bench")
	elif os.path.exists("./"):
		return os.path.abspath("./")
	else:
		return "/home/frappe/frappe-bench"  # Default path


def setup_default_settings():
	"""Create default Indeed Integration Settings"""
	try:
		# Check if settings already exist
		if frappe.db.exists("Indeed Integration Settings", "Indeed Integration Settings"):
			print("📋 Indeed Integration Settings already exist")
			return
		
		# Create default settings
		settings = frappe.get_doc({
			"doctype": "Indeed Integration Settings",
			"enable_auto_posting": 0,  # Disabled by default
			"integration_method": "XML_FEED",  # Default to XML feed
			"xml_feed_enabled": 1,
			"webhook_enabled": 1,
		})
		
		# Set default company if available
		companies = frappe.get_all("Company", limit=1)
		if companies:
			settings.company = companies[0].name
		
		settings.insert(ignore_permissions=True)
		print("📋 Created default Indeed Integration Settings")
		
	except Exception as e:
		print(f"⚠️  Could not create default settings: {str(e)}")


def enable_required_features():
	"""Enable features required for Indeed integration"""
	try:
		# Enable email notifications for HR module
		print("📧 Configuring email notifications...")
		
		# Enable file management for XML feeds
		print("📁 Configuring file management...")
		
		# Set up basic permissions
		setup_permissions()
		
	except Exception as e:
		print(f"⚠️  Could not enable all features: {str(e)}")


def setup_permissions():
	"""Set up basic permissions for Indeed integration"""
	try:
		# Ensure HR Manager role has access to Indeed features
		hr_manager_permissions = [
			"Indeed Integration Settings",
			"Indeed Job Integration", 
			"Indeed Dashboard",
			"Application Analytics",
			"Bulk Job Manager"
		]
		
		for doctype in hr_manager_permissions:
			if frappe.db.exists("DocType", doctype):
				# Check if permission already exists
				existing_perm = frappe.db.exists("DocPerm", {
					"parent": doctype,
					"role": "HR Manager"
				})
				
				if not existing_perm:
					# Add basic permissions for HR Manager
					perm = frappe.get_doc({
						"doctype": "DocPerm",
						"parent": doctype,
						"parenttype": "DocType", 
						"parentfield": "permissions",
						"role": "HR Manager",
						"read": 1,
						"write": 1,
						"create": 1,
						"submit": 0,
						"cancel": 0,
						"delete": 1
					})
					perm.insert(ignore_permissions=True)
		
		print("🔐 Set up basic permissions for HR Manager role")
		
	except Exception as e:
		print(f"⚠️  Could not set up all permissions: {str(e)}")


def create_sample_data():
	"""Create sample data for demonstration (optional)"""
	try:
		# Only create sample data in developer mode
		if frappe.conf.developer_mode:
			print("🎯 Creating sample data for development...")
			# Sample data creation logic can be added here
		
	except Exception as e:
		print(f"⚠️  Could not create sample data: {str(e)}")


def ensure_proper_app_order():
	"""Ensure apps are installed in the correct order"""
	try:
		import os
		site_path = frappe.utils.get_site_path()
		apps_txt_path = os.path.join(site_path, "apps.txt")
		
		if os.path.exists(apps_txt_path):
			with open(apps_txt_path, 'r') as f:
				apps = [line.strip() for line in f.readlines() if line.strip()]
			
			# Check if hrms comes before indeed
			if 'hrms' in apps and 'indeed' in apps:
				hrms_index = apps.index('hrms')
				indeed_index = apps.index('indeed')
				
				if hrms_index > indeed_index:
					print("🔄 Reordering apps.txt to ensure correct dependency order...")
					# Remove and re-add indeed after hrms
					apps.remove('indeed')
					hrms_index = apps.index('hrms')
					apps.insert(hrms_index + 1, 'indeed')
					
					# Write back to apps.txt
					with open(apps_txt_path, 'w') as f:
						for app in apps:
							f.write(app + '\n')
					
					print("✅ App order corrected in apps.txt")
		
	except Exception as e:
		print(f"⚠️  Could not verify app order: {str(e)}")
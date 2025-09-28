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
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_days, date_diff
import random
import math


class ABTestCampaign(Document):
	"""A/B Testing Campaign for Job Descriptions"""
	
	def validate(self):
		"""Validate test configuration"""
		
		if self.start_date and self.end_date:
			if self.start_date >= self.end_date:
				frappe.throw(_("End date must be after start date"))
		
		if self.traffic_split < 10 or self.traffic_split > 90:
			frappe.throw(_("Traffic split must be between 10% and 90%"))
		
		# Validate that variants are different
		if self.test_variable == "Job Title":
			if self.variant_a_title == self.variant_b_title:
				frappe.throw(_("Variant A and B titles must be different for testing"))
		
		if self.test_variable == "Job Description":
			if self.variant_a_description == self.variant_b_description:
				frappe.throw(_("Variant A and B descriptions must be different for testing"))
	
	def before_save(self):
		"""Auto-populate variants from base job if not set"""
		
		if self.base_job_opening and not self.variant_a_title:
			job = frappe.get_doc("Job Opening", self.base_job_opening)
			
			# Set Variant A as the original
			self.variant_a_title = job.job_title
			self.variant_a_description = job.description
			
			# Variant B needs to be set manually by user
			if not self.variant_b_title:
				self.variant_b_title = job.job_title + " (Variant B)"
	
	def on_update(self):
		"""Handle status changes"""
		
		if self.status == "Active" and self.has_value_changed("status"):
			self.start_ab_test()
		
		elif self.status == "Completed" and self.has_value_changed("status"):
			self.calculate_results()
	
	def start_ab_test(self):
		"""Start the A/B test by creating variant job postings"""
		
		if not self.base_job_opening:
			frappe.throw(_("Base job opening is required to start test"))
		
		base_job = frappe.get_doc("Job Opening", self.base_job_opening)
		
		# Create Variant A job (based on original)
		variant_a = self.create_variant_job(base_job, "A", self.variant_a_title, self.variant_a_description)
		
		# Create Variant B job
		variant_b = self.create_variant_job(base_job, "B", self.variant_b_title, self.variant_b_description)
		
		# Link variants to this test
		self.db_set("variant_a_job", variant_a.name)
		self.db_set("variant_b_job", variant_b.name)
		
		frappe.msgprint(_("A/B Test started! Variant jobs created and posted to Indeed."))
	
	def create_variant_job(self, base_job, variant_letter, title, description):
		"""Create a variant job posting"""
		
		variant_job = frappe.copy_doc(base_job)
		
		# Update with variant content
		variant_job.job_title = title
		variant_job.description = description
		variant_job.job_opening = None  # Clear to get new name
		
		# Add AB test identifier
		variant_job.custom_ab_test_campaign = self.name
		variant_job.custom_ab_test_variant = f"Variant {variant_letter}"
		
		# Enable Indeed posting
		variant_job.custom_post_to_indeed = 1
		
		variant_job.insert()
		
		return variant_job
	
	def calculate_results(self):
		"""Calculate test results and determine winner"""
		
		# Get application data for both variants
		variant_a_data = self.get_variant_metrics("variant_a_job")
		variant_b_data = self.get_variant_metrics("variant_b_job")
		
		# Update metrics
		self.variant_a_applications = variant_a_data["applications"]
		self.variant_a_conversion = variant_a_data["conversion_rate"]
		self.variant_b_applications = variant_b_data["applications"]
		self.variant_b_conversion = variant_b_data["conversion_rate"]
		
		# Determine winner using statistical significance
		self.determine_winner(variant_a_data, variant_b_data)
		
		# Generate conclusions
		self.generate_test_conclusion(variant_a_data, variant_b_data)
	
	def get_variant_metrics(self, variant_field):
		"""Get metrics for a specific variant"""
		
		variant_job = self.get(variant_field)
		if not variant_job:
			return {"applications": 0, "conversion_rate": 0, "views": 0}
		
		# Count applications received
		applications = frappe.db.count(
			"Job Applicant",
			filters={
				"job_title": variant_job,
				"application_date": ["between", [self.start_date, self.end_date]]
			}
		)
		
		# Get job views (if tracked) - placeholder for now
		views = 100  # This would come from Indeed analytics API
		
		# Calculate conversion rate
		conversion_rate = (applications / views * 100) if views > 0 else 0
		
		return {
			"applications": applications,
			"conversion_rate": conversion_rate,
			"views": views
		}
	
	def determine_winner(self, variant_a_data, variant_b_data):
		"""Determine statistical winner using chi-square test"""
		
		# Simple statistical significance calculation
		# In production, you'd use proper statistical tests
		
		a_apps = variant_a_data["applications"]
		a_views = variant_a_data["views"]
		b_apps = variant_b_data["applications"]
		b_views = variant_b_data["views"]
		
		total_apps = a_apps + b_apps
		total_views = a_views + b_views
		
		if total_apps == 0 or total_views == 0:
			self.winner = "No Significant Difference"
			self.confidence_level = 0
			self.statistical_significance = 0
			return
		
		# Calculate expected applications for each variant
		expected_a = (a_views / total_views) * total_apps
		expected_b = (b_views / total_views) * total_apps
		
		# Chi-square test (simplified)
		if expected_a > 0 and expected_b > 0:
			chi_square = ((a_apps - expected_a) ** 2 / expected_a) + ((b_apps - expected_b) ** 2 / expected_b)
			
			# Simplified confidence calculation
			if chi_square > 3.84:  # 95% confidence threshold
				self.statistical_significance = 1
				self.confidence_level = 95
				
				if variant_a_data["conversion_rate"] > variant_b_data["conversion_rate"]:
					self.winner = "Variant A"
				else:
					self.winner = "Variant B"
			else:
				self.winner = "No Significant Difference"
				self.confidence_level = chi_square / 3.84 * 95  # Rough approximation
				self.statistical_significance = 0
		else:
			self.winner = "No Significant Difference"
			self.confidence_level = 0
			self.statistical_significance = 0
	
	def generate_test_conclusion(self, variant_a_data, variant_b_data):
		"""Generate detailed test conclusions and recommendations"""
		
		conclusion = f"""
A/B Test Results for: {self.test_name}

Test Period: {self.start_date} to {self.end_date}
Test Variable: {self.test_variable}

RESULTS SUMMARY:
================
Variant A ({self.variant_a_title}):
- Applications: {variant_a_data['applications']}
- Conversion Rate: {variant_a_data['conversion_rate']:.2f}%

Variant B ({self.variant_b_title}):
- Applications: {variant_b_data['applications']} 
- Conversion Rate: {variant_b_data['conversion_rate']:.2f}%

WINNER: {self.winner}
Confidence Level: {self.confidence_level:.1f}%
Statistical Significance: {'Yes' if self.statistical_significance else 'No'}

RECOMMENDATIONS:
================
"""
		
		if self.winner == "Variant A":
			conclusion += f"""
✅ Variant A outperformed Variant B
- Use Variant A approach for future similar jobs
- Consider applying Variant A elements to other job postings
- Difference: {abs(variant_a_data['conversion_rate'] - variant_b_data['conversion_rate']):.2f} percentage points
"""
		elif self.winner == "Variant B":
			conclusion += f"""
✅ Variant B outperformed Variant A  
- Implement Variant B approach for future jobs
- Update existing job templates with Variant B elements
- Difference: {abs(variant_b_data['conversion_rate'] - variant_a_data['conversion_rate']):.2f} percentage points
"""
		else:
			conclusion += """
📊 No significant difference found
- Both variants performed similarly
- Consider testing different variables (title, benefits, requirements)
- May need longer test period or higher traffic volume
- Current differences may be due to random variation
"""
		
		if not self.statistical_significance:
			conclusion += f"""

⚠️  CAUTION: Results not statistically significant
- Consider running test longer for more reliable data
- Current confidence level: {self.confidence_level:.1f}%
- Recommended minimum: 95% confidence for decision making
"""
		
		self.test_conclusion = conclusion

	@frappe.whitelist()
	def clone_winning_variant(self):
		"""Clone the winning variant to create a new optimized job posting"""
		
		if not self.winner or self.winner == "No Significant Difference":
			frappe.throw(_("Cannot clone - no clear winner determined"))
		
		winning_job_field = "variant_a_job" if self.winner == "Variant A" else "variant_b_job"
		winning_job_name = self.get(winning_job_field)
		
		if not winning_job_name:
			frappe.throw(_("Winning variant job not found"))
		
		winning_job = frappe.get_doc("Job Opening", winning_job_name)
		
		# Create optimized job based on winner
		optimized_job = frappe.copy_doc(winning_job)
		optimized_job.job_title = f"{winning_job.job_title} (Optimized)"
		optimized_job.custom_ab_test_campaign = None
		optimized_job.custom_ab_test_variant = None
		optimized_job.insert()
		
		frappe.msgprint(_(f"Optimized job created: {optimized_job.name}"))
		
		return optimized_job.name
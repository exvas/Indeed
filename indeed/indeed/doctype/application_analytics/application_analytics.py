import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_days, date_diff
import json


class ApplicationAnalytics(Document):
	"""Application Analytics for Indeed Integration"""
	
	def onload(self):
		"""Load analytics data when document opens"""
		self.load_analytics_data()
	
	def load_analytics_data(self):
		"""Load comprehensive analytics data"""
		
		# Set default dates if not provided
		if not self.from_date:
			self.from_date = add_days(now_datetime(), -30)
		if not self.to_date:
			self.to_date = now_datetime()
		
		# Load all metrics
		self.load_application_metrics()
		self.load_source_analysis()
		self.load_job_performance()
		self.load_trend_analysis()
		self.generate_recommendations()
		
		# Generate main dashboard HTML
		self.analytics_html = self.generate_analytics_dashboard()
	
	def load_application_metrics(self):
		"""Load key application metrics"""
		
		# Build base filters
		filters = {
			"creation": ["between", [self.from_date, self.to_date]]
		}
		
		if self.company_filter:
			# Get jobs for this company and filter by them
			company_jobs = frappe.get_all(
				"Job Opening", 
				filters={"company": self.company_filter},
				pluck="name"
			)
			if company_jobs:
				filters["job_title"] = ["in", company_jobs]
			else:
				# No jobs for this company, set impossible filter
				filters["job_title"] = ["in", ["__no_jobs_found__"]]
		
		if self.job_filter:
			filters["job_title"] = self.job_filter
			
		if self.source_filter:
			filters["source"] = self.source_filter
		
		# Get application data
		applications = frappe.get_all(
			"Job Applicant",
			filters=filters,
			fields=["name", "source", "job_title", "creation"]
		)
		
		# Calculate basic metrics
		self.total_applications = len(applications)
		self.indeed_applications = len([a for a in applications if a.source == "Indeed"])
		
		# Conversion rate (Indeed apps / Total apps)
		if self.total_applications > 0:
			self.conversion_rate = (self.indeed_applications / self.total_applications) * 100
		else:
			self.conversion_rate = 0
		
		# Average time to apply (from job posting to application)
		self.calculate_avg_time_to_apply(applications)
	
	def calculate_avg_time_to_apply(self, applications):
		"""Calculate average time from job posting to application"""
		
		time_diffs = []
		
		for app in applications:
			if app.job_title and app.creation:
				# Get job opening creation date
				job_creation = frappe.db.get_value(
					"Job Opening", 
					app.job_title, 
					"creation"
				)
				
				if job_creation:
					days_diff = date_diff(app.creation, job_creation.date())
					if days_diff >= 0:  # Only positive differences
						time_diffs.append(days_diff)
		
		if time_diffs:
			self.avg_time_to_apply = sum(time_diffs) / len(time_diffs)
		else:
			self.avg_time_to_apply = 0
	
	def load_source_analysis(self):
		"""Analyze application sources"""
		
		# Build filter conditions
		conditions = ["creation BETWEEN %s AND %s"]
		params = [self.from_date, self.to_date]
		
		if self.company_filter:
			conditions.append(f"job_title IN (SELECT name FROM `tabJob Opening` WHERE company = '{self.company_filter}')")
		
		if self.job_filter:
			conditions.append(f"job_title = '{self.job_filter}'")
		
		source_data = frappe.db.sql(f"""
			SELECT 
				COALESCE(source, 'Unknown') as source,
				COUNT(*) as applications,
				COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
			FROM `tabJob Applicant`
			WHERE {' AND '.join(conditions)}
			GROUP BY source
			ORDER BY applications DESC
		""", params, as_dict=True)
		
		# Format source breakdown
		breakdown = []
		for row in source_data:
			breakdown.append(f"{row.source}: {row.applications} applications ({row.percentage:.1f}%)")
		
		self.source_breakdown = "\n".join(breakdown)
	
	def load_job_performance(self):
		"""Analyze job posting performance"""
		
		# Build job performance filter conditions
		job_conditions = ["jo.creation BETWEEN %s AND %s"]
		job_params = [self.from_date, self.to_date, self.from_date, self.to_date]
		
		if self.company_filter:
			job_conditions.append(f"jo.company = '{self.company_filter}'")
		
		if self.job_filter:
			job_conditions.append(f"jo.name = '{self.job_filter}'")
		
		job_performance = frappe.db.sql(f"""
			SELECT 
				jo.job_title,
				jo.name as job_id,
				COUNT(ja.name) as total_applications,
				COUNT(CASE WHEN ja.source = 'Indeed' THEN 1 END) as indeed_applications,
				jo.creation as job_posted_date
			FROM `tabJob Opening` jo
			LEFT JOIN `tabJob Applicant` ja ON ja.job_title = jo.name 
				AND ja.creation BETWEEN %s AND %s
			WHERE {' AND '.join(job_conditions)}
			GROUP BY jo.name, jo.job_title, jo.creation
			HAVING total_applications > 0
			ORDER BY total_applications DESC
			LIMIT 10
		""", job_params, as_dict=True)
		
		# Format job performance
		performance = []
		for job in job_performance:
			indeed_pct = (job.indeed_applications / job.total_applications * 100) if job.total_applications > 0 else 0
			performance.append(
				f"{job.job_title}: {job.total_applications} total apps "
				f"({job.indeed_applications} from Indeed - {indeed_pct:.1f}%)"
			)
		
		self.top_job_performance = "\n".join(performance)
	
	def load_trend_analysis(self):
		"""Analyze application trends over time"""
		
		# Build weekly trend filter conditions
		weekly_conditions = ["creation BETWEEN %s AND %s"]
		weekly_params = [self.from_date, self.to_date]
		
		if self.company_filter:
			weekly_conditions.append(f"job_title IN (SELECT name FROM `tabJob Opening` WHERE company = '{self.company_filter}')")
		
		if self.job_filter:
			weekly_conditions.append(f"job_title = '{self.job_filter}'")
		
		# Weekly trend analysis
		weekly_data = frappe.db.sql(f"""
			SELECT 
				YEARWEEK(creation) as week_year,
				DATE_SUB(creation, INTERVAL WEEKDAY(creation) DAY) as week_start,
				COUNT(*) as total_apps,
				COUNT(CASE WHEN source = 'Indeed' THEN 1 END) as indeed_apps
			FROM `tabJob Applicant`
			WHERE {' AND '.join(weekly_conditions)}
			GROUP BY YEARWEEK(creation), DATE_SUB(creation, INTERVAL WEEKDAY(creation) DAY)
			ORDER BY week_year
		""", weekly_params, as_dict=True)
		
		# Format trend analysis
		trends = []
		for week in weekly_data:
			indeed_pct = (week.indeed_apps / week.total_apps * 100) if week.total_apps > 0 else 0
			trends.append(
				f"Week of {week.week_start.strftime('%Y-%m-%d')}: {week.total_apps} total "
				f"({week.indeed_apps} Indeed - {indeed_pct:.1f}%)"
			)
		
		self.trend_analysis = "\n".join(trends) if trends else "No trend data available for selected period."
	
	def generate_recommendations(self):
		"""Generate actionable recommendations based on data"""
		
		recommendations = []
		
		# Indeed conversion rate recommendations
		if self.conversion_rate < 20:
			recommendations.append("🔍 Low Indeed conversion rate (<20%). Consider improving job descriptions or Indeed SEO.")
		elif self.conversion_rate > 50:
			recommendations.append("✅ Excellent Indeed performance (>50%). Consider increasing Indeed investment.")
		
		# Application volume recommendations
		if self.total_applications < 10:
			recommendations.append("📈 Low application volume. Consider expanding job posting channels.")
		
		# Time to apply recommendations
		if self.avg_time_to_apply > 14:
			recommendations.append("⏱️ Long time to apply (>14 days). Job posts may need better visibility or urgency.")
		elif self.avg_time_to_apply < 2:
			recommendations.append("🚀 Very fast applications (<2 days). Great job visibility and appeal!")
		
		# Add more recommendations based on source breakdown
		sources = self.source_breakdown.split('\n') if self.source_breakdown else []
		if len(sources) == 1:
			recommendations.append("🔄 Single source dependency. Consider diversifying application channels.")
		
		self.recommendations = "\n".join(recommendations) if recommendations else "Continue monitoring metrics for optimization opportunities."
	
	def generate_analytics_dashboard(self):
		"""Generate comprehensive analytics dashboard HTML"""
		
		html = f"""
		<div class="application-analytics">
			<style>
				.analytics-container {{
					font-family: Arial, sans-serif;
				}}
				.metric-grid {{
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
					gap: 15px;
					margin: 20px 0;
				}}
				.metric-card {{
					background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
					color: white;
					padding: 20px;
					border-radius: 10px;
					text-align: center;
				}}
				.metric-value {{
					font-size: 2.5em;
					font-weight: bold;
					margin-bottom: 5px;
				}}
				.metric-label {{
					font-size: 0.9em;
					opacity: 0.9;
				}}
				.chart-container {{
					background: #f8f9fa;
					border: 1px solid #dee2e6;
					border-radius: 8px;
					padding: 20px;
					margin: 20px 0;
				}}
				.recommendation-box {{
					background: #e7f3ff;
					border-left: 4px solid #007bff;
					padding: 15px;
					margin: 15px 0;
				}}
				.source-chart {{
					display: flex;
					flex-wrap: wrap;
					gap: 10px;
					margin: 15px 0;
				}}
				.source-bar {{
					background: #007bff;
					color: white;
					padding: 8px 12px;
					border-radius: 20px;
					font-size: 0.9em;
				}}
			</style>
			
			<h3>📊 Application Analytics Dashboard</h3>
			
			<div class="metric-grid">
				<div class="metric-card">
					<div class="metric-value">{self.total_applications}</div>
					<div class="metric-label">Total Applications</div>
				</div>
				
				<div class="metric-card">
					<div class="metric-value">{self.indeed_applications}</div>
					<div class="metric-label">Indeed Applications</div>
				</div>
				
				<div class="metric-card">
					<div class="metric-value">{self.conversion_rate:.1f}%</div>
					<div class="metric-label">Indeed Conversion Rate</div>
				</div>
				
				<div class="metric-card">
					<div class="metric-value">{self.avg_time_to_apply:.1f}</div>
					<div class="metric-label">Avg Days to Apply</div>
				</div>
			</div>
			
			<div class="chart-container">
				<h4>📈 Application Source Distribution</h4>
				<div class="source-chart">
					{self.generate_source_chart()}
				</div>
			</div>
			
			<div class="chart-container">
				<h4>🏆 Top Performing Jobs</h4>
				<div style="font-family: monospace; font-size: 0.9em; line-height: 1.6;">
					{self.top_job_performance.replace(chr(10), '<br>') if self.top_job_performance else 'No job performance data available.'}
				</div>
			</div>
			
			<div class="recommendation-box">
				<h4>💡 Actionable Recommendations</h4>
				<div style="line-height: 1.6;">
					{self.recommendations.replace(chr(10), '<br>') if self.recommendations else 'No specific recommendations at this time.'}
				</div>
			</div>
			
			<div style="margin-top: 30px;">
				<button class="btn btn-primary" onclick="exportAnalytics()">📊 Export Report</button>
				<button class="btn btn-secondary" onclick="refreshData()">🔄 Refresh Data</button>
				<button class="btn btn-info" onclick="scheduleReport()">📅 Schedule Report</button>
			</div>
		</div>
		
		<script>
			function exportAnalytics() {{
				window.open('/api/method/indeed.indeed.analytics_api.export_analytics_report');
			}}
			
			function refreshData() {{
				cur_frm.reload_doc();
			}}
			
			function scheduleReport() {{
				frappe.msgprint('Report scheduling coming soon!');
			}}
		</script>
		"""
		
		return html
	
	def generate_source_chart(self):
		"""Generate visual source distribution"""
		
		if not self.source_breakdown:
			return "<p>No source data available.</p>"
		
		sources = self.source_breakdown.split('\n')
		chart_html = ""
		
		for source in sources:
			if ':' in source:
				parts = source.split(':')
				source_name = parts[0].strip()
				details = parts[1].strip()
				chart_html += f'<div class="source-bar">{source_name}: {details}</div>'
		
		return chart_html
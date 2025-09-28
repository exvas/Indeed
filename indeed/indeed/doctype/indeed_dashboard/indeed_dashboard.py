import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_days
import json


class IndeedDashboard(Document):
	"""Indeed Integration Dashboard for monitoring job sync status"""
	
	def onload(self):
		"""Load dashboard data when document is opened"""
		self.load_dashboard_data()
	
	def load_dashboard_data(self):
		"""Load all dashboard metrics and charts"""
		
		# Set default dates if not provided
		if not self.from_date:
			self.from_date = add_days(now_datetime(), -30)
		if not self.to_date:
			self.to_date = now_datetime()
		
		# Load metrics
		self.load_metrics()
		
		# Generate dashboard HTML
		self.sync_status_html = self.generate_dashboard_html()
	
	def load_metrics(self):
		"""Load key integration metrics"""
		
		# Build filters
		filters = {
			"creation": ["between", [self.from_date, self.to_date]]
		}
		
		if self.company_filter:
			filters["company"] = self.company_filter
		
		if self.status_filter:
			filters["status"] = self.status_filter
		
		# Get job integration data
		job_integrations = frappe.get_all(
			"Indeed Job Integration",
			filters=filters,
			fields=["status", "creation", "posted_date", "error_message"]
		)
		
		# Calculate metrics
		self.total_jobs = len(job_integrations)
		self.successful_posts = len([j for j in job_integrations if j.status == "Posted"])
		self.failed_posts = len([j for j in job_integrations if j.status == "Failed"])
		self.pending_jobs = len([j for j in job_integrations if j.status == "Pending"])
		self.active_jobs = len([j for j in job_integrations if j.status in ["Posted", "Active"]])
		
		# Success rate
		if self.total_jobs > 0:
			self.success_rate = (self.successful_posts / self.total_jobs) * 100
		else:
			self.success_rate = 0
		
		# Average processing time (hours between creation and posting)
		processing_times = []
		for job in job_integrations:
			if job.posted_date and job.creation:
				time_diff = get_datetime(job.posted_date) - get_datetime(job.creation)
				processing_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
		
		if processing_times:
			self.avg_response_time = sum(processing_times) / len(processing_times)
		else:
			self.avg_response_time = 0
		
		# Last sync time
		last_integration = frappe.db.get_value(
			"Indeed Job Integration",
			filters={"status": "Posted"},
			fieldname="creation",
			order_by="creation desc"
		)
		self.last_sync_time = last_integration
	
	def generate_dashboard_html(self):
		"""Generate HTML for dashboard visualization"""
		
		html = f"""
		<div class="indeed-dashboard">
			<style>
				.indeed-dashboard {{
					font-family: Arial, sans-serif;
				}}
				.metric-card {{
					background: #f8f9fa;
					border: 1px solid #dee2e6;
					border-radius: 8px;
					padding: 20px;
					margin: 10px;
					text-align: center;
					display: inline-block;
					width: 200px;
					vertical-align: top;
				}}
				.metric-value {{
					font-size: 2em;
					font-weight: bold;
					color: #007bff;
				}}
				.metric-label {{
					font-size: 0.9em;
					color: #6c757d;
					margin-top: 5px;
				}}
				.status-chart {{
					margin: 20px 0;
					padding: 20px;
					border: 1px solid #dee2e6;
					border-radius: 8px;
				}}
				.success {{ color: #28a745; }}
				.failed {{ color: #dc3545; }}
				.pending {{ color: #ffc107; }}
			</style>
			
			<h3>Indeed Integration Health Overview</h3>
			
			<div class="metric-cards">
				<div class="metric-card">
					<div class="metric-value success">{self.successful_posts}</div>
					<div class="metric-label">Successful Posts</div>
				</div>
				
				<div class="metric-card">
					<div class="metric-value failed">{self.failed_posts}</div>
					<div class="metric-label">Failed Posts</div>
				</div>
				
				<div class="metric-card">
					<div class="metric-value pending">{self.pending_jobs}</div>
					<div class="metric-label">Pending Jobs</div>
				</div>
				
				<div class="metric-card">
					<div class="metric-value">{self.success_rate:.1f}%</div>
					<div class="metric-label">Success Rate</div>
				</div>
			</div>
			
			<div class="status-chart">
				<h4>Recent Integration Activity</h4>
				{self.generate_activity_chart()}
			</div>
			
			<div class="status-chart">
				<h4>Quick Actions</h4>
				<button class="btn btn-primary" onclick="regenerateXMLFeed()">Regenerate XML Feed</button>
				<button class="btn btn-secondary" onclick="viewFailedJobs()">View Failed Jobs</button>
				<button class="btn btn-info" onclick="downloadReport()">Download Report</button>
			</div>
		</div>
		
		<script>
			function regenerateXMLFeed() {{
				frappe.call({{
					method: 'indeed.indeed.utils.regenerate_xml_feed',
					callback: function(r) {{
						if (r.message.success) {{
							frappe.show_alert({{message: 'XML Feed regenerated successfully!', indicator: 'green'}});
						}}
					}}
				}});
			}}
			
			function viewFailedJobs() {{
				frappe.set_route('List', 'Indeed Job Integration', {{'status': 'Failed'}});
			}}
			
			function downloadReport() {{
				window.open('/api/method/indeed.indeed.dashboard_api.export_integration_report');
			}}
		</script>
		"""
		
		return html
	
	def generate_activity_chart(self):
		"""Generate activity timeline chart"""
		
		# Get recent activity (last 7 days)
		from_date = add_days(now_datetime(), -7)
		
		activity_data = frappe.db.sql("""
			SELECT 
				DATE(creation) as date,
				status,
				COUNT(*) as count
			FROM `tabIndeed Job Integration`
			WHERE creation >= %s
			GROUP BY DATE(creation), status
			ORDER BY date DESC
		""", [from_date], as_dict=True)
		
		if not activity_data:
			return "<p>No recent activity found.</p>"
		
		# Group by date
		dates = {}
		for row in activity_data:
			date = row.date.strftime("%Y-%m-%d")
			if date not in dates:
				dates[date] = {"Posted": 0, "Failed": 0, "Pending": 0}
			dates[date][row.status] = row.count
		
		# Generate chart HTML
		chart_html = """
		<table class="table table-striped">
			<thead>
				<tr>
					<th>Date</th>
					<th class="success">Posted</th>
					<th class="failed">Failed</th>
					<th class="pending">Pending</th>
				</tr>
			</thead>
			<tbody>
		"""
		
		for date, counts in sorted(dates.items(), reverse=True):
			chart_html += f"""
				<tr>
					<td>{date}</td>
					<td class="success">{counts.get('Posted', 0)}</td>
					<td class="failed">{counts.get('Failed', 0)}</td>
					<td class="pending">{counts.get('Pending', 0)}</td>
				</tr>
			"""
		
		chart_html += "</tbody></table>"
		return chart_html
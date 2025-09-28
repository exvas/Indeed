import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_days
import json


class BulkJobManager(Document):
	"""Bulk Job Management Tool for Indeed Integration"""
	
	def onload(self):
		"""Load matching jobs when document opens"""
		self.load_matching_jobs()
	
	def load_matching_jobs(self):
		"""Load jobs matching the selection criteria"""
		
		# Build filters based on user selection
		filters = {}
		
		if self.company_filter:
			filters["company"] = self.company_filter
		
		if self.department_filter:
			filters["department"] = self.department_filter
		
		if self.job_status_filter:
			filters["status"] = self.job_status_filter
			
		if self.from_date and self.to_date:
			filters["creation"] = ["between", [self.from_date, self.to_date]]
		elif self.from_date:
			filters["creation"] = [">=", self.from_date]
		elif self.to_date:
			filters["creation"] = ["<=", self.to_date]
		
		# Get matching job openings
		jobs = frappe.get_all(
			"Job Opening",
			filters=filters,
			fields=[
				"name", "job_title", "company", "department", "status", 
				"creation", "custom_post_to_indeed"
			],
			limit=100  # Limit for performance
		)
		
		# Generate HTML table for job selection
		self.selected_jobs_html = self.generate_job_selection_html(jobs)
	
	def generate_job_selection_html(self, jobs):
		"""Generate HTML for job selection interface"""
		
		if not jobs:
			return "<p>No jobs found matching the criteria.</p>"
		
		html = f"""
		<div class="bulk-job-manager">
			<style>
				.job-table {{
					width: 100%;
					border-collapse: collapse;
					margin: 10px 0;
				}}
				.job-table th, .job-table td {{
					border: 1px solid #ddd;
					padding: 8px;
					text-align: left;
				}}
				.job-table th {{
					background-color: #f2f2f2;
				}}
				.job-checkbox {{
					margin-right: 5px;
				}}
				.indeed-status {{
					padding: 2px 6px;
					border-radius: 3px;
					font-size: 11px;
				}}
				.indeed-enabled {{ background: #d4edda; color: #155724; }}
				.indeed-disabled {{ background: #f8d7da; color: #721c24; }}
			</style>
			
			<p><strong>Found {len(jobs)} jobs matching criteria</strong></p>
			
			<table class="job-table">
				<thead>
					<tr>
						<th><input type="checkbox" id="select-all-jobs" onchange="toggleAllJobs()"> Select</th>
						<th>Job Title</th>
						<th>Company</th>
						<th>Department</th>
						<th>Status</th>
						<th>Indeed Status</th>
						<th>Created</th>
					</tr>
				</thead>
				<tbody>
		"""
		
		for job in jobs:
			indeed_status = "Enabled" if job.custom_post_to_indeed else "Disabled"
			indeed_class = "indeed-enabled" if job.custom_post_to_indeed else "indeed-disabled"
			
			html += f"""
				<tr>
					<td>
						<input type="checkbox" class="job-checkbox" 
							   value="{job.name}" name="selected_job">
					</td>
					<td><a href="/app/job-opening/{job.name}" target="_blank">{job.job_title}</a></td>
					<td>{job.company or ''}</td>
					<td>{job.department or ''}</td>
					<td>{job.status}</td>
					<td><span class="indeed-status {indeed_class}">{indeed_status}</span></td>
					<td>{job.creation.strftime('%Y-%m-%d') if job.creation else ''}</td>
				</tr>
			"""
		
		html += """
				</tbody>
			</table>
			
			<div style="margin-top: 20px;">
				<button class="btn btn-primary" onclick="executeSelectedOperation()">
					Execute Operation on Selected Jobs
				</button>
				<span id="selected-count" style="margin-left: 10px; color: #666;">
					0 jobs selected
				</span>
			</div>
		</div>
		
		<script>
			function toggleAllJobs() {
				var selectAll = document.getElementById('select-all-jobs');
				var checkboxes = document.getElementsByClassName('job-checkbox');
				
				for (var i = 0; i < checkboxes.length; i++) {
					checkboxes[i].checked = selectAll.checked;
				}
				updateSelectedCount();
			}
			
			function updateSelectedCount() {
				var checkboxes = document.getElementsByClassName('job-checkbox');
				var selectedCount = 0;
				
				for (var i = 0; i < checkboxes.length; i++) {
					if (checkboxes[i].checked) {
						selectedCount++;
					}
				}
				
				document.getElementById('selected-count').textContent = selectedCount + ' jobs selected';
			}
			
			// Add event listeners to individual checkboxes
			document.addEventListener('change', function(e) {
				if (e.target.classList.contains('job-checkbox')) {
					updateSelectedCount();
				}
			});
			
			function executeSelectedOperation() {
				var selectedJobs = [];
				var checkboxes = document.getElementsByClassName('job-checkbox');
				
				for (var i = 0; i < checkboxes.length; i++) {
					if (checkboxes[i].checked) {
						selectedJobs.push(checkboxes[i].value);
					}
				}
				
				if (selectedJobs.length === 0) {
					frappe.msgprint('Please select at least one job to perform bulk operation.');
					return;
				}
				
				// Call server method to execute bulk operation
				frappe.call({
					method: 'indeed.indeed.bulk_operations.execute_bulk_operation',
					args: {
						job_names: selectedJobs,
						operation: cur_frm.doc.bulk_action,
						new_status: cur_frm.doc.new_status,
						indeed_action: cur_frm.doc.indeed_action
					},
					callback: function(r) {
						if (r.message) {
							cur_frm.set_value('operation_results', r.message.results);
							cur_frm.refresh_field('operation_results');
							frappe.show_alert({
								message: r.message.summary,
								indicator: r.message.success ? 'green' : 'red'
							});
						}
					}
				});
			}
		</script>
		"""
		
		return html
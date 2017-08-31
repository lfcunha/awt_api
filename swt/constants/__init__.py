DIGS_TERMINAL_REQUEST_STATUSES = '"completed", "failed-samples not received", "failed-sample qc", "failed-sequencing/assembly", "declined"'

EXTRACT_EMAIL_FACILITY_SUBJECT = 'New DIGS Sequencing Request Assigned to Your Facility'
EXTRACT_EMAIL_FACILITY_BODY = """Dear DIGS Manager,<br><br>
The DPCC has provisionally assigned a new sequencing request to your facility (request ID {}, attached).
The requester is waiting for confirmation that you accept the request before shipping the samples.
Please confirm with the requester at your earliest convenience:<br>
&nbsp;&nbsp;&nbsp;&nbsp;Name: {}<br>&nbsp;&nbsp;&nbsp;&nbsp;Address: {}<br>
&nbsp;&nbsp;&nbsp;&nbsp;Phone: {}<br>&nbsp;&nbsp;&nbsp;&nbsp;Email: {}<br><br>
If you accept the request, please go to SWT and change the status of the samples to Accepted.<br>{}{}"""
EXTRACT_EMAIL_REQUESTER_SUBJECT = 'Receipt for your DIGS Sequencing Request'
EXTRACT_EMAIL_REQUESTER_BODY = """Dear {},<br><br>
The DPCC has received your sequencing request with ID R{}.
You can download another copy of your shipping manifest <a href = '{}'>here</a>.<br>
Your request has been provisionally assigned to the {} DIGS facility.
A representative from {} will confirm with you directly that they can perform the work.
Please wait for their confirmation before shipping the samples.<br><br>
You can follow the status of your request by selecting “Check the status of EXISTING REQUESTS” on the SWT main page.<br>
{}{}"""
EXTRACT_EMAIL_SIGNATURE = """<br>Thank you for using the DIGS service,<br>
The CEIRS DPCC Team<br><br>
For technical support, submit a support request <a href='https://dpcc.niaidceirs.org/ometa/support.action'>online</a><br>
Or contact us:<br>
&nbsp;&nbsp;&nbsp;&nbsp;By Phone: 1-855-846-2697<br>
&nbsp;&nbsp;&nbsp;&nbsp;By Email: support@niaidceirs.org<br>
"""
# 2. User Story

## 2.1 User Management

A user will sign up to access the platform by providing their name,
email and password. The password will be at least 6 characters long. If
the email exists, the user is informed that the email is already
registered and they are prompted to log in instead. If the email does
not exist, the user is registered successfully. The user can log in into
the system after registration providing their email and password. After
the credentials are validated the user is redirected to their dashboard.
The user can choose to reset the password by providing their email. An
OTP is sent to the validated email. The user can reset their password
ensuring the new password meets the required criteria.

## 2.2 Job Post Management

A company user can post a job with: Job title, Job description, Required
skills, Experience level, Salary range and Location. If the inputs are
valid (e.g., all required fields are filled) the job post becomes
visible to job seekers in the search results. A company can view a list
of all their job posts in the dashboard. They can edit job details
(e.g., update the salary or description), delete outdated job posts. Job
seekers can use filters like location, skills, and salary to narrow down
the results and apply if interested.

## 2.3 Job Application Management

A job seeker can apply for a job by uploading their resume (PDF or Word
format). Once submitted, the application details (resume and applicant
info) are sent to the company's email. The job seeker can view a list of
jobs they've applied to, check the status of each application (e.g.,
Pending, Reviewed, Shortlisted, Rejected) and withdraw an application if
needed.

Companies can view all applicants for a specific job post in their
dashboard. For each applicant, the system displays the applicant's
profile (skills, experience, location) and uploaded resume. Companies
can filter applicants based on skills or experience and update
application statuses (e.g., Shortlisted, Rejected).

## 2.4 Recommendation

Job seekers are recommended job posts that match with their skills. The
user can click on a recommended job post to view details or apply
directly. If a user updates their profile (e.g., adds new skills or
changes salary expectations), the recommendations are refreshed to show
the updated preferences.

## 2.5 Chat Management

A Company can initiate a chat or conversation with an applicant to
discuss job roles, share details about openings, or clarify any queries
related to the hiring process.

Users can exchange real-time messages. They can also manage their chat
history and share files with each other.

## 2.6 Hiring Management

A company can view and manage job applications, update their status to
"Hired" or "Rejected," and input offer letter details for hired
candidates. After confirmation, the system sends the offer letter to the
selected applicant through email.

A job seeker can track the status of their applications (e.g., Pending,
Rejected, Hired). If hired, they can view the offer letter and accept or
reject it. They can also download the offer letter sent by the company.

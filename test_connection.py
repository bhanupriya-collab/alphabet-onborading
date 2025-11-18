from root_agent.tools.utils.gmail_client import GmailAPIClient
# from root_agent.tools.welcome_mail import welcome_mail

client = GmailAPIClient()  # Uses hard-coded client_id/client_secret in the file
print(client.test_connection())  # Optional sanity check

html_body = "<p>this is a test.</p>"
result = client.send_email(
    to="bhangupta@deloitte.com",
    subject="Test Email",
    body=html_body
)

# # result = welcome_mail(
# #     Candidate_name="Test User",
# #     Joining_Date="N/A",
# #     HR_Poc="HR Team",
# #     candidateEmailID="bhangupta@deloitte.com"
# # )


# result = welcome_mail("Bhanu", "UK", "bhangupta@deloitte.com")
print(result)
import os
from google.adk.agents import Agent
from google.adk.tools import VertexAiSearchTool, agent_tool
from dotenv import load_dotenv
from .prompts.prompts import ROOT_AGENT_PROMPT
from .tools.welcome_mail import welcome_mail
from .tools.bulk_welcome import tracker_welcome_emails
from .tools.action_required_mail import batch_action_required_emails, send_action_required_mail
from .tools.password_setup_reminder import batch_password_setup_reminders, send_password_setup_reminder
from .tools.compliance_reminder import batch_compliance_reminders, send_compliance_reminder
load_dotenv()
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")
MODEL_PRO = os.environ.get("MODEL_PRO", "gemini-2.5-pro")
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

root_agent = Agent(
    name='root_agent',
    # model = MODEL_PRO,
    model = MODEL,
    instruction=ROOT_AGENT_PROMPT, 
    description="The agent streamlines and automates the process of sending personalized emails to new employees during their preboarding and onboarding journey",
    tools=[welcome_mail, 
           tracker_welcome_emails, 
           batch_action_required_emails, 
           send_action_required_mail,
           batch_password_setup_reminders,
           send_password_setup_reminder,
           batch_compliance_reminders,
           send_compliance_reminder,]
)
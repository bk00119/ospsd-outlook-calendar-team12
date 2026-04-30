"""Run the Slack polling loop for the calendar assistant."""

from outlook_client_service.slack_poller import run_slack_poller

if __name__ == "__main__":
    run_slack_poller()

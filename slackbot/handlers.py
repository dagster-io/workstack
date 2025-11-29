"""Slack command handlers for Erk integration."""

from slack_bolt.async_app import AsyncApp

from slackbot.erk_service import ErkService


def register_handlers(app: AsyncApp, erk: ErkService) -> None:
    """Register slash command handlers with the Slack app.

    Args:
        app: Slack Bolt AsyncApp instance
        erk: ErkService instance for Erk operations
    """

    @app.command("/erk-plan")
    async def handle_plan(ack, command, respond) -> None:  # type: ignore[no-untyped-def]
        """Handle /erk-plan command to create a plan from the message text.

        Usage: /erk-plan <plan content>
        """
        await ack()

        text = command.get("text", "").strip()
        if not text:
            await respond(
                "Please provide plan content.\n\n"
                "Usage: `/erk-plan <plan content>`\n\n"
                "Example:\n```\n/erk-plan # My Feature\n\n"
                "## Goal\nImplement a new feature\n\n"
                "## Steps\n1. Do this\n2. Do that\n```"
            )
            return

        try:
            result = erk.create_plan(text)
            await respond(
                f"Plan created successfully!\n\n"
                f"*Issue:* <{result.url}|#{result.issue_number}>\n"
                f"*Title:* {result.title}\n\n"
                f"Next steps:\n"
                f"- View: `erk get {result.issue_number}`\n"
                f"- Implement: `erk implement {result.issue_number}`\n"
                f"- Submit: `/erk-submit {result.issue_number}`"
            )
        except ValueError as e:
            await respond(f"Failed to create plan: {e}")
        except RuntimeError as e:
            await respond(f"Error communicating with GitHub: {e}")

    @app.command("/erk-submit")
    async def handle_submit(ack, command, respond) -> None:  # type: ignore[no-untyped-def]
        """Handle /erk-submit command to submit a plan to the queue.

        Usage: /erk-submit <issue_number>
        """
        await ack()

        text = command.get("text", "").strip()
        if not text:
            await respond(
                "Please provide an issue number.\n\n"
                "Usage: `/erk-submit <issue_number>`\n\n"
                "Example: `/erk-submit 123`"
            )
            return

        # Parse issue number
        if not text.isdigit():
            await respond(f"Invalid issue number: `{text}`\n\nPlease provide a valid number.")
            return

        issue_number = int(text)

        # Get submitter from Slack user info
        user_id = command.get("user_id", "unknown")
        user_name = command.get("user_name", user_id)

        try:
            result = erk.submit_to_queue(issue_number, submitted_by=user_name)
            await respond(
                f"Plan #{issue_number} submitted to queue!\n\n"
                f"*Workflow run:* <{result.workflow_url}|View run>\n\n"
                f"The implementation will start shortly."
            )
        except ValueError as e:
            await respond(f"Failed to submit plan: {e}")
        except RuntimeError as e:
            await respond(f"Error communicating with GitHub: {e}")

    @app.command("/erk-plans")
    async def handle_plans(ack, respond) -> None:  # type: ignore[no-untyped-def]
        """Handle /erk-plans command to list open plans.

        Usage: /erk-plans
        """
        await ack()

        try:
            plans = erk.list_plans(limit=20)

            if not plans:
                await respond("No open plans found.")
                return

            lines = ["*Open Plans:*\n"]
            for plan in plans:
                # Format created_at as relative time
                lines.append(f"- <{plan.url}|#{plan.number}>: {plan.title}")

            await respond("\n".join(lines))
        except RuntimeError as e:
            await respond(f"Error fetching plans: {e}")

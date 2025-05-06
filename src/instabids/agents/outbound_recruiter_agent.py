"""
OutboundRecruiterAgent – ensures each bid-card gets >= MIN_BIDS by
1) pinging in-platform contractors
2) emailing / texting prospect contractors
3) (optional) using Grasp to post to web lead-forms

Runs periodically (e.g., via a CRON job or scheduled function).
"""
from __future__ import annotations
import os
import logging
import random
import datetime as dt
from typing import List, Dict, Any, Optional, Set

# Assuming these imports are valid relative to the project structure
try:
    from instabids.data.supabase_client import create_client
    _sb = create_client()
except ImportError:
    logging.critical("Failed to import or initialize Supabase client.")
    _sb = None # type: ignore

try:
    from instabids.tools.twilio_sms_tool import send_sms
except ImportError:
    logging.error("Twilio SMS tool not found. SMS sending will fail.")
    def send_sms(to: str, body: str) -> Dict[str, Any]:
        log.error("STUB: Twilio send_sms called but tool not available.")
        return {"sid": "stub-sms-error", "status": "failed"}

try:
    from instabids.tools.sendgrid_email_tool import send_email
except ImportError:
    logging.error("SendGrid email tool not found. Email sending will fail.")
    def send_email(to: str, subject: str, html: str) -> str:
        log.error("STUB: SendGrid send_email called but tool not available.")
        return "sg:error"

# Optional Grasp tool - not used yet
# try:
#     from instabids.tools.grasp_scraper_tool import post_to_lead_form
# except ImportError:
#     logging.info("Grasp scraper tool not found. Lead form posting disabled.")
#     def post_to_lead_form(*args, **kwargs): return False


log = logging.getLogger(__name__)
if not log.handlers:
     # Basic config if running standalone or if root logger not configured
     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Constants ---
_MIN_BIDS = int(os.getenv("MIN_BIDS_PER_CARD", 3))
_MAX_ATTEMPTS = int(os.getenv("MAX_INVITE_ATTEMPTS", 3))
# How far back to look for bid cards needing attention (e.g., created in last 7 days)
_LOOKBACK_DAYS = int(os.getenv("OUTBOUND_LOOKBACK_DAYS", 7))
_APP_URL = os.getenv("APP_URL", "https://app.instabids.com") # Default URL

class OutboundRecruiterAgent:
    def __init__(self) -> None:
        self.now = dt.datetime.now(dt.timezone.utc)
        if not _sb:
            raise RuntimeError("Supabase client is not initialized. Agent cannot function.")

    # ---------- public entry point -----------------
    def run_cycle(self) -> Dict[str, int]:
        """
        Runs one cycle of the outbound recruiting process.
        Fetches bid cards needing bids, selects targets, and dispatches invites.

        Returns:
            A dictionary summarizing the actions taken, e.g.,
            {'processed_cards': 5, 'invites_sent': 12, 'errors': 0}
        """
        processed_count = 0
        sent_count = 0
        error_count = 0
        log.info(f"Starting OutboundRecruiterAgent cycle at {self.now.isoformat()}")

        bid_cards_to_process = self._bid_cards_needing_bids()
        log.info(f"Found {len(bid_cards_to_process)} bid cards needing attention.")

        for card in bid_cards_to_process:
            processed_count += 1
            bid_card_id = card.get("id")
            project_id = card.get("project_id") # Needed for match_contractors RPC
            job_type = card.get("job_type", card.get("category", "work")) # For message content

            if not bid_card_id or not project_id:
                log.error(f"Skipping card due to missing id or project_id: {card}")
                error_count += 1
                continue

            try:
                log.debug(f"Processing bid card: {bid_card_id}")
                # Count active invites (queued, sent, responded)
                # Assumes 'opted_out' means don't retry, 'failed' means maybe retry later (handled implicitly by _MAX_ATTEMPTS logic)
                active_invites = self._get_active_invite_count(bid_card_id)
                needed = _MIN_BIDS - active_invites

                if needed <= 0:
                    log.debug(f"Bid card {bid_card_id} already has {active_invites} >= {_MIN_BIDS} active invites. Skipping.")
                    continue

                log.info(f"Bid card {bid_card_id} needs {needed} more invites (has {active_invites}).")

                # Get IDs of contractors/prospects already invited (any status) to avoid re-inviting immediately
                invited_target_ids = self._get_invited_target_ids(bid_card_id)

                # Select new targets
                targets = self._select_targets(card, needed, invited_target_ids)
                log.info(f"Selected {len(targets)} new targets for bid card {bid_card_id}.")

                # Dispatch invites to new targets
                dispatched_count = self._dispatch_invites(card, targets)
                sent_count += dispatched_count

            except Exception as e:
                log.exception(f"Error processing bid card {bid_card_id}:", exc_info=e)
                error_count += 1
                # Continue to next card

        summary = {
            'processed_cards': processed_count,
            'invites_sent': sent_count,
            'errors': error_count
        }
        log.info(f"OutboundRecruiterAgent cycle finished. Summary: {summary}")
        return summary

    # ---------- Database Interaction Helpers -----------------

    def _bid_cards_needing_bids(self) -> List[Dict[str, Any]]:
        """
        Fetches bid cards created recently that might need more bids.
        Relies on a Supabase RPC or view optimized for this query.
        """
        try:
            # Assumes RPC 'bidcards_needing_bids_v2' exists and returns relevant cards
            # It should filter by creation date, status, and potentially current bid count
            lookback_date = self.now - dt.timedelta(days=_LOOKBACK_DAYS)
            log.debug(f"Fetching bid cards created since {lookback_date.isoformat()} needing bids.")
            # Placeholder: Replace with actual RPC call if available
            # For now, fetch recent cards and filter minimally in Python (less efficient)
            res = _sb.table("bid_cards")\
                     .select("id, project_id, category, job_type, created_at")\
                     .gte("created_at", lookback_date.isoformat())\
                     .in_("status", ["active", "open"]) # Example statuses
                     .order("created_at", desc=True)\
                     .limit(100) # Limit query size
                     .execute()

            if hasattr(res, 'error') and res.error:
                log.error(f"Error fetching bid cards: {res.error}")
                return []
            log.info(f"Fetched {len(res.data)} candidate bid cards.")
            return res.data or []
        except Exception as e:
            log.exception("Exception fetching bid cards:", exc_info=e)
            return []

    def _get_active_invite_count(self, bid_card_id: str) -> int:
        """Counts invites for a bid card that are not in a terminal 'failed' or 'opted_out' state."""
        try:
            res = _sb.table("contractor_invites")\
                     .select("id", count='exact')\
                     .eq("bid_card_id", bid_card_id)\
                     .in_("status", ["queued", "sent", "responded"]) # Active statuses
                     .execute()
            # Check if the response has the 'count' attribute
            count = getattr(res, 'count', None)
            error = getattr(res, 'error', None)
            if error:
                log.error(f"Error counting active invites for {bid_card_id}: {error}")
                return 0 # Assume zero if count fails
            return count or 0
        except Exception as e:
            log.exception(f"Exception counting active invites for {bid_card_id}:", exc_info=e)
            return 0

    def _get_invited_target_ids(self, bid_card_id: str) -> Set[str]:
        """Gets the set of contractor_id or prospect_id already invited for this bid."""
        invited_ids: Set[str] = set()
        try:
            res = _sb.table("contractor_invites")\
                     .select("contractor_id, prospect_id")\
                     .eq("bid_card_id", bid_card_id)\
                     .execute()
            if hasattr(res, 'error') and res.error:
                log.error(f"Error fetching invited targets for {bid_card_id}: {res.error}")
                return invited_ids # Return empty set on error

            for row in res.data or []:
                if row.get("contractor_id"):
                    invited_ids.add(row["contractor_id"])
                elif row.get("prospect_id"):
                    invited_ids.add(row["prospect_id"])
            log.debug(f"Found {len(invited_ids)} previously invited targets for {bid_card_id}.")
            return invited_ids
        except Exception as e:
            log.exception(f"Exception fetching invited targets for {bid_card_id}:", exc_info=e)
            return invited_ids # Return empty set on error

    def _select_targets(self, card: Dict[str, Any], n: int, invited_target_ids: Set[str]) -> List[Dict[str, Any]]:
        """
        Selects up to 'n' new targets (contractors or prospects) for a bid card,
        excluding those already invited.
        """
        targets: List[Dict[str, Any]] = []
        bid_card_id = card["id"]
        project_id = card["project_id"]
        category = card.get("category")

        # 1. Try finding matched in-platform contractors first
        try:
            log.debug(f"Calling match_contractors RPC for project {project_id}")
            # Assumes match_contractors returns list like [{'contractor_id': UUID, 'match_score': float, ...}]
            # It needs the *project_id* associated with the bid_card
            match_res = _sb.rpc("match_contractors", { "p_project": project_id }).execute()
            if hasattr(match_res, 'error') and match_res.error:
                log.error(f"Error calling match_contractors RPC for project {project_id}: {match_res.error}")
            else:
                potential_matches = match_res.data or []
                log.debug(f"RPC returned {len(potential_matches)} potential matches.")
                # Filter out already invited and take top N needed
                for match in potential_matches:
                    contractor_id = match.get("contractor_id") # The RPC returns contractor_id
                    if contractor_id and contractor_id not in invited_target_ids:
                        # Fetch contractor profile details needed for outreach (e.g., preferred channel)
                        # Placeholder: Assume match dict contains enough info or fetch separately
                        match['target_type'] = 'contractor' # Add type for dispatch logic
                        targets.append(match)
                        if len(targets) >= n:
                            break
                log.info(f"Selected {len(targets)} in-platform contractors for {bid_card_id}.")

        except Exception as e:
            log.exception(f"Exception during contractor matching for {bid_card_id}:", exc_info=e)

        # 2. If still need more targets, look for prospects
        shortfall = n - len(targets)
        if shortfall <= 0:
            return targets

        log.info(f"Shortfall of {shortfall}. Looking for prospects for category '{category}'.")
        try:
            # Query prospects matching the category, excluding already invited
            prospect_query = _sb.table("prospect_contractors")\
                               .select("id, phone, email, business_name") # Select needed fields

            # Filter by category if available
            if category:
                prospect_query = prospect_query.contains("service_categories", [category])

            prospect_res = prospect_query.limit(shortfall * 5).execute() # Fetch more prospects than needed initially

            if hasattr(prospect_res, 'error') and prospect_res.error:
                log.error(f"Error fetching prospects for {bid_card_id}: {prospect_res.error}")
            else:
                potential_prospects = prospect_res.data or []
                log.debug(f"Found {len(potential_prospects)} potential prospects.")
                # Filter out already invited prospects and shuffle for variety
                eligible_prospects = [
                    p for p in potential_prospects
                    if p.get("id") and p.get("id") not in invited_target_ids and (p.get("phone") or p.get("email"))
                ]
                random.shuffle(eligible_prospects)

                added_prospects = 0
                for prospect in eligible_prospects:
                     if len(targets) < n:
                        prospect['target_type'] = 'prospect' # Add type
                        targets.append(prospect)
                        added_prospects +=1
                     else:
                        break
                log.info(f"Selected {added_prospects} prospects for {bid_card_id}.")

        except Exception as e:
            log.exception(f"Exception during prospect selection for {bid_card_id}:", exc_info=e)

        return targets

    def _dispatch_invites(self, card: Dict[str, Any], targets: List[Dict[str, Any]]) -> int:
        """Sends invites to selected targets via appropriate channels."""
        sent_count = 0
        bid_card_id = card["id"]
        job_type = card.get("job_type", card.get("category", "a new job")) # For message content
        join_url = f"{_APP_URL}/join?bid={bid_card_id}" # Example join URL

        for target in targets:
            target_type = target.get("target_type")
            invite_recorded = False
            try:
                if target_type == "contractor":
                    contractor_id = target.get("contractor_id")
                    if contractor_id:
                        log.info(f"Dispatching internal notification to contractor {contractor_id} for bid {bid_card_id}")
                        self._internal_notify(contractor_id, card)
                        # Record immediately as 'sent' for internal notifications
                        self._record_invite(bid_card_id, contractor_id=contractor_id,
                                            channel="internal", status="sent")
                        invite_recorded = True
                        sent_count += 1
                    else:
                         log.warning(f"Skipping contractor target due to missing contractor_id: {target}")

                elif target_type == "prospect":
                    prospect_id = target.get("id")
                    if not prospect_id:
                        log.warning(f"Skipping prospect target due to missing id: {target}")
                        continue

                    phone = target.get("phone")
                    email = target.get("email")
                    business_name = target.get("business_name", "Contractor")

                    invite_status = "queued" # Default to queued, update on successful send attempt
                    channel_used = None
                    response_payload = None

                    # Prefer SMS if phone number is available
                    if phone:
                        channel_used = "sms"
                        sms_body = (
                            f"Hi {business_name}, a homeowner near you needs {job_type}. "
                            f"Quote for free on InstaBids: {join_url}"
                        )
                        try:
                            log.info(f"Sending SMS to prospect {prospect_id} ({phone}) for bid {bid_card_id}")
                            sms_response = send_sms(to=phone, body=sms_body)
                            # Use status from Twilio if available, otherwise assume 'sent' if no error
                            invite_status = sms_response.get("status", "sent")
                            response_payload = sms_response
                            log.info(f"SMS send attempt result for prospect {prospect_id}: {invite_status}")
                            sent_count += 1
                        except Exception as sms_error:
                            log.error(f"Failed to send SMS to prospect {prospect_id} ({phone}): {sms_error}")
                            invite_status = "failed"
                            response_payload = {"error": str(sms_error)}

                    # Fallback to email if no phone or SMS failed (and email exists)
                    elif email:
                        channel_used = "email"
                        email_subject = f"Free Lead Opportunity: {job_type} in your area"
                        email_html = (
                            f"<p>Hi {business_name},</p>"
                            f"<p>A homeowner in your service area posted a job for {job_type} on InstaBids.</p>"
                            f"<p>You can view the details and submit a quote for free (no lead fees).</p>"
                            f"<p><a href='{join_url}'>Click here to view the job & join InstaBids</a></p>"
                            f"<p>Thanks,<br/>The InstaBids Team</p>"
                        )
                        try:
                            log.info(f"Sending email to prospect {prospect_id} ({email}) for bid {bid_card_id}")
                            email_ref = send_email(to=email, subject=email_subject, html=email_html)
                            # Assuming send_email returns 'sg:<code>' on success
                            if isinstance(email_ref, str) and email_ref.startswith("sg:2"): # Check for 2xx status
                                invite_status = "sent"
                                log.info(f"Email sent successfully to prospect {prospect_id}. Ref: {email_ref}")
                                sent_count += 1
                            else:
                                invite_status = "failed"
                                log.error(f"SendGrid indicated failure for prospect {prospect_id}. Ref: {email_ref}")
                            response_payload = {"ref": email_ref}
                        except Exception as email_error:
                            log.error(f"Failed to send email to prospect {prospect_id} ({email}): {email_error}")
                            invite_status = "failed"
                            response_payload = {"error": str(email_error)}
                    else:
                        log.warning(f"Prospect {prospect_id} has no phone or email. Cannot send invite.")
                        invite_status = "failed" # Mark as failed if no contact method
                        channel_used = "none"
                        response_payload = {"error": "No contact method available"}


                    # Record the prospect invite attempt
                    if channel_used and channel_used != "none":
                         self._record_invite(bid_card_id, prospect_id=prospect_id,
                                            channel=channel_used, status=invite_status, # type: ignore
                                            payload=response_payload)
                         invite_recorded = True
                    elif invite_status == "failed": # Record failure even if no channel used
                         self._record_invite(bid_card_id, prospect_id=prospect_id,
                                            channel="none", status="failed",
                                            payload=response_payload)
                         invite_recorded = True


                else:
                    log.warning(f"Unknown target type '{target_type}' for target: {target}")

            except Exception as dispatch_error:
                 log.exception(f"Error dispatching invite for target {target.get('id') or target.get('contractor_id')} "
                               f"and bid {bid_card_id}:", exc_info=dispatch_error)
                 # Optionally record a failure if an error occurred mid-dispatch before recording
                 if not invite_recorded and target_type == 'prospect' and target.get('id'):
                      self._record_invite(bid_card_id, prospect_id=target['id'], channel='error', status='failed',
                                          payload={'error': f'Dispatch exception: {dispatch_error}'})


        return sent_count


    # ---------- Internal Helpers -----------------------------

    def _internal_notify(self, contractor_id: str, card: Dict[str, Any]) -> None:
        """Sends an internal notification (e.g., A2A event) to a signed-up contractor."""
        # Placeholder - In a real system, this would likely publish to a message queue
        # or use the A2A communication mechanism.
        # For now, insert into a placeholder table or just log.
        event_payload = {
            "topic": "contractor.invite.new", # Example topic
            "recipient_user_id": contractor_id,
            "payload": {
                "bid_card_id": card.get("id"),
                "job_type": card.get("job_type", card.get("category")),
                # Add other relevant details: location hint, description snippet?
            },
            "created_at": self.now.isoformat()
        }
        log.info(f"INTERNAL_NOTIFY: Sending event: {event_payload}")
        # Example: Insert into a simple event table if one exists
        # try:
        #     _sb.table("internal_notifications").insert(event_payload).execute()
        # except Exception as e:
        #     log.error(f"Failed to record internal notification for {contractor_id}: {e}")


    def _record_invite(self, bid_card_id: str, *,
                       contractor_id: Optional[str] = None,
                       prospect_id: Optional[str] = None,
                       channel: str, status: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Records an invite attempt in the contractor_invites table."""
        if not bid_card_id or not (contractor_id or prospect_id):
            log.error("Cannot record invite: Missing bid_card_id or target ID (contractor/prospect).")
            return

        insert_data = {
            "bid_card_id": bid_card_id,
            "contractor_id": contractor_id,
            "prospect_id": prospect_id,
            "channel": channel,
            "status": status,
            "attempts": 1, # First attempt for this record
            "last_attempt_at": self.now.isoformat(), # Use ISO format for timestamp
            "response_payload": payload or {}
        }
        log.debug(f"Recording invite: {insert_data}")
        try:
            res = _sb.table("contractor_invites").insert(insert_data).execute()
            if hasattr(res, 'error') and res.error:
                log.error(f"Failed to record invite: {res.error}. Data: {insert_data}")
        except Exception as e:
            log.exception("Exception recording invite:", exc_info=e)


# --- Entry point for testing or manual execution ---
if __name__ == "__main__":
    print("Running OutboundRecruiterAgent cycle manually...")
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Ensure environment variables are set (TWILIO_*, SENDGRID_KEY, SUPABASE_URL, SUPABASE_KEY, APP_URL etc.)
    if not _sb:
         log.critical("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY.")
    else:
        agent = OutboundRecruiterAgent()
        run_summary = agent.run_cycle()
        print(f"Manual run finished. Summary: {run_summary}")

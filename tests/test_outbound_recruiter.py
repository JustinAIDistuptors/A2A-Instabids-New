import pytest
import datetime as dt
from unittest.mock import patch, MagicMock, call, ANY

# Module to test - adjust path if necessary
from instabids.agents.outbound_recruiter_agent import OutboundRecruiterAgent, _MIN_BIDS

# --- Test Fixtures & Mock Data ---

@pytest.fixture
def mock_supabase_client():
    """Provides a mocked Supabase client instance."""
    client = MagicMock()
    # Mock chainable methods used in the agent
    client.table.return_value.select.return_value.eq.return_value = client # for _get_invited_target_ids, _get_active_invite_count
    client.table.return_value.select.return_value.eq.return_value.in_.return_value = client # for _get_active_invite_count
    client.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[], count=0, error=None) # Default empty
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], count=0, error=None) # Default empty
    
    # Mock for _bid_cards_needing_bids (simplified)
    client.table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[], error=None)
    
    # Mock for prospect query
    client.table.return_value.select.return_value.contains.return_value.limit.return_value.execute.return_value = MagicMock(data=[], error=None)
    client.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[], error=None) # Prospect query without category
    
    # Mock for _record_invite
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(error=None)
    
    # Mock for RPC calls
    client.rpc.return_value.execute.return_value = MagicMock(data=[], error=None)
    
    return client

@pytest.fixture
def mock_tools():
    """Provides mocks for external tools (SMS, Email)."""
    with patch('instabids.agents.outbound_recruiter_agent.send_sms') as mock_sms, \
         patch('instabids.agents.outbound_recruiter_agent.send_email') as mock_email, \
         patch('instabids.agents.outbound_recruiter_agent._sb', new_callable=MagicMock) as mock_sb: # Patch the module-level client used by Agent
         
        mock_sms.return_value = {'sid': 'SM_test_sid', 'status': 'queued'}
        mock_email.return_value = 'sg:202'
        # Configure mock_sb with behavior from mock_supabase_client fixture
        # (This assumes the agent directly uses the imported _sb)
        mock_sb.table.return_value.select.return_value.eq.return_value = mock_sb
        mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value = mock_sb
        mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[], count=0, error=None)
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], count=0, error=None)
        mock_sb.table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[], error=None)
        mock_sb.table.return_value.select.return_value.contains.return_value.limit.return_value.execute.return_value = MagicMock(data=[], error=None)
        mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[], error=None)
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(error=None)
        mock_sb.rpc.return_value.execute.return_value = MagicMock(data=[], error=None)

        yield {
            'sms': mock_sms,
            'email': mock_email,
            'sb': mock_sb
        }

# --- Test Cases ---

def test_run_cycle_no_cards_needed(mock_tools):
    """Test run_cycle when no bid cards require more bids."""
    agent = OutboundRecruiterAgent()
    
    # Mock DB calls to return no cards needing bids
    mock_tools['sb'].table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[], error=None)
    
    summary = agent.run_cycle()
    
    assert summary['processed_cards'] == 0
    assert summary['invites_sent'] == 0
    assert summary['errors'] == 0
    mock_tools['sms'].assert_not_called()
    mock_tools['email'].assert_not_called()
    mock_tools['sb'].rpc.assert_not_called() # No targets needed, so no matching

def test_run_cycle_card_already_has_enough_invites(mock_tools):
    """Test run_cycle skips card if active invites >= MIN_BIDS."""
    bid_card_id = 'bc_enough'
    project_id = 'proj_enough'
    mock_bid_card = {'id': bid_card_id, 'project_id': project_id, 'category': 'plumbing', 'created_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    
    # Mock DB to return this card
    mock_tools['sb'].table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_bid_card], error=None)
    # Mock active invite count to be >= MIN_BIDS
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[{'id': i} for i in range(_MIN_BIDS)], count=_MIN_BIDS, error=None)

    agent = OutboundRecruiterAgent()
    summary = agent.run_cycle()
    
    assert summary['processed_cards'] == 1
    assert summary['invites_sent'] == 0
    assert summary['errors'] == 0
    # Verify active invite count was checked
    mock_tools['sb'].table('contractor_invites').select('id', count='exact').eq('bid_card_id', bid_card_id).in_('status', ['queued', 'sent', 'responded']).execute.assert_called_once()
    # Verify no further actions taken for this card
    mock_tools['sb'].rpc.assert_not_called()
    mock_tools['sms'].assert_not_called()
    mock_tools['email'].assert_not_called()

def test_run_cycle_invite_internal_contractor(mock_tools):
    """Test selecting and inviting an internal contractor."""
    bid_card_id = 'bc_internal'
    project_id = 'proj_internal'
    contractor_id = 'user_internal_1'
    mock_bid_card = {'id': bid_card_id, 'project_id': project_id, 'category': 'electrical', 'created_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    mock_match = {'contractor_id': contractor_id, 'match_score': 0.9}
    
    # Setup mocks
    mock_tools['sb'].table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_bid_card], error=None)
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[], count=0, error=None) # No active invites
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], error=None) # No previously invited targets
    mock_tools['sb'].rpc.return_value.execute.return_value = MagicMock(data=[mock_match], error=None) # RPC returns one match

    agent = OutboundRecruiterAgent()
    # Patch _internal_notify as it's complex to test fully here
    with patch.object(agent, '_internal_notify', return_value=None) as mock_internal_notify:
        summary = agent.run_cycle()

    assert summary['processed_cards'] == 1
    assert summary['invites_sent'] == 1 # One internal invite sent
    assert summary['errors'] == 0
    
    # Verify RPC was called for matching
    mock_tools['sb'].rpc.assert_called_once_with('match_contractors', {'p_project': project_id})
    # Verify internal notification was called
    mock_internal_notify.assert_called_once_with(contractor_id, mock_bid_card)
    # Verify invite was recorded
    mock_tools['sb'].table('contractor_invites').insert.assert_called_once_with({
        'bid_card_id': bid_card_id,
        'contractor_id': contractor_id,
        'prospect_id': None,
        'channel': 'internal',
        'status': 'sent',
        'attempts': 1,
        'last_attempt_at': ANY, # Check time was set
        'response_payload': {}
    })
    # Verify external tools not called
    mock_tools['sms'].assert_not_called()
    mock_tools['email'].assert_not_called()

def test_run_cycle_invite_prospect_via_sms(mock_tools):
    """Test selecting and inviting a prospect via SMS."""
    bid_card_id = 'bc_prospect_sms'
    project_id = 'proj_prospect'
    prospect_id = 'prospect_sms_1'
    phone = '+15551234567'
    mock_bid_card = {'id': bid_card_id, 'project_id': project_id, 'category': 'landscaping', 'job_type': 'tree trimming', 'created_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    mock_prospect = {'id': prospect_id, 'phone': phone, 'email': None, 'business_name': 'Tree Co', 'service_categories': ['landscaping']}
    
    # Setup mocks
    mock_tools['sb'].table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_bid_card], error=None)
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[], count=0, error=None) # No active invites
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], error=None) # No previously invited targets
    mock_tools['sb'].rpc.return_value.execute.return_value = MagicMock(data=[], error=None) # No internal matches found
    # Prospect query returns the prospect
    mock_tools['sb'].table.return_value.select.return_value.contains.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_prospect], error=None)

    agent = OutboundRecruiterAgent()
    summary = agent.run_cycle()

    assert summary['processed_cards'] == 1
    assert summary['invites_sent'] == 1
    assert summary['errors'] == 0
    
    # Verify SMS tool was called
    mock_tools['sms'].assert_called_once()
    call_args, call_kwargs = mock_tools['sms'].call_args
    assert call_kwargs['to'] == phone
    assert mock_bid_card['job_type'] in call_kwargs['body']
    assert bid_card_id in call_kwargs['body'] # Check link contains bid_card_id
    
    # Verify invite was recorded
    mock_tools['sb'].table('contractor_invites').insert.assert_called_once_with({
        'bid_card_id': bid_card_id,
        'contractor_id': None,
        'prospect_id': prospect_id,
        'channel': 'sms',
        'status': 'queued', # Status from mock send_sms
        'attempts': 1,
        'last_attempt_at': ANY, 
        'response_payload': {'sid': 'SM_test_sid', 'status': 'queued'} # Payload from mock send_sms
    })
    mock_tools['email'].assert_not_called()

def test_run_cycle_invite_prospect_via_email(mock_tools):
    """Test selecting and inviting a prospect via Email (no phone)."""
    bid_card_id = 'bc_prospect_email'
    project_id = 'proj_prospect'
    prospect_id = 'prospect_email_1'
    email = 'test@example.com'
    mock_bid_card = {'id': bid_card_id, 'project_id': project_id, 'category': 'cleaning', 'job_type': 'deep clean', 'created_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    mock_prospect = {'id': prospect_id, 'phone': None, 'email': email, 'business_name': 'Clean Inc', 'service_categories': ['cleaning']}
    
    # Setup mocks (similar to SMS test, but prospect has email, no phone)
    mock_tools['sb'].table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_bid_card], error=None)
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[], count=0, error=None) 
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], error=None) 
    mock_tools['sb'].rpc.return_value.execute.return_value = MagicMock(data=[], error=None) 
    mock_tools['sb'].table.return_value.select.return_value.contains.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_prospect], error=None)

    agent = OutboundRecruiterAgent()
    summary = agent.run_cycle()

    assert summary['processed_cards'] == 1
    assert summary['invites_sent'] == 1
    assert summary['errors'] == 0
    
    # Verify Email tool was called
    mock_tools['email'].assert_called_once()
    call_args, call_kwargs = mock_tools['email'].call_args
    assert call_kwargs['to'] == email
    assert mock_bid_card['job_type'] in call_kwargs['subject']
    assert bid_card_id in call_kwargs['html'] # Check link
    
    # Verify invite was recorded
    mock_tools['sb'].table('contractor_invites').insert.assert_called_once_with({
        'bid_card_id': bid_card_id,
        'contractor_id': None,
        'prospect_id': prospect_id,
        'channel': 'email',
        'status': 'sent', # Assumes sg:202 means success
        'attempts': 1,
        'last_attempt_at': ANY, 
        'response_payload': {'ref': 'sg:202'} # Payload from mock send_email
    })
    mock_tools['sms'].assert_not_called()

def test_run_cycle_target_selection_mix(mock_tools):
    """Test selecting a mix of contractors and prospects when needed."""
    bid_card_id = 'bc_mix'
    project_id = 'proj_mix'
    contractor_id = 'user_mix_1'
    prospect_id = 'prospect_mix_1'
    phone = '+15557778888'
    
    mock_bid_card = {'id': bid_card_id, 'project_id': project_id, 'category': 'hvac', 'job_type': 'AC repair', 'created_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    mock_match = {'contractor_id': contractor_id, 'match_score': 0.8}
    mock_prospect = {'id': prospect_id, 'phone': phone, 'email': None, 'business_name': 'Cool Dudes', 'service_categories': ['hvac']}
    
    # Setup mocks: Need >=2 bids (_MIN_BIDS might be 3)
    mock_tools['sb'].table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_bid_card], error=None)
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[], count=0, error=None) # No active invites
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], error=None) # No previously invited targets
    mock_tools['sb'].rpc.return_value.execute.return_value = MagicMock(data=[mock_match], error=None) # RPC returns one match
    mock_tools['sb'].table.return_value.select.return_value.contains.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_prospect], error=None) # Prospect query returns one prospect

    agent = OutboundRecruiterAgent()
    with patch.object(agent, '_internal_notify', return_value=None) as mock_internal_notify:
        summary = agent.run_cycle()

    needed_invites = _MIN_BIDS # Expects to send this many if starting from 0
    assert summary['processed_cards'] == 1
    assert summary['invites_sent'] == 2 # Sent 1 internal + 1 SMS
    assert summary['errors'] == 0
    
    # Verify calls
    mock_internal_notify.assert_called_once_with(contractor_id, mock_bid_card)
    mock_tools['sms'].assert_called_once_with(to=phone, body=ANY)
    mock_tools['email'].assert_not_called()
    
    # Verify recording (called twice)
    assert mock_tools['sb'].table('contractor_invites').insert.call_count == 2
    calls = mock_tools['sb'].table('contractor_invites').insert.call_args_list
    # Check contractor invite recorded
    assert any(c.args[0]['contractor_id'] == contractor_id and c.args[0]['channel'] == 'internal' for c in calls)
    # Check prospect invite recorded
    assert any(c.args[0]['prospect_id'] == prospect_id and c.args[0]['channel'] == 'sms' for c in calls)

def test_run_cycle_skips_already_invited(mock_tools):
    """Test that already invited targets are skipped during selection."""
    bid_card_id = 'bc_skip'
    project_id = 'proj_skip'
    contractor_id_invited = 'user_skip_1'
    contractor_id_new = 'user_skip_2'
    prospect_id_invited = 'prospect_skip_1'
    prospect_id_new = 'prospect_skip_2'
    
    mock_bid_card = {'id': bid_card_id, 'project_id': project_id, 'category': 'painting', 'created_at': dt.datetime.now(dt.timezone.utc).isoformat()}
    mock_matches = [
        {'contractor_id': contractor_id_invited, 'match_score': 0.9},
        {'contractor_id': contractor_id_new, 'match_score': 0.8}
    ]
    mock_prospects = [
        {'id': prospect_id_invited, 'phone': '+15551112222', 'service_categories': ['painting']},
        {'id': prospect_id_new, 'email': 'new@prospect.com', 'service_categories': ['painting']}
    ]
    
    # Setup mocks
    mock_tools['sb'].table.return_value.select.return_value.gte.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_bid_card], error=None)
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[], count=0, error=None) # No active invites
    # Mock previously invited targets
    mock_tools['sb'].table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
        {'contractor_id': contractor_id_invited, 'prospect_id': None},
        {'contractor_id': None, 'prospect_id': prospect_id_invited}
    ], error=None) 
    mock_tools['sb'].rpc.return_value.execute.return_value = MagicMock(data=mock_matches, error=None) # RPC returns both matches
    mock_tools['sb'].table.return_value.select.return_value.contains.return_value.limit.return_value.execute.return_value = MagicMock(data=mock_prospects, error=None) # Query returns both prospects

    agent = OutboundRecruiterAgent()
    with patch.object(agent, '_internal_notify', return_value=None) as mock_internal_notify:
        summary = agent.run_cycle()

    assert summary['processed_cards'] == 1
    assert summary['invites_sent'] == 2 # Only new contractor and new prospect invited
    assert summary['errors'] == 0
    
    # Verify only new targets invited
    mock_internal_notify.assert_called_once_with(contractor_id_new, mock_bid_card)
    mock_tools['email'].assert_called_once_with(to=mock_prospects[1]['email'], subject=ANY, html=ANY)
    mock_tools['sms'].assert_not_called()
    
    # Verify recording
    assert mock_tools['sb'].table('contractor_invites').insert.call_count == 2
    calls = mock_tools['sb'].table('contractor_invites').insert.call_args_list
    assert any(c.args[0]['contractor_id'] == contractor_id_new for c in calls)
    assert any(c.args[0]['prospect_id'] == prospect_id_new for c in calls)

# Add more tests: Error handling (DB errors, tool errors), prospect without contact info, etc.

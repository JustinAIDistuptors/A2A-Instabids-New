import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, call

# Mock the A2A comms early before importing the agent
# This prevents the @on_envelope decorator from trying to register
mock_a2a_comm = MagicMock()

modules = {
    'instabids.a2a_comm': mock_a2a_comm,
    'instabids.data.supabase_client': MagicMock(),
    'instabids.tools.twilio_sms': MagicMock(),
    'instabids.tools.sendgrid_mail': MagicMock(),
    'instabids.services.google_places': MagicMock(),
}

with patch.dict('sys.modules', modules):
    from instabids.agents.matching_agent import handle_new_bidcard, _geo_from_location

# --- Test Data ---
_FAKE_BID_ID = "00000000-0000-0000-0000-000000000001"
_FAKE_EVT = {
    "bid_card_id": _FAKE_BID_ID,
}
_BID_ROW_VALID_LOC = {
    "id": _FAKE_BID_ID,
    "title": "Fix roof leak", 
    "category": "roofing", 
    "location": "40.123,-75.456" # Valid location
}
_BID_ROW_INVALID_LOC = {
    "id": _FAKE_BID_ID,
    "title": "Paint fence", 
    "category": "painting", 
    "location": "invalid-location-string" # Invalid location
}
_BID_ROW_NO_LOC = {
    "id": _FAKE_BID_ID,
    "title": "Install window", 
    "category": "windows", 
    "location": None # No location
}
_MATCH_RESULTS = [
    {"id": "a0000000-0000-0000-0000-00000000000a", "score": 0.85},
    {"id": "b0000000-0000-0000-0000-00000000000b", "score": 0.72},
]
_PROSPECTS = [
    {"place_id": "p1", "name": "Prospect One", "formatted_phone_number": "+15551112222", "vicinity": "1 Main St"},
    {"place_id": "p2", "name": "Prospect Two", "formatted_phone_number": "+15553334444", "vicinity": "2 Oak Ave"},
]

# --- Fixture for Mock Supabase --- 
@pytest.fixture
def mock_sb():
    # Create a mock Supabase client instance for patching
    # Use AsyncMock for methods that might be awaitable if Supabase client uses async
    # If Supabase client is sync, MagicMock is fine. Assuming sync for now.
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute = MagicMock(
         return_value=MagicMock(data=_BID_ROW_VALID_LOC, error=None)
    )
    sb.rpc.return_value.execute = MagicMock(
        return_value=MagicMock(data=_MATCH_RESULTS, error=None)
    )
    sb.table.return_value.insert.return_value.execute = MagicMock(
        return_value=MagicMock(data=[{"id": 1}], error=None) # Simulate successful insert
    )
    sb.table.return_value.upsert.return_value.execute = MagicMock(
        return_value=MagicMock(data=[{"id": 1}], error=None) # Simulate successful upsert
    )
    return sb

# --- Test Cases ---

@patch('instabids.agents.matching_agent._sb')
@patch('instabids.agents.matching_agent.send_envelope')
@patch('instabids.agents.matching_agent.google_places.nearby_contractors', return_value=[]) # No prospects initially
def test_handle_bidcard_success_flow(mock_google_places, mock_send_envelope, mock_sb_instance, mock_sb):
    """Tests the main success path: fetch bid, match RPC, insert scores, send envelope."""
    # Arrange: Configure the mock_sb fixture passed via patching
    mock_sb_instance.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = _BID_ROW_VALID_LOC
    mock_sb_instance.rpc.return_value.execute.return_value.data = _MATCH_RESULTS
    mock_sb_instance.table.return_value.insert.return_value.execute.return_value.data = [{}, {}] # Simulate 2 inserts
    
    # Act
    asyncio.run(handle_new_bidcard(_FAKE_EVT))
    
    # Assert
    # 1. Bid card fetch
    mock_sb_instance.table.assert_any_call('bid_cards')
    mock_sb_instance.table().select().eq.assert_called_once_with('id', _FAKE_BID_ID)
    mock_sb_instance.table().select().eq().maybe_single().execute.assert_called_once()
    
    # 2. RPC call
    expected_lat, expected_lng = _geo_from_location(_BID_ROW_VALID_LOC['location'])
    mock_sb_instance.rpc.assert_called_once_with(
        'match_contractors_rule', 
        {'p_category': _BID_ROW_VALID_LOC['category'], 'p_lat': expected_lat, 'p_lng': expected_lng}
    )
    mock_sb_instance.rpc().execute.assert_called_once()
    
    # 3. Insert match scores
    mock_sb_instance.table.assert_any_call('match_scores')
    expected_insert_payload = [
        {'bid_card_id': _FAKE_BID_ID, 'contractor_id': r['id'], 'score': r['score'], 'status': 'pending'} 
        for r in _MATCH_RESULTS
    ]
    # Check if the insert call was made with the correct payload (order might not matter)
    # This checks the *last* call to insert(). Need careful checks if multiple inserts happen.
    insert_call_args = mock_sb_instance.table('match_scores').insert.call_args[0][0]
    assert isinstance(insert_call_args, list)
    assert len(insert_call_args) == len(expected_insert_payload)
    # Compare contents ignoring order (convert to tuple of tuples for hashing in set)
    assert set(tuple(sorted(d.items())) for d in insert_call_args) == set(tuple(sorted(d.items())) for d in expected_insert_payload)
    mock_sb_instance.table('match_scores').insert().execute.assert_called_once()
    
    # 4. Send envelope
    mock_send_envelope.assert_called_once_with(
        'matching.invited', 
        {'bid_card_id': _FAKE_BID_ID, 'contractor_ids': [r['id'] for r in _MATCH_RESULTS]}
    )
    
    # 5. Google Places call (should not happen if matches >= 6, or if no lat/lng)
    mock_google_places.assert_not_called() # Because we found 2 matches, and lat/lng was valid

@patch('instabids.agents.matching_agent._sb')
@patch('instabids.agents.matching_agent.send_envelope')
@patch('instabids.agents.matching_agent.google_places.nearby_contractors', return_value=_PROSPECTS)
def test_handle_bidcard_with_prospect_seeding(mock_google_places, mock_send_envelope, mock_sb_instance, mock_sb):
    """Tests prospect seeding when DB matches are low and location is valid."""
    # Arrange: Simulate 0 matches from RPC, but valid location
    mock_sb_instance.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = _BID_ROW_VALID_LOC
    mock_sb_instance.rpc.return_value.execute.return_value.data = [] # No DB matches
    # Mock insert for match_scores (will be empty) and prospect tables
    mock_sb_instance.table('match_scores').insert.return_value.execute = MagicMock(return_value=MagicMock(data=[], error=None))
    mock_sb_instance.table('prospect_contractors').upsert.return_value.execute = MagicMock(return_value=MagicMock(data=[{}, {}], error=None))
    mock_sb_instance.table('prospect_outbox').insert.return_value.execute = MagicMock(return_value=MagicMock(data=[{}, {}], error=None))
    
    # Act
    asyncio.run(handle_new_bidcard(_FAKE_EVT))
    
    # Assert
    # 1. Bid card fetch and RPC happened (as in previous test)
    mock_sb_instance.table('bid_cards').select().eq().maybe_single().execute.assert_called_once()
    expected_lat, expected_lng = _geo_from_location(_BID_ROW_VALID_LOC['location'])
    mock_sb_instance.rpc.assert_called_once_with('match_contractors_rule', {'p_category': 'roofing', 'p_lat': expected_lat, 'p_lng': expected_lng})

    # 2. Match scores insert should NOT have been called with data (or called with empty list)
    # Check if table('match_scores').insert was called. If yes, assert its args were empty.
    insert_calls = mock_sb_instance.table('match_scores').insert.call_args_list
    if insert_calls:
        assert not insert_calls[0][0][0] # Assert the list passed to insert was empty
    # Or more simply, assert the execute on the insert wasn't called if insert returns self
    # mock_sb_instance.table('match_scores').insert().execute.assert_not_called() # If insert returns self
    # If insert doesn't return self, check execute on the specific result mock:
    # mock_sb_instance.table('match_scores').insert.return_value.execute.assert_not_called() # This depends on setup
    # Let's check based on the fixture setup: execute should be called even if list is empty
    mock_sb_instance.table('match_scores').insert().execute.assert_called_once()


    # 3. Send envelope should NOT be called as no contractors were matched
    mock_send_envelope.assert_not_called()
    
    # 4. Google Places should be called
    mock_google_places.assert_called_once_with(expected_lat, expected_lng)
    
    # 5. Prospect upsert
    mock_sb_instance.table.assert_any_call('prospect_contractors')
    expected_upsert_payload = [
        {'place_id': p['place_id'], 'name': p['name'], 'phone': p.get('formatted_phone_number'), 'raw_json': p} 
        for p in _PROSPECTS
    ]
    upsert_call_args = mock_sb_instance.table('prospect_contractors').upsert.call_args[0][0]
    assert isinstance(upsert_call_args, list)
    assert len(upsert_call_args) == len(expected_upsert_payload)
    assert set(tuple(sorted(d.items())) for d in upsert_call_args) == set(tuple(sorted(d.items())) for d in expected_upsert_payload)
    mock_sb_instance.table('prospect_contractors').upsert().execute.assert_called_once()
    
    # 6. Outbox insert
    mock_sb_instance.table.assert_any_call('prospect_outbox')
    expected_outbox_payload = [
        {'prospect_id': p['place_id'], 'bid_card_id': _FAKE_BID_ID, 'channel': 'sms', 
         'payload': {'body': f"InstaBids invite for {_BID_ROW_VALID_LOC['title']}"}, 'status': 'pending'} 
        for p in _PROSPECTS
    ]
    outbox_insert_call_args = mock_sb_instance.table('prospect_outbox').insert.call_args[0][0]
    assert isinstance(outbox_insert_call_args, list)
    assert len(outbox_insert_call_args) == len(expected_outbox_payload)
    assert set(tuple(sorted(d.items())) for d in outbox_insert_call_args) == set(tuple(sorted(d.items())) for d in expected_outbox_payload)
    mock_sb_instance.table('prospect_outbox').insert().execute.assert_called_once()

@patch('instabids.agents.matching_agent._sb')
@patch('instabids.agents.matching_agent.send_envelope')
@patch('instabids.agents.matching_agent.google_places.nearby_contractors')
def test_handle_bidcard_no_location_skips_seeding(mock_google_places, mock_send_envelope, mock_sb_instance, mock_sb):
    """Tests that prospect seeding is skipped if bid card has no location."""
    # Arrange: Simulate matches found, but no location in bid card
    mock_sb_instance.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = _BID_ROW_NO_LOC
    mock_sb_instance.rpc.return_value.execute.return_value.data = _MATCH_RESULTS # Found matches
    mock_sb_instance.table('match_scores').insert.return_value.execute = MagicMock(return_value=MagicMock(data=[{}, {}], error=None))

    # Act
    asyncio.run(handle_new_bidcard(_FAKE_EVT))

    # Assert
    # 1. RPC called with None for lat/lng
    mock_sb_instance.rpc.assert_called_once_with('match_contractors_rule', {'p_category': 'windows', 'p_lat': None, 'p_lng': None})
    # 2. Match scores inserted, envelope sent (as matches were found)
    mock_sb_instance.table('match_scores').insert().execute.assert_called_once()
    mock_send_envelope.assert_called_once()
    # 3. Google Places NOT called
    mock_google_places.assert_not_called()
    # 4. Prospect tables NOT touched
    assert mock_sb_instance.table('prospect_contractors').upsert.call_count == 0
    assert mock_sb_instance.table('prospect_outbox').insert.call_count == 1 # Called for match_scores, not prospect_outbox
    # More specific check for prospect_outbox insert:
    outbox_calls = mock_sb_instance.table('prospect_outbox').insert.call_args_list
    assert len(outbox_calls) == 0 # Should not have been called for prospect_outbox

@patch('instabids.agents.matching_agent._sb')
@patch('instabids.agents.matching_agent.send_envelope')
@patch('instabids.agents.matching_agent.google_places.nearby_contractors')
def test_handle_bidcard_rpc_error(mock_google_places, mock_send_envelope, mock_sb_instance, mock_sb):
    """Tests handling when the match_contractors_rule RPC fails."""
    # Arrange: Simulate RPC error
    mock_sb_instance.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = _BID_ROW_VALID_LOC
    mock_sb_instance.rpc.return_value.execute.return_value = MagicMock(data=None, error={"message": "RPC Error", "code": "500"})

    # Act
    asyncio.run(handle_new_bidcard(_FAKE_EVT))

    # Assert
    # 1. RPC was called
    mock_sb_instance.rpc.assert_called_once()
    # 2. Match scores insert should not happen with data
    insert_calls = mock_sb_instance.table('match_scores').insert.call_args_list
    if insert_calls:
        assert not insert_calls[0][0][0] # Assert the list passed to insert was empty
    # 3. Send envelope should not be called
    mock_send_envelope.assert_not_called()
    # 4. Google Places might be called (depends on error handling, currently it proceeds)
    # Let's assert it IS called because len(contractors) becomes 0 after error
    expected_lat, expected_lng = _geo_from_location(_BID_ROW_VALID_LOC['location'])
    mock_google_places.assert_called_once_with(expected_lat, expected_lng)

@patch('instabids.agents.matching_agent._sb')
def test_handle_bidcard_fetch_bid_fails(mock_sb_instance, mock_sb):
    """Tests handling when fetching the bid card fails."""
    # Arrange: Simulate bid fetch error
    mock_sb_instance.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None, error={"message": "DB Error", "code": "500"})
    # Spy on RPC call to ensure it's not made
    rpc_spy = mock_sb_instance.rpc

    # Act
    asyncio.run(handle_new_bidcard(_FAKE_EVT))

    # Assert
    # 1. Fetch was attempted
    mock_sb_instance.table('bid_cards').select().eq().maybe_single().execute.assert_called_once()
    # 2. RPC, insert, send_envelope, google_places should NOT be called
    rpc_spy.assert_not_called()
    assert mock_sb_instance.table('match_scores').insert.call_count == 0
    # Cannot easily check send_envelope/google_places without patching them here too
    # assert mock_send_envelope.call_count == 0 # Requires patching
    # assert mock_google_places.call_count == 0 # Requires patching

# --- Helper function tests ---
@pytest.mark.parametrize("location_str, expected_lat, expected_lng", [
    ("40.123,-75.456", 40.123, -75.456),
    (" 30.0 , 100.0 ", 30.0, 100.0), # With spaces
    ("-90,180", -90.0, 180.0),     # Edge cases
    ("90,-180", 90.0, -180.0),     # Edge cases
    ("invalid", None, None),
    ("40.123", None, None),
    (",-75.456", None, None),
    ("91.0,-75.0", None, None),     # Invalid lat
    ("40.0,-181.0", None, None),    # Invalid lng
    (None, None, None),
    ("", None, None),
])
def test_geo_from_location(location_str, expected_lat, expected_lng):
    lat, lng = _geo_from_location(location_str)
    if expected_lat is None:
        assert lat is None
        assert lng is None
    else:
        assert lat == pytest.approx(expected_lat)
        assert lng == pytest.approx(expected_lng)

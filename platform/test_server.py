"""
AND-103 Task 2: Server tests — existing endpoints (Part A) and
detail endpoint TDD (Part B).

Run from the project root:
    python3 -m pytest platform/test_server.py -v
"""
import sys
from pathlib import Path

# Allow importing server.py from the platform/ directory
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from server import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Part A: Tests for existing endpoints
# ---------------------------------------------------------------------------

def test_main_page_loads(client):
    """GET / returns HTTP 200 and contains the dashboard page."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Rocket Elevators" in response.data


def test_status_filter_returns_only_matching_rows(client):
    """GET /elevators?status=ACTIVE returns only ACTIVE rows in the fragment."""
    response = client.get("/elevators?status=ACTIVE")
    assert response.status_code == 200
    # All status badges in the response should be ACTIVE
    data = response.data.decode()
    assert "ACTIVE" in data
    assert "PENDING_RENEWAL" not in data


def test_sort_elevator_id_ascending_returns_correct_order(client):
    """GET /elevators?sort=elevator_id&order=asc returns rows in ascending ID order."""
    response = client.get("/elevators?sort=elevator_id&order=asc")
    assert response.status_code == 200
    data = response.data.decode()
    # Extract elevator IDs from the monospace table cells in order
    import re
    ids = [int(m) for m in re.findall(
        r'<td class="px-5 py-3 font-mono text-xs text-gray-600">(\d+)</td>', data
    )]
    assert ids == sorted(ids), "Elevator IDs are not in ascending order"


# ---------------------------------------------------------------------------
# Part B: TDD tests for GET /elevator/{id} (endpoint does not exist yet)
# ---------------------------------------------------------------------------

KNOWN_ID   = 10       # elevator 10 exists in merged_elevator_data.csv and inspection.csv
UNKNOWN_ID = 9999999  # guaranteed not to exist in the dataset


def test_detail_endpoint_known_id_returns_200(client):
    """GET /elevator/<known_id> returns HTTP 200 and includes that elevator's ID."""
    response = client.get(f"/elevator/{KNOWN_ID}")
    assert response.status_code == 200
    assert str(KNOWN_ID).encode() in response.data


def test_detail_endpoint_unknown_id_returns_404(client):
    """GET /elevator/<unknown_id> returns HTTP 404."""
    response = client.get(f"/elevator/{UNKNOWN_ID}")
    assert response.status_code == 404


def test_detail_endpoint_includes_inspection_history(client):
    """GET /elevator/<known_id> response includes inspection records with date, type, and outcome."""
    response = client.get(f"/elevator/{KNOWN_ID}")
    assert response.status_code == 200
    data = response.data.decode()
    # Elevator 10 has inspections in inspection.csv — at least one date, type, and outcome must appear
    assert "Inspection" in data or "inspection" in data
    # Passed is a known outcome for elevator 10
    assert "Passed" in data or "Follow up" in data or "Complete" in data

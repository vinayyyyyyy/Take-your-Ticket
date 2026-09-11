import pytest

from app import app,db


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def login_user(client, user_id=1, user_name="Test User", user_role="user"):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_name"] = user_name
        session["user_role"] = user_role


@pytest.fixture
def available_seat():
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT seats.id
        FROM seats
        JOIN shows
            ON shows.screen_id = seats.screen_id
        WHERE shows.id = 646
          AND seats.id NOT IN (
              SELECT booking_seats.seat_id
              FROM booking_seats
              JOIN bookings
                  ON booking_seats.booking_id = bookings.id
              WHERE bookings.show_id = 646
          )
        LIMIT 1
        """
    )

    seat = cursor.fetchone()
    cursor.close()

    assert seat is not None, "No available seat found for show 646."

    return seat["id"]


# --------------------------------------------------
# MOVIE API
# --------------------------------------------------

def test_get_movies(client):
    response = client.get("/api/v1/movies")

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_get_existing_movie(client):
    response = client.get("/api/v1/movies/1")

    assert response.status_code == 200

    data = response.get_json()

    assert "id" in data
    assert data["id"] == 1


def test_get_nonexistent_movie(client):
    response = client.get("/api/v1/movies/999999")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Movie not found."


# --------------------------------------------------
# SHOW API
# --------------------------------------------------

def test_get_movie_shows(client):
    response = client.get("/api/v1/movies/1/shows")

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_get_nonexistent_show(client):
    response = client.get("/api/v1/shows/999999")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Show not found."


# --------------------------------------------------
# BOOKING AUTHENTICATION
# --------------------------------------------------

def test_get_bookings_requires_authentication(client):
    response = client.get("/api/v1/bookings")

    assert response.status_code == 401

    data = response.get_json()

    assert data["error"] == "Authentication required."


def test_create_booking_requires_authentication(client):
    response = client.post(
        "/api/v1/bookings",
        json={
            "show_id": 646,
            "seat_ids": [1178]
        }
    )

    assert response.status_code == 401

    data = response.get_json()

    assert data["error"] == "Authentication required."


# --------------------------------------------------
# BOOKING VALIDATION
# --------------------------------------------------

def test_booking_requires_json_body(client):
    login_user(client)

    response = client.post(
        "/api/v1/bookings",
        json={}
    )

    assert response.status_code == 400


def test_booking_requires_show_id(client):
    login_user(client)

    response = client.post(
        "/api/v1/bookings",
        json={
            "seat_ids": [1178]
        }
    )

    assert response.status_code == 400


def test_booking_requires_seat_ids(client):
    login_user(client)

    response = client.post(
        "/api/v1/bookings",
        json={
            "show_id": 646
        }
    )

    assert response.status_code == 400


def test_booking_rejects_invalid_show_id(client):
    login_user(client)

    response = client.post(
        "/api/v1/bookings",
        json={
            "show_id": -1,
            "seat_ids": [1178]
        }
    )

    assert response.status_code == 400


# --------------------------------------------------
# API ERROR HANDLERS
# --------------------------------------------------

def test_unknown_api_endpoint(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "API endpoint not found."


def test_api_method_not_allowed(client):
    response = client.post("/api/v1/movies")

    assert response.status_code == 405

    data = response.get_json()

    assert data["error"] == "Method not allowed."


# --------------------------------------------------
# BOOKING BEHAVIOR
# --------------------------------------------------

def test_get_bookings_authenticated(client):
    login_user(client)

    response = client.get("/api/v1/bookings")

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_get_nonexistent_booking(client):
    login_user(client)

    response = client.get("/api/v1/bookings/999999")

    assert response.status_code == 404


def test_get_booking_belonging_to_another_user(client):
    login_user(client, user_id=2)

    response = client.get("/api/v1/bookings/21")

    assert response.status_code == 404


# --------------------------------------------------
# BOOKING SUCCESS AND CONFLICT
# --------------------------------------------------

def test_create_booking_success(client, available_seat):
    login_user(client)

    response = client.post(
        "/api/v1/bookings",
        json={
            "show_id": 646,
            "seat_ids": [available_seat]
        }
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Booking created successfully."
    assert data["show_id"] == 646
    assert data["seat_ids"] == [available_seat]
    assert "booking_id" in data
    assert "total_amount" in data


def test_create_booking_conflict(client, available_seat):
    login_user(client)

    first_response = client.post(
        "/api/v1/bookings",
        json={
            "show_id": 646,
            "seat_ids": [available_seat]
        }
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/bookings",
        json={
            "show_id": 646,
            "seat_ids": [available_seat]
        }
    )

    assert second_response.status_code == 409

    data = second_response.get_json()

    assert "already been booked" in data["error"]
def test_booking_transaction_rolls_back(client, available_seat, monkeypatch):
    login_user(client)

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT COUNT(*) AS booking_count
        FROM bookings
        WHERE show_id = 646
          AND user_id = 1
        """
    )

    before = cursor.fetchone()["booking_count"]
    cursor.close()

    def failing_commit():
        raise Exception("Forced test failure")

    monkeypatch.setattr(db, "commit", failing_commit)

    response = client.post(
        "/api/v1/bookings",
        json={
            "show_id": 646,
            "seat_ids": [available_seat]
        }
    )

    assert response.status_code == 500

    data = response.get_json()

    assert data["error"] == "Booking failed. Please try again."

    monkeypatch.undo()

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT COUNT(*) AS booking_count
        FROM bookings
        WHERE show_id = 646
          AND user_id = 1
        """
    )

    after = cursor.fetchone()["booking_count"]
    cursor.close()

    assert after == before

def test_get_show_seats(client):
    response = client.get("/api/v1/shows/646/seats")

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) > 0

    seat = data[0]

    assert "seat_id" in seat
    assert "seat_number" in seat
    assert "category_name" in seat
    assert "price" in seat
    assert "is_booked" in seat


def test_get_nonexistent_show_seats(client):
    response = client.get("/api/v1/shows/999999/seats")

    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Show not found."

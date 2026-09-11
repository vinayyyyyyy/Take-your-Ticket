from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from dotenv import load_dotenv
from services.booking_service import (
    create_booking,
    get_booking_details,
    get_booking_preview,
    ShowNotFoundError,
    InvalidSeatSelectionError,
    SeatAlreadyBookedError
)
from services.movie_service import (
    get_all_movies,
    get_movie_by_id,
    get_movie_shows
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

print("MySQL connection successful!")


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Authentication required."
                }), 401

            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view


def admin_required(view_function):
    @wraps(view_function)
    @login_required
    def wrapped_view(*args, **kwargs):
        if session.get("user_role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Admin access required."
                }), 403

            return "Access denied. Admins only.", 403

        return view_function(*args, **kwargs)

    return wrapped_view


@app.before_request
def authentication_middleware():

    protected_paths = (
        "/api/v1/bookings",
        "/api/v1/booking-summary",
        "/bookings",
        "/booking-summary",
        "/confirm-booking",
    )

    if request.path.startswith(protected_paths):

        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Authentication required."
                }), 401

            return redirect("/login")


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return "All fields are required."

        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            return "An account with this email already exists."

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (name, email, password_hash)
        )

        db.commit()
        cursor.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return "Email and password are required."

        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, name, email, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()
        cursor.close()

        if not user:
            return "Invalid email or password."

        if not check_password_hash(user["password_hash"], password):
            return "Invalid email or password."

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]

        return redirect(url_for("api_movies"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("home"))


@app.route("/api/v1/movies", methods=["GET"])
@app.route("/movies", methods=["GET"])
def api_movies():
    if request.path.startswith("/api/"):
        movies_data = get_all_movies(db)
        return jsonify(movies_data)

    cursor = db.cursor(dictionary=True)

    selected_city = request.args.get("city", "").strip()

    selected_theatre = request.args.get("theatre", "").strip()
    selected_date = request.args.get("date", "").strip()

    # ---------------------------------------------------------
    # Get cities
    # ---------------------------------------------------------
    cursor.execute(
        """
        SELECT DISTINCT location
        FROM theatres
        WHERE location IS NOT NULL
          AND location <> ''
        ORDER BY location
        """
    )
    cities = [row["location"] for row in cursor.fetchall()]

    # ---------------------------------------------------------
    # Get theatres (optionally limited to the selected city)
    # ---------------------------------------------------------
    if selected_city:
        cursor.execute(
            """
            SELECT id, name, location
            FROM theatres
            WHERE location = %s
            ORDER BY name
            """,
            (selected_city,)
        )
    else:
        cursor.execute(
            """
            SELECT id, name, location
            FROM theatres
            ORDER BY location, name
            """
        )

    theatres = cursor.fetchall()

    # ---------------------------------------------------------
    # Get available dates, limited by city and theatre filters
    # ---------------------------------------------------------
    date_query = """
        SELECT DISTINCT shows.show_date
        FROM shows
        JOIN screens ON shows.screen_id = screens.id
        JOIN theatres ON screens.theatre_id = theatres.id
        WHERE shows.show_date >= CURDATE()
    """
    date_params = []

    if selected_city:
        date_query += """
            AND theatres.location = %s
        """
        date_params.append(selected_city)

    if selected_theatre:
        date_query += """
            AND theatres.id = %s
        """
        date_params.append(selected_theatre)

    date_query += """
        ORDER BY shows.show_date
    """

    cursor.execute(date_query, tuple(date_params))
    dates = [row["show_date"] for row in cursor.fetchall()]

    # ---------------------------------------------------------
    # Build the movie query from the optional filters
    # ---------------------------------------------------------
    movie_query = """
        SELECT DISTINCT movies.*
        FROM movies
        JOIN shows ON shows.movie_id = movies.id
        JOIN screens ON shows.screen_id = screens.id
        JOIN theatres ON screens.theatre_id = theatres.id
        WHERE shows.show_date >= CURDATE()
    """
    movie_params = []

    if selected_city:
        movie_query += """
            AND theatres.location = %s
        """
        movie_params.append(selected_city)

    if selected_theatre:
        movie_query += """
            AND theatres.id = %s
        """
        movie_params.append(selected_theatre)

    if selected_date:
        movie_query += """
            AND shows.show_date = %s
        """
        movie_params.append(selected_date)

    movie_query += """
        ORDER BY movies.id
    """

    cursor.execute(movie_query, tuple(movie_params))
    movies_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "movies.html",
        movies=movies_data,
        cities=cities,
        theatres=theatres,
        dates=dates,
        selected_city=selected_city,
        selected_theatre=selected_theatre,
        selected_date=selected_date
    )


@app.errorhandler(404)
def api_not_found(error):
    if request.path.startswith("/api/v1/"):
        return jsonify({
            "error": "API endpoint not found."
        }), 404

    return error


@app.errorhandler(405)
def api_method_not_allowed(error):
    if request.path.startswith("/api/v1/"):
        return jsonify({
            "error": "Method not allowed."
        }), 405

    return error


@app.errorhandler(500)
def api_internal_server_error(error):
    if request.path.startswith("/api/v1/"):
        return jsonify({
            "error": "Internal server error."
        }), 500

    return error


@app.route("/api/v1/movies/<int:movie_id>/shows", methods=["GET"])
def api_movie_shows(movie_id):

    cursor = db.cursor(dictionary=True)

    # ---------------------------------------------------------
    # Check movie exists
    # ---------------------------------------------------------
    cursor.execute(
        "SELECT id FROM movies WHERE id = %s",
        (movie_id,)
    )

    movie = cursor.fetchone()

    if not movie:
        cursor.close()
        return jsonify({
            "error": "Movie not found."
        }), 404

    # ---------------------------------------------------------
    # Read optional query parameters
    # ---------------------------------------------------------
    selected_date = request.args.get("date", "").strip()
    selected_location = request.args.get("location", "").strip()
    selected_theatre = request.args.get("theatre", "").strip()

    # ---------------------------------------------------------
    # Validate date
    # ---------------------------------------------------------
    if selected_date:
        try:
            datetime.strptime(selected_date, "%Y-%m-%d")
        except ValueError:
            cursor.close()
            return jsonify({
                "error": "date must be in YYYY-MM-DD format."
            }), 400

    # ---------------------------------------------------------
    # Validate theatre
    # ---------------------------------------------------------
    if selected_theatre:
        try:
            selected_theatre = int(selected_theatre)
        except ValueError:
            cursor.close()
            return jsonify({
                "error": "theatre must be an integer."
            }), 400

        if selected_theatre <= 0:
            cursor.close()
            return jsonify({
                "error": "theatre must be a positive integer."
            }), 400

    # ---------------------------------------------------------
    # Validate location
    # ---------------------------------------------------------
    if selected_location and not isinstance(selected_location, str):
        cursor.close()
        return jsonify({
            "error": "location must be a string."
        }), 400

    cursor.close()

    shows_data = get_movie_shows(
        db,
        movie_id,
        selected_date=selected_date or None,
        selected_location=selected_location or None,
        selected_theatre=selected_theatre or None
    )

    for show in shows_data:
        show["show_time"] = str(show["show_time"])

    return jsonify(shows_data)


def get_show_details_data(show_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            shows.id AS show_id,
            movies.id AS movie_id,
            movies.name AS movie_name,
            movies.language,
            movies.duration,
            theatres.id AS theatre_id,
            theatres.name AS theatre_name,
            theatres.location,
            screens.id AS screen_id,
            screens.name AS screen_name,
            screens.screen_format,
            shows.show_date,
            CAST(shows.show_time AS CHAR) AS show_time
        FROM shows
        JOIN movies
            ON shows.movie_id = movies.id
        JOIN screens
            ON shows.screen_id = screens.id
        JOIN theatres
            ON screens.theatre_id = theatres.id
        WHERE shows.id = %s
        """,
        (show_id,)
    )

    show = cursor.fetchone()
    cursor.close()

    return show


def get_show_seats_data(show_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            seats.id AS seat_id,
            seats.seat_number,
            seats.row_label,
            seats.column_number,
            seat_categories.id AS category_id,
            seat_categories.name AS category_name,
            show_seat_prices.price,

            EXISTS (
                SELECT 1
                FROM booking_seats
                JOIN bookings
                    ON booking_seats.booking_id = bookings.id
                WHERE booking_seats.seat_id = seats.id
                  AND bookings.show_id = %s
            ) AS is_booked

        FROM shows
        JOIN seats
            ON seats.screen_id = shows.screen_id
        JOIN seat_categories
            ON seats.category_id = seat_categories.id
        JOIN show_seat_prices
            ON show_seat_prices.show_id = %s
           AND show_seat_prices.category_id = seats.category_id

        WHERE shows.id = %s

        ORDER BY
            seats.row_label,
            seats.column_number
        """,
        (show_id, show_id, show_id)
    )

    seats = cursor.fetchall()
    cursor.close()

    return seats


def show_controller(show_id):
    show = get_show_details_data(show_id)

    if not show:
        return None

    seats = get_show_seats_data(show_id)

    return {
        "show": show,
        "seats": seats
    }


@app.route("/api/v1/shows/<int:show_id>", methods=["GET"])
@app.route("/show/<int:show_id>", methods=["GET"])
def api_show_details(show_id):
    show_data = show_controller(show_id)

    if not show_data:
        if request.path.startswith("/api/"):
            return jsonify({
                "error": "Show not found."
            }), 404

        return "Show not found.", 404

    show = show_data["show"]
    seats = show_data["seats"]

    if request.path.startswith("/api/"):
        return jsonify(show)

    seat_rows = {}

    for seat in seats:
        row = seat["row_label"]

        if row not in seat_rows:
            seat_rows[row] = []

        seat_rows[row].append(seat)

    return render_template(
        "show_details.html",
        show=show,
        seats=seats,
        seat_rows=seat_rows
    )


@app.route("/api/v1/shows/<int:show_id>/seats", methods=["GET"])
def api_show_seats(show_id):
    show_data = show_controller(show_id)

    if not show_data:
        return jsonify({
            "error": "Show not found."
        }), 404

    return jsonify(show_data["seats"])


def get_user_bookings(user_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            bookings.id AS booking_id,

            movies.name AS movie,

            theatres.name AS theatre,
            theatres.location,

            screens.name AS screen,

            shows.show_date,
            CAST(shows.show_time AS CHAR) AS show_time,

            bookings.booking_time,
            bookings.total_amount,

            GROUP_CONCAT(
                seats.seat_number
                ORDER BY seats.row_label, seats.column_number
                SEPARATOR ', '
            ) AS seats

        FROM bookings

        JOIN shows
            ON bookings.show_id = shows.id

        JOIN movies
            ON shows.movie_id = movies.id

        JOIN screens
            ON shows.screen_id = screens.id

        JOIN theatres
            ON screens.theatre_id = theatres.id

        JOIN booking_seats
            ON bookings.id = booking_seats.booking_id

        JOIN seats
            ON booking_seats.seat_id = seats.id

        WHERE bookings.user_id = %s

        GROUP BY
            bookings.id,
            movies.name,
            theatres.name,
            theatres.location,
            screens.name,
            shows.show_date,
            shows.show_time,
            bookings.booking_time,
            bookings.total_amount

        ORDER BY
            bookings.booking_time DESC
        """,
        (user_id,)
    )

    bookings_data = cursor.fetchall()
    cursor.close()

    return bookings_data


def bookings_controller(user_id):
    return get_user_bookings(user_id)


def create_booking_controller(user_id, show_id, selected_seats):
    return create_booking(
        db,
        user_id,
        show_id,
        selected_seats
    )


def booking_details_controller(booking_id, user_id):
    return get_booking_details(
        db,
        booking_id,
        user_id
    )


@app.route("/api/v1/bookings", methods=["GET"])
@app.route("/bookings", methods=["GET"])
def api_bookings():
    bookings_data = bookings_controller(
        session["user_id"]
    )

    if request.path.startswith("/api/"):
        return jsonify(bookings_data)

    return render_template(
        "bookings.html",
        bookings=bookings_data
    )


@app.route("/api/v1/bookings/<int:booking_id>", methods=["GET"])
def api_booking_details(booking_id):
    booking_data = booking_details_controller(
        booking_id,
        session["user_id"]
    )

    if not booking_data:
        return jsonify({
            "error": "Booking not found."
        }), 404

    return jsonify(booking_data)


@app.route("/api/v1/bookings", methods=["POST"])
@app.route("/confirm-booking/<int:show_id>", methods=["POST"])
@login_required
def api_create_booking(show_id=None):

    is_api_request = request.path.startswith("/api/")

    if is_api_request:
        data = request.get_json(silent=True)

        if data is None:
            return jsonify({
                "error": "JSON request body is required."
            }), 400

        if not isinstance(data, dict):
            return jsonify({
                "error": "JSON request body must be an object."
            }), 400

        show_id = data.get("show_id")
        selected_seats = data.get("seat_ids")

    else:
        selected_seats = request.form.getlist("seats")

    if show_id is None:
        if is_api_request:
            return jsonify({
                "error": "show_id is required."
            }), 400

        return "Invalid show."

    if (
        isinstance(show_id, bool)
        or not isinstance(show_id, int)
        or show_id <= 0
    ):
        if is_api_request:
            return jsonify({
                "error": "show_id must be a positive integer."
            }), 400

        return "Invalid show."

    if selected_seats is None or not selected_seats:
        if is_api_request:
            return jsonify({
                "error": "seat_ids must be a non-empty list."
            }), 400

        return "Please select at least one seat."

    if not is_api_request:
        try:
            selected_seats = [
                int(seat_id)
                for seat_id in selected_seats
            ]
        except ValueError:
            return "Invalid seat selection."

    if not isinstance(selected_seats, list):
        return jsonify({
            "error": "seat_ids must be a list."
        }), 400

    if not selected_seats:
        if is_api_request:
            return jsonify({
                "error": "seat_ids must be a non-empty list."
            }), 400

        return "Please select at least one seat."

    if any(
        isinstance(seat_id, bool)
        or not isinstance(seat_id, int)
        for seat_id in selected_seats
    ):
        if is_api_request:
            return jsonify({
                "error": "seat_ids must contain only integers."
            }), 400

        return "Invalid seat selection."

    if any(seat_id <= 0 for seat_id in selected_seats):
        if is_api_request:
            return jsonify({
                "error": "seat_ids must contain only positive integers."
            }), 400

        return "Invalid seat selection."

    if len(selected_seats) != len(set(selected_seats)):
        if is_api_request:
            return jsonify({
                "error": "Duplicate seat IDs are not allowed."
            }), 400

        return "Invalid seat selection."

    try:
        result = create_booking_controller(
            session["user_id"],
            show_id,
            selected_seats
        )

        if is_api_request:
            return jsonify({
                "message": "Booking created successfully.",
                "booking_id": result["booking_id"],
                "show_id": show_id,
                "seat_ids": selected_seats,
                "total_amount": str(result["total_price"])
            }), 201

        return render_template(
            "booking_success.html",
            show=result["show"],
            seats=result["seats"],
            total_price=result["total_price"],
            booking_id=result["booking_id"]
        )

    except ShowNotFoundError:
        if is_api_request:
            return jsonify({
                "error": "Show not found."
            }), 404

        return "Invalid show."

    except InvalidSeatSelectionError:
        if is_api_request:
            return jsonify({
                "error": "Invalid seat selection for this show."
            }), 400

        return "Invalid seat selection for this show."

    except SeatAlreadyBookedError as error:
        if is_api_request:
            return jsonify({
                "error": (
                    f"Seat {error.seat_number} "
                    "has already been booked."
                )
            }), 409

        return (
            f"Seat {error.seat_number} "
            "has already been booked. "
            "Please select another seat."
        )

    except Exception as error:
        print("Booking error:", error)

        if is_api_request:
            return jsonify({
                "error": "Booking failed. Please try again."
            }), 500

        return "Booking failed. Please try again."


@app.route("/api/v1/movies/<int:movie_id>", methods=["GET"])
@app.route("/movie/<int:movie_id>")
def api_movie_details(movie_id):
    # Receive filters from the movies page.
    selected_city = request.args.get("city", "").strip()
    selected_theatre = request.args.get("theatre", "").strip()
    selected_date = request.args.get("date", "").strip()

    # ---------------------------------------------------------
    # Get movie
    # ---------------------------------------------------------
    now = datetime.now()

    current_date = now.date()
    current_time = now.time()

    movie = get_movie_by_id(db, movie_id)

    if not movie:
        if request.path.startswith("/api/"):
            return jsonify({
                "error": "Movie not found."
            }), 404

        return "Movie not found."

    if request.path.startswith("/api/"):
        return jsonify(movie)

    cursor = db.cursor(dictionary=True)

    # ---------------------------------------------------------
    # Get available dates.
    # Exclude the selected date filter.
    # ---------------------------------------------------------
    date_shows = get_movie_shows(
        db,
        movie_id,
        current_date=current_date,
        current_time=current_time,
        selected_location=selected_city or None,
        selected_theatre=selected_theatre or None
    )

    available_dates = []

    for show in date_shows:
        if show["show_date"] not in available_dates:
            available_dates.append(show["show_date"])

    # ---------------------------------------------------------
    # Get available theatres.
    # Exclude the selected theatre filter.
    # ---------------------------------------------------------
    theatre_shows = get_movie_shows(
        db,
        movie_id,
        current_date=current_date,
        current_time=current_time,
        selected_location=selected_city or None,
        selected_date=selected_date or None
    )

    available_theatres = {}

    for show in theatre_shows:
        theatre_id = show["theatre_id"]

        available_theatres[theatre_id] = {
            "id": theatre_id,
            "name": show["theatre_name"],
            "location": show["location"]
        }

    available_theatres = list(available_theatres.values())

    # ---------------------------------------------------------
    # Get shows matching all selected filters.
    # ---------------------------------------------------------
    shows = get_movie_shows(
        db,
        movie_id,
        current_date=current_date,
        current_time=current_time,
        selected_location=selected_city or None,
        selected_theatre=selected_theatre or None,
        selected_date=selected_date or None
    )

    for show in shows:
        show["theatre"] = show["theatre_name"]
        show["screen"] = show["screen_name"]
        show["show_time_display"] = str(show["show_time"])[:5]

    # ---------------------------------------------------------
    # Group shows: Date -> Theatre -> Screen -> Show times
    # ---------------------------------------------------------
    show_groups = {}

    for show in shows:
        date = show["show_date"]

        if date not in show_groups:
            show_groups[date] = {}

        theatre = show["theatre"]

        if theatre not in show_groups[date]:
            show_groups[date][theatre] = {}

        screen = show["screen"]

        if screen not in show_groups[date][theatre]:
            show_groups[date][theatre][screen] = []

        show_groups[date][theatre][screen].append(show)

    selected_theatre_name = None

    if selected_theatre:
        cursor.execute(
            """
            SELECT name
            FROM theatres
            WHERE id = %s
            """,
            (selected_theatre,)
        )
        theatre_row = cursor.fetchone()

        if theatre_row:
            selected_theatre_name = theatre_row["name"]

    cursor.close()

    return render_template(
        "movie_details.html",
        movie=movie,
        shows=shows,
        show_groups=show_groups,
        available_dates=available_dates,
        available_theatres=available_theatres,
        selected_city=selected_city,
        selected_theatre=selected_theatre,
        selected_theatre_name=selected_theatre_name,
        selected_date=selected_date
    )

def booking_summary_controller(show_id, selected_seats):

    if not selected_seats:
        return {
            "error": "Please select at least one seat."
        }

    try:
        selected_seats = [
            int(seat_id)
            for seat_id in selected_seats
        ]
    except (ValueError, TypeError):
        return {
            "error": "Invalid seat selection."
        }

    if len(selected_seats) != len(set(selected_seats)):
        return {
            "error": "Invalid seat selection."
        }

    try:
        return get_booking_preview(
            db,
            show_id,
            selected_seats
        )

    except ShowNotFoundError:
        return {
            "error": "Show not found."
        }

    except InvalidSeatSelectionError:
        return {
            "error": "Invalid seat selection for this show."
        }

    except SeatAlreadyBookedError as error:
        return {
            "error": (
                f"Seat {error.seat_number} "
                "has already been booked. "
                "Please select another seat."
            )
        }


@app.route(
    "/api/v1/booking-summary/<int:show_id>",
    methods=["POST"]
)
@app.route(
    "/booking-summary/<int:show_id>",
    methods=["POST"]
)
@login_required
def booking_summary_handler(show_id):

    if request.path.startswith("/api/v1/"):
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "JSON request body must be an object."
            }), 400

        selected_seats = data.get("seat_ids")

    else:
        selected_seats = request.form.getlist("seats")

    result = booking_summary_controller(
        show_id,
        selected_seats
    )

    if "error" in result:
        if request.path.startswith("/api/v1/"):
            return jsonify(result), 400

        return result["error"]

    if request.path.startswith("/api/v1/"):
        return jsonify(result)

    return render_template(
        "booking_summary.html",
        show=result["show"],
        seats=result["seats"],
        total_price=result["total_price"]
    )

@app.route("/admin")
@admin_required
def admin():
    return "Welcome to the Admin Dashboard."


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)


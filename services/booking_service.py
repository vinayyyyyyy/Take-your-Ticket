class BookingServiceError(Exception):
    pass


class ShowNotFoundError(BookingServiceError):
    pass


class InvalidSeatSelectionError(BookingServiceError):
    pass


class SeatAlreadyBookedError(BookingServiceError):

    def __init__(self, seat_number):
        self.seat_number = seat_number


def create_booking(db, user_id, show_id, selected_seats):

    selected_seats = sorted(selected_seats)

    cursor = db.cursor(dictionary=True)

    try:
        db.rollback()
        db.start_transaction()

        # 1. Lock show and load booking information
        cursor.execute(
            """
            SELECT
                shows.id AS show_id,
                shows.show_date,
                shows.show_time,

                movies.id AS movie_id,
                movies.name AS movie_name,

                screens.id AS screen_id,
                screens.name AS screen,
                screens.screen_format,

                theatres.id AS theatre_id,
                theatres.name AS theatre,
                theatres.location

            FROM shows

            JOIN movies
                ON shows.movie_id = movies.id

            JOIN screens
                ON shows.screen_id = screens.id

            JOIN theatres
                ON screens.theatre_id = theatres.id

            WHERE shows.id = %s

            FOR UPDATE
            """,
            (show_id,)
        )

        show = cursor.fetchone()

        if not show:
            raise ShowNotFoundError()

        # 2. Lock selected seats
        placeholders = ",".join(
            ["%s"] * len(selected_seats)
        )

        cursor.execute(
            f"""
            SELECT
                seats.id,
                seats.screen_id,
                seats.seat_number,
                seats.category_id,

                seat_categories.name AS category_name,

                show_seat_prices.price

            FROM seats

            JOIN seat_categories
                ON seats.category_id = seat_categories.id

            JOIN show_seat_prices
                ON show_seat_prices.show_id = %s
               AND show_seat_prices.category_id = seats.category_id

            WHERE seats.screen_id = %s
              AND seats.id IN ({placeholders})

            ORDER BY seats.id

            FOR UPDATE
            """,
            (
                show_id,
                show["screen_id"],
                *selected_seats
            )
        )

        seats = cursor.fetchall()

        # 3. Validate that every selected seat belongs to this screen
        if len(seats) != len(selected_seats):
            raise InvalidSeatSelectionError()

        # 4. Check whether any selected seat is already booked
        cursor.execute(
            f"""
            SELECT
                booking_seats.seat_id,
                seats.seat_number

            FROM booking_seats

            JOIN bookings
                ON booking_seats.booking_id = bookings.id

            JOIN seats
                ON booking_seats.seat_id = seats.id

            WHERE bookings.show_id = %s
              AND booking_seats.seat_id IN ({placeholders})
            """,
            (
                show_id,
                *selected_seats
            )
        )

        already_booked = cursor.fetchall()

        if already_booked:
            raise SeatAlreadyBookedError(
                already_booked[0]["seat_number"]
            )

        # 5. Calculate total price
        total_price = sum(
            seat["price"]
            for seat in seats
        )

        # 6. Create booking
        cursor.execute(
            """
            INSERT INTO bookings
            (
                show_id,
                user_id,
                total_amount
            )
            VALUES
            (%s, %s, %s)
            """,
            (
                show_id,
                user_id,
                total_price
            )
        )

        booking_id = cursor.lastrowid

        # 7. Create booking-seat records
        for seat in seats:

            cursor.execute(
                """
                INSERT INTO booking_seats
                (
                    booking_id,
                    seat_id,
                    price_paid
                )
                VALUES
                (%s, %s, %s)
                """,
                (
                    booking_id,
                    seat["id"],
                    seat["price"]
                )
            )

        # 8. Commit the complete transaction
        db.commit()

        return {
            "booking_id": booking_id,
            "show": show,
            "seats": seats,
            "total_price": total_price
        }

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()


def get_booking_details(db, booking_id, user_id):

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                bookings.id AS booking_id,
                bookings.show_id,
                bookings.total_amount,
                bookings.booking_time,
                seats.id AS seat_id,
                seats.seat_number
            FROM bookings
            JOIN booking_seats
                ON bookings.id = booking_seats.booking_id
            JOIN seats
                ON booking_seats.seat_id = seats.id
            WHERE bookings.id = %s
              AND bookings.user_id = %s
            """,
            (booking_id, user_id)
        )

        return cursor.fetchall()

    finally:
        cursor.close()


def get_booking_preview(db, show_id, selected_seats):

    selected_seats = sorted(selected_seats)

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                shows.id AS show_id,
                shows.show_date,
                CAST(shows.show_time AS CHAR) AS show_time,

                movies.id AS movie_id,
                movies.name AS movie_name,

                theatres.name AS theatre,
                theatres.location,

                screens.id AS screen_id,
                screens.name AS screen,
                screens.screen_format

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

        if not show:
            raise ShowNotFoundError()

        placeholders = ",".join(
            ["%s"] * len(selected_seats)
        )

        cursor.execute(
            f"""
            SELECT
                seats.id,
                seats.seat_number,

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

            FROM seats

            JOIN seat_categories
                ON seats.category_id = seat_categories.id

            JOIN show_seat_prices
                ON show_seat_prices.show_id = %s
               AND show_seat_prices.category_id = seats.category_id

            WHERE seats.screen_id = %s
              AND seats.id IN ({placeholders})

            ORDER BY
                seats.row_label,
                seats.column_number
            """,
            (
                show_id,
                show_id,
                show["screen_id"],
                *selected_seats
            )
        )

        seats = cursor.fetchall()

        if len(seats) != len(selected_seats):
            raise InvalidSeatSelectionError()

        for seat in seats:
            if seat["is_booked"]:
                raise SeatAlreadyBookedError(
                    seat["seat_number"]
                )

        total_price = sum(
            seat["price"]
            for seat in seats
        )

        show["id"] = show["show_id"]

        return {
            "show": show,
            "seats": seats,
            "total_price": total_price
        }

    finally:
        cursor.close()
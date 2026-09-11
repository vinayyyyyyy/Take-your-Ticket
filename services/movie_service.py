def get_all_movies(db):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM movies
        ORDER BY id
        """
    )

    movies = cursor.fetchall()
    cursor.close()

    return movies


def get_movie_by_id(db, movie_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM movies
        WHERE id = %s
        """,
        (movie_id,)
    )

    movie = cursor.fetchone()
    cursor.close()

    return movie


def get_movie_shows(
    db,
    movie_id,
    current_date=None,
    current_time=None,
    selected_date=None,
    selected_location=None,
    selected_theatre=None
):
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT
            shows.id AS show_id,
            shows.show_date,
            shows.show_time,

            theatres.id AS theatre_id,
            theatres.name AS theatre_name,
            theatres.location,

            screens.id AS screen_id,
            screens.name AS screen_name,
            screens.screen_format

        FROM shows

        JOIN screens
            ON shows.screen_id = screens.id

        JOIN theatres
            ON screens.theatre_id = theatres.id

        WHERE shows.movie_id = %s
    """

    params = [movie_id]

    if current_date is not None and current_time is not None:
        query += """
            AND (
                shows.show_date > %s
                OR (
                    shows.show_date = %s
                    AND shows.show_time > %s
                )
            )
        """

        params.extend([
            current_date,
            current_date,
            current_time
        ])

    if selected_date:
        query += """
            AND shows.show_date = %s
        """
        params.append(selected_date)

    if selected_location:
        query += """
            AND theatres.location = %s
        """
        params.append(selected_location)

    if selected_theatre:
        query += """
            AND theatres.id = %s
        """
        params.append(selected_theatre)

    query += """
        ORDER BY
            shows.show_date,
            shows.show_time
    """

    cursor.execute(query, tuple(params))

    shows = cursor.fetchall()
    cursor.close()

    return shows

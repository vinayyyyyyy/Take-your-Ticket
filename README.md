# 🎬 Take Your Ticket

<p align="center">
  <img src="assets/main-poster.jpg" alt="Take Your Ticket" width="700">
</p>

<p align="center">
  <b>A Flask-based movie ticket booking system with MySQL, REST APIs, authentication, and transaction-safe seat booking.</b>
</p>

---

## Overview

**Take Your Ticket** is a Flask-based movie ticket booking system built with **Python, MySQL, Jinja2, HTML, and CSS**.

The application provides end-to-end movie booking functionality, including movie and show discovery, seat selection, booking management, user authentication, role-based authorization, and REST APIs.

The booking workflow uses **database transactions, row-level locking, seat availability validation, and concurrency control** to safely handle competing booking requests.

---

<div align="center">

# ✨ What Can You Do?

</div>

| 🎬 **Movie Discovery** | 🎟️ **Ticket Booking** |
|:---|:---|
| Browse movies & shows<br>Filter by **city, theatre & date**<br>View movie details & schedules | View seat availability<br>Select & validate multiple seats<br>Server-side price calculation<br>Conflict prevention |

| 🔐 **Authentication** | 🔌 **REST APIs** |
|:---|:---|
| Registration & login<br>Session-based authentication<br>Protected booking operations<br>Role-based admin access | Versioned `/api/v1/` endpoints<br>JSON request/response handling<br>Movie, show, seat & booking APIs<br>Structured HTTP responses |

<br>

<div align="center">

### 🛡️ Technical Core

`TRANSACTIONS` &nbsp; • &nbsp; `ROW-LEVEL LOCKING` &nbsp; • &nbsp; `SEAT VALIDATION` &nbsp; • &nbsp; `CONCURRENCY CONTROL`

</div>

---

<div align="center">

# 🏗️ Architecture

</div>

```text
                         CLIENT
                    ┌───────────────┐
                    │    Browser    │
                    │      /        │
                    │   API Client  │
                    └───────┬───────┘
                            │
                       HTTP Request
                            │
                            ▼
                 ┌─────────────────────┐
                 │    Flask Backend    │
                 │                     │
                 │ Middleware / Auth   │
                 │        ↓            │
                 │ Routes / Controllers│
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    Service Layer    │
                 │                     │
                 │ Movie Operations    │
                 │ Booking Operations  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │       MySQL         │
                 │                     │
                 │ Queries             │
                 │ Transactions        │
                 │ Row-Level Locks     │
                 └──────────┬──────────┘
                            │
                            ▼
                       Result Data
                       ↙        ↘
                    HTML         JSON
                    Jinja      REST API
```

---

<div align="center">

# 🎟️ Booking Engine

### From seat selection to a transaction-safe booking

</div>

```text
User selects seats
        │
        ▼
  POST Booking Request
        │
        ▼
 Authentication Check
        │
        ▼
 Booking Controller
        │
        ▼
  Booking Service
        │
        ▼
 Start Transaction
        │
        ▼
   Lock Show Row
        │
        ▼
 Lock Selected Seats
        │
        ▼
 Validate Seat Set
        │
        ▼
 Check Existing Booking
        │
        ▼
  Calculate Price
        │
        ▼
  Create Booking
        │
        ▼
 Create Booking Seats
        │
        ▼
      COMMIT
        │
        ▼
   HTML / JSON
```

---

<div align="center">

# 🔒 Concurrency & Transaction Safety

</div>

The booking service uses **MySQL row-level locking** with:

```sql
SELECT ... FOR UPDATE
```

inside a database transaction.

```text
Start Transaction
       │
       ▼
   Lock Show
       │
       ▼
  Lock Seats
       │
       ▼
Validate Availability
       │
       ▼
 Calculate Price
       │
       ▼
 Create Booking
       │
       ▼
Create Booking Seats
       │
       ▼
     COMMIT
```

If an operation fails:

```text
Exception
    │
    ▼
 ROLLBACK
```

This coordinates concurrent booking requests at the **database level** and prevents partially completed booking operations.

---

<div align="center">

# 🗄️ Database

### MySQL 8.0 • InnoDB • Relational Data Model

</div>

```text
                         movies
                            │
                            ▼
                          shows
                            │
                     ┌──────┴──────┐
                     ▼             ▼
                  screens       show_seat_prices
                     │
                     ▼
                  theatres

users
  │
  ▼
bookings
  │
  ▼
booking_seats
  │
  ▼
seats
  │
  ▼
seat_categories
```

### 📊 Project Dataset

| Entity | Records |
|:---|---:|
| 🎬 Movies | **9** |
| 🏢 Theatres | **23** |
| 🖥️ Screens | **61** |
| 🎞️ Shows | **7,812** |
| 💺 Seats | **10,640** |
| 💰 Show-seat pricing records | **23,436** |

---

<div align="center">

# 🔌 REST API

### Versioned endpoints under `/api/v1/`

</div>

| Method | Endpoint | Purpose |
|:---:|:---|:---|
| `GET` | `/api/v1/movies` | Retrieve movies |
| `GET` | `/api/v1/movies/<id>` | Retrieve movie details |
| `GET` | `/api/v1/movies/<id>/shows` | Retrieve movie shows |
| `GET` | `/api/v1/shows/<id>` | Retrieve show details |
| `GET` | `/api/v1/shows/<id>/seats` | Retrieve seat availability |
| `GET` | `/api/v1/bookings` | Retrieve user bookings |
| `GET` | `/api/v1/bookings/<id>` | Retrieve booking details |
| `POST` | `/api/v1/booking-summary/<id>` | Generate booking preview |
| `POST` | `/api/v1/bookings` | Create a booking |

### HTTP Response Handling

```text
200  OK
201  Created
400  Bad Request
401  Unauthorized
403  Forbidden
404  Not Found
405  Method Not Allowed
409  Conflict
500  Internal Server Error
```

API errors are returned as structured JSON responses.

---

<div align="center">

# 🔐 Authentication & Authorization

</div>

```text
                  User
                   │
             Register / Login
                   │
                   ▼
          Credential Verification
                   │
                   ▼
             Flask Session
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
 Authentication          Authorization
        │                     │
   Is user logged in?    Is user admin?
        │                     │
        ▼                     ▼
 Protected Routes       Admin Functions
```

Passwords are stored using **Werkzeug password hashing** rather than plaintext credentials.

The application uses Flask sessions for authenticated user state and role information.

---

<div align="center">

# ⚙️ Technology Stack

</div>

| Layer | Technology |
|:---|:---|
| 🐍 Language | **Python** |
| 🌐 Backend | **Flask** |
| 🎨 Templates | **Jinja2** |
| 🖥️ Frontend | **HTML5 + CSS3** |
| 🔌 API | **REST / JSON** |
| 🗄️ Database | **MySQL 8.0** |
| 🔗 Database Driver | **MySQL Connector/Python** |
| 🔐 Security | **Flask Sessions + Werkzeug** |
| ⚙️ Configuration | **python-dotenv** |
| 🚀 Server | **Waitress** |

---

<div align="center">

# 📁 Project Structure

</div>

```text
Take-your-Ticket/
│
├── app.py
│
├── services/
│   ├── movie_service.py
│   └── booking_service.py
│
├── templates/
│   ├── booking_success.html
│   ├── booking_summary.html
│   ├── bookings.html
│   ├── home.html
│   ├── login.html
│   ├── movie_details.html
│   ├── movies.html
│   ├── navbar.html
│   ├── register.html
│   └── show_details.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── images/
│
├── assets/
│   └── main-poster.jpg
│
├── tests/
│   └── test_api.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

<div align="center">

# 🚀 Getting Started

</div>

### 1. Clone the repository

```bash
git clone https://github.com/vinayyyyyyy/Take-your-Ticket.git
cd Take-your-Ticket
```

### 2. Create a virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MySQL

Create the database:

```text
bookmyshow_v2
```

Import the project's SQL database dump into MySQL.

### 5. Configure environment variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key

DB_HOST=localhost
DB_USER=your-mysql-user
DB_PASSWORD=your-mysql-password
DB_NAME=bookmyshow_v2

FLASK_DEBUG=false
```

### 6. Run the application

```bash
python app.py
```

---

<div align="center">

### 🎬 Browse Movies → 🎟️ Select Seats → 🔒 Validate → 💳 Book → ✅ Confirm

<br>

**Take Your Ticket**

</div>

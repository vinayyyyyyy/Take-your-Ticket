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
                 │    Service Layer   │
                 │                     │
                 │ Movie Operations    │
                 │ Booking Operations  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │       MySQL         │
                 │                     │
                 │ Queries /           │
                 │ Transactions /      │
                 │ Row-Level Locks     │
                 └──────────┬──────────┘
                            │
                            ▼
                       Result Data
                       ↙        ↘
                    HTML         JSON
                    Jinja      REST API

# 🎬 Take Your Ticket

<p align="center">
  <img src="assets/main-poster.jpg" alt="Take Your Ticket" width="900">
</p>

<p align="center">
  <b>A Flask-based movie ticket booking system with MySQL, REST APIs, authentication, and transaction-safe seat booking.</b>
</p>
## Overview

**Take Your Ticket** is a Flask-based movie ticket booking system built with **Python, MySQL, Jinja2, HTML, and CSS**.

The application provides end-to-end movie booking functionality, including movie and show discovery, seat selection, booking management, user authentication, role-based authorization, and REST APIs.

The booking workflow uses **database transactions, row-level locking, seat availability validation, and concurrency control** to safely handle competing booking requests.

---

<div align="center">

# ✨ What Can You Do?

</div>

<table>
<tr>
<td width="50%" valign="top">

### 🎬 Movie Discovery

- Browse available movies and shows
- Filter by **city, theatre, and date**
- View detailed movie information
- Explore show schedules

</td>

<td width="50%" valign="top">

### 🎟️ Ticket Booking

- View real-time seat availability
- Select multiple seats
- Validate seats against the show's screen
- Calculate booking prices server-side
- Prevent conflicting bookings

</td>
</tr>

<tr>
<td width="50%" valign="top">

### 🔐 Authentication

- User registration and login
- Session-based authentication
- Protected booking operations
- Role-based admin authorization

</td>

<td width="50%" valign="top">

### 🔌 REST APIs

- Versioned `/api/v1/` endpoints
- JSON request/response handling
- Movie, show, seat and booking APIs
- Structured HTTP error responses

</td>
</tr>
</table>

<br>

<div align="center">

### 🛡️ The Technical Core

**Transactions** &nbsp; • &nbsp; **Row-Level Locking** &nbsp; • &nbsp; **Seat Validation** &nbsp; • &nbsp; **Concurrency Control**

</div>

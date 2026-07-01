# NBU Guidance System

A real-time classroom scheduling and relocation web application built for Northern Border University's Faculty of Computing and Information Technology. The system gives students, lecturers, and administrators live visibility into classroom availability, automatically detects scheduling conflicts, and instantly notifies affected users when a lecture is moved.

## Overview

University timetables are typically static and manually managed, making it hard to detect scheduling conflicts or safely relocate a lecture without accidentally clashing with another class or a student's existing schedule. This project solves that by combining automated conflict detection with real-time, student-aware relocation suggestions and live notifications.

## Features

- **Automated Conflict Detection** — Flags overlapping bookings by classroom, day, and time, removing the need for manual schedule-checking.
- **Student-Aware Relocation** — Before suggesting a new hall or time for a lecture, the system checks the timetables of every enrolled student and only offers conflict-free options, preventing new clashes before they happen.
- **Live Notifications** — Uses WebSocket (Socket.IO) to instantly alert affected students, lecturers, and admins when a lecture is relocated or a hall becomes free.
- **Role-Based Access Control** — Separate views and permissions for students, lecturers, and administrators.
- **Real Data Processing** — Ingests real course and enrollment data (CSV/JSON) exported from the university's Argos student system.
- **Atomic Bulk Undo** — Reverts all relocations in a single atomic operation, avoiding race conditions that occur with per-item undo requests.

## Tech Stack

- **Backend:** Python, Flask, Flask-SocketIO
- **Frontend:** JavaScript, HTML, CSS
- **Real-Time Communication:** WebSocket (Socket.IO)
- **Data:** CSV / JSON processing

## How It Works

1. Course and classroom data is loaded from CSV files and parsed into structured records.
2. A conflict-detection algorithm scans all bookings for the same classroom, day, and overlapping time ranges.
3. When a lecturer or admin relocates a class, the system cross-references every enrolled student's timetable to ensure the new slot is conflict-free for everyone.
4. Once a relocation is confirmed, the server broadcasts the update over WebSocket so all connected clients (students, lecturers, admins) see the change instantly — no page refresh required.
5. Notifications are automatically cleaned up once they expire, keeping the system lightweight.

## Project Structure

```
├── app.py                  # Flask backend, API routes, and SocketIO events
├── index.html               # Frontend interface
├── fcit_sample.csv           # Sample course/schedule data (fake data, real column structure)
├── ID_fcit_sample.csv        # Sample student enrollment data (fake data, real column structure)
├── .gitignore                # Excludes real university data from version control
├── LICENSE                    # MIT License
```

## Note on Data Privacy

The original dataset used during development was exported from NBU's Argos student system and contains real student and faculty information. That data has been excluded from this repository via `.gitignore`. Sample files with the same column structure but fictional data (`fcit_sample.csv`, `ID_fcit_sample.csv`) are provided so the project can be run and tested locally — rename them to `fcit.csv` and `ID_fcit.csv` (or update the paths in `app.py`) to use them.

## Team

- **Dhari Talal Alshammari** — dhari.altalal@gmail.com
- **Fahad Habib Alshammari**
- **Jarrah Faisal Alshammari**

Information Systems Graduates, Northern Border University

## Academic Context

Graduation Project — Northern Border University, Faculty of Computing and Information Technology
Supervised by Dr. Aadil Alshammari | Team of 8 | 2026

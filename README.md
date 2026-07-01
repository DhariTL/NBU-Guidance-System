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
├── app.py              # Flask backend, API routes, and SocketIO events
├── index.html           # Frontend interface
├── fcit.csv              # Course/schedule data (sample structure only — real data not included)
├── ID_fcit.csv           # Student enrollment data (sample structure only — real data not included)
```

## Note on Data Privacy

The original dataset used during development was exported from NBU's Argos student system and contains real student and faculty information. That data has been excluded from this repository. To run the project locally, replace `fcit.csv` and `ID_fcit.csv` with your own sample data following the same column structure.

## Author

**Dhari Al Talal**
Information Systems Graduate, Northern Border University
[LinkedIn](#) · dhari.altalal@gmail.com

## Academic Context

Graduation Project — Northern Border University, Faculty of Computing and Information Technology
Supervised by Dr. Aadil Alshammari | Team of 8 | 2026

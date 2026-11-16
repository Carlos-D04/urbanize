# Urbanize

Urbanize is a REST API for reporting and tracking urban issues, such as potholes,
broken streetlights, and missed waste collection. It is a backend engineering
learning project built with Python 3.13, Django, Django REST Framework, and
PostgreSQL.

## Request workflow

A request starts as `PENDING` and follows this sequence:

**PENDING → IN_REVIEW → IN_PROGRESS → RESOLVED**

Every request has an author, a category, and a responsible department. The
department comes from the selected category. Reclassifying a request updates its
category and department together.

API access is scoped by role:

| Role | Request access |
| --- | --- |
| `CITIZEN` | Can see their own requests and edit their details while they are pending. |
| `STAFF` | Can manage requests assigned to their department. |
| `ADMIN` | Can manage requests across departments. |

Status and category changes use dedicated API actions. The services reload and
lock the request before checking permissions and validating the change. The
request update, history entry, and any applicable in-app notification are written
in the same transaction. History distinguishes status changes from
reclassifications and includes the previous and new values relevant to the event.

## Notifications and email

Users can list their own notifications and mark them as read. Status changes
notify the author. Reclassifications also notify the author unless they performed
the change themselves.

A transition to `IN_PROGRESS` or `RESOLVED`, or a reclassification that creates an
in-app notification, schedules an email delivery after the main transaction
commits. If the delivery record cannot be created, the request change, history,
and in-app notification are preserved and the error is logged.

The email processor runs manually. It uses the recipient's current email
address, processes candidate deliveries oldest first, allows up to three
attempts per delivery, and waits at least 30 minutes between attempts on the
same delivery. It also waits 30 minutes after a successful delivery before
sending another email to the same recipient. Once a notification is 24 hours
old, a pending or retryable delivery is marked `EXPIRED` when processed.
The in-app notification remains available. Delivery status, attempts, and errors
can be inspected in the read-only Django Admin view.

## Local development with Docker Compose

Install Docker with Compose support. From the project root, copy `.env.example`
to `.env` and fill in these values. Replace the example secret and credentials
with local development values; keep `.env` out of version control.

| Variable | Example | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | A locally generated secret | Django signing key |
| `DB_NAME` | `urbanize` | Database name |
| `DB_USER` | `urbanize` | PostgreSQL user |
| `DB_PASSWORD` | A local development password | PostgreSQL password |
| `DB_HOST` | `db` | PostgreSQL service name inside Compose |
| `DB_PORT` | `5432` | PostgreSQL port inside Compose |

Start the services and apply the migrations:

```powershell
docker compose up -d --build
docker compose exec web python manage.py migrate
```

- API: [localhost:8000](http://localhost:8000/)
- Swagger UI: [localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- Django Admin: [localhost:8000/admin/](http://localhost:8000/admin/)
- PostgreSQL from the host: `127.0.0.1:5433`. Inside Compose, use `db:5432`.

To create a local administrator, run
`docker compose exec web python manage.py createsuperuser`. Use the Admin to
create departments and categories before submitting requests.
Django Admin access and the Urbanize API role are separate. To exercise API
operations as an administrator, assign the user the `ADMIN` role in Django Admin.

The image copies the source at build time. After changing application code,
rebuild the web service with `docker compose up -d --build web`. This setup uses
Django's development server and is intended for local use.

If you run Django directly on your host against the Compose database, set
`DB_HOST=127.0.0.1` and `DB_PORT=5433` for that process.

### Process email deliveries

```powershell
docker compose exec web python manage.py process_email_deliveries
```

Run one instance at a time. The command reports sent, failed, skipped, and
expired deliveries. It does not run automatically.

Django uses the console email backend by default. To capture email locally over
SMTP, set these values in your `.env`:

```dotenv
EMAIL_BACKEND=smtp
EMAIL_HOST=mailpit
EMAIL_PORT=1025
```

Run `docker compose up -d --build web mailpit` to load the updated environment.
Using the API, move a test request from `PENDING` to `IN_REVIEW` and then to
`IN_PROGRESS`. The second transition creates a pending delivery. Run the
processor above and verify that the delivery is `SENT` in Django Admin and the
recipient, subject, and body match in [Mailpit](http://127.0.0.1:8025/).

This workflow has been verified against Mailpit. Messages stay in the local
capture service; this does not validate delivery to an external inbox.

### Run tests

```powershell
docker compose exec web python manage.py test
```

For a focused run, append an app label such as `reports` or `notifications`.
Rebuild the web image first if the container does not have the latest code.

## API reference

Use `POST /api/token/` to obtain a JWT access token and
`POST /api/token/refresh/` to refresh it. Send the access token in the
`Authorization: Bearer <access_token>` header. The OpenAPI schema is at
`/api/schema/` and the interactive documentation is at `/api/docs/`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/requests/` | List requests visible to the authenticated user. |
| POST | `/requests/` | Submit a request with a category ID. |
| GET | `/requests/{id}/` | Retrieve a visible request. |
| PUT, PATCH | `/requests/{id}/` | Update editable request details. |
| PATCH | `/requests/{id}/change-status/` | Apply the next allowed status transition. |
| PATCH | `/requests/{id}/reclassify/` | Change the request's category and update its department. |
| GET | `/requests/{id}/history/` | Retrieve status and reclassification events. |
| GET | `/notifications/` | List the authenticated user's notifications. |
| PATCH | `/notifications/{id}/mark-read/` | Mark one of the user's notifications as read. |

The request list supports filtering by status, category, and department, text
search, and ordering by creation or update date. For example:
`/requests/?status=RESOLVED&search=pothole&ordering=-created_at`.

## Known limits

- Scheduled execution of the processor and delivery to external inboxes are
  still pending.
- The processor does not coordinate concurrent runs. If the mail backend accepts
  a message but the database update fails, a later attempt may send it again.
- Direct edits to requests in Django Admin do not use the API services that
  enforce transitions and write history and notifications.

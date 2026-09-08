# PZ IT Helpdesk

PZ IT Helpdesk is a Django-based internal IT support system used to manage user requests, approvals, assignments, comments, notifications, and service reporting.

## OOP & DBMS Concept Map

### Encapsulation
- `RequestService` encapsulates the business rules for the request lifecycle.
- Ticket actions such as `approve_request`, `reject_request`, `assign_request`, `start_work`, and `complete_work` are grouped behind a service layer instead of being spread across views.
- This keeps request logic consistent, testable, and easier to maintain.

### Inheritance
- `User` inherits from Django’s `AbstractUser` and adds project-specific fields and role logic.
- It provides role-based properties such as `is_employee`, `is_it_staff`, and `is_it_admin` to model behaviour without creating separate user tables.

### Polymorphism
- Role-based behaviour is represented through properties and `TextChoices`.
- The same request or dashboard logic can behave differently depending on the current user’s role.
- In practice, the same action endpoint may route to different paths depending on whether the actor is an employee, IT staff, or IT admin.

### Transactions
- The service layer uses Django transactions (`@transaction.atomic`) when multiple database operations must be treated as one unit.
- This ensures a request action like approving, assigning, or completing work does not leave partial data behind if an error occurs mid-process.

### Foreign keys and constraints
- Requests, updates, notifications, and history all rely on foreign keys to connect records to users and requests.
- `PROTECT` and `SET_NULL` constraints help preserve data integrity and prevent broken references.
- The app uses relational modelling to capture the whole support workflow and maintain traceability.

### Indexes and performance
- Frequently queried fields are indexed using `db_index=True` for faster lookups.
- Examples include `Request.status`, `Request.created_at`, `User.pzc`, `Notification.recipient`, and `RequestUpdate.request`.
- Views use `select_related` and `prefetch_related` to reduce repeated queries and avoid the N+1 problem.

### Aggregations and reporting
- Query aggregation is used in the statistics view to summarize ticket states and workload.
- Examples include counting requests by status, grouping by category, and calculating average resolution time using ORM expressions.
- These support operational reporting and statistical analysis without writing custom SQL.

### Migrations
- Django migrations track schema changes over time.
- They allow the project to evolve safely as new fields, indexes, or constraints are added without losing existing data.

## Database and Query Notes

The project uses Django’s ORM for most query work, with a service layer for the full business workflow. The most critical optimizations are:
- index on frequently filtered fields
- eager loading for request and notification pages
- aggregation for dashboard and statistics reporting

## Suggested next phase

After the OOP/DBMS phase, the next engineering phase is feature delivery:
- request numbering
- avatar upload
- attachments
- pagination
- production deployment settings

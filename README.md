# booking-system
COMP2140 Booking System Project
## Core Rules, Status, Business Hours, and Availability

What’s enforced now:
- Service.price > 0, Service.duration_minutes > 0 (validators)
- Booking cannot be in the past (serializer)
- Basic overlap prevention (per staff)
- Booking status: CONFIRMED/CANCELLED
  - Cancel endpoint sets status=Cancelled (no delete), keeps history

Business hours (configmgr):
- SystemSetting keys:
  - BUSINESS_OPEN (e.g., 09:00)
  - BUSINESS_CLOSE (e.g., 17:00)
- If not set, defaults to 09:00–17:00.

Staff availability (staff app):
- StaffAvailability model lets you store time windows when each staff can work.
- Availability endpoint includes a slot only if:
  - No availability rows exist for that staff (treated as available by default), OR
  - The slot fits entirely inside at least one availability window for that staff.

Test quickly:
1) Run:
   python manage.py runserver

2) Optional: Admin → SystemSetting:
   BUSINESS_OPEN=09:00, BUSINESS_CLOSE=17:00

3) Create data via API:
   - Service: POST /api/services/
   - Client:  POST /api/clients/
   - Staff:   POST /api/staff/

4) (Optional) Admin → StaffAvailability: add a window for your date

5) Check slots:
   GET /api/bookings/availability/?service=1&date=YYYY-MM-DD

6) Create booking:
   POST /api/bookings/ (status=CONFIRMED, confirmation prints to terminal)

7) Cancel booking:
   POST /api/bookings/{id}/cancel/ (status becomes CANCELLED, email prints)

Emails:
- Console email backend prints to the server terminal (free).
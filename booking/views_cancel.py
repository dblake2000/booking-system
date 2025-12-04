# booking/views_cancel.py
#
# Purpose:
# - Public "Cancel Booking" flow:
#   * GET  /bookings/cancel/        -> render the HTML form (non-API)
#   * POST /bookings/cancel/submit/ -> validate + cancel booking by rules
#
# Notes:
# - This view renders cancel_booking.html which you have placed at:
#     booking/templates/cancel_booking.html  (flat, no "booking/" subfolder)
# - If later you move the file under booking/templates/booking/cancel_booking.html,
#   change the render() call to "booking/cancel_booking.html".
#
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Booking
from .services.booking_manager import BookingManager


@require_http_methods(["GET"])
def cancel_booking_page(request):
    """
    Render the public cancellation page (HTML form).
    Template location:
    - Flat template path at: booking/templates/cancel_booking.html
    - IMPORTANT: we render "cancel_booking.html" (no "booking/" prefix)
    """
    return render(request, "cancel_booking.html")


@require_http_methods(["POST"])
def cancel_booking_action(request):
    """
    POST handler to cancel a booking.

    Expected form fields:
      - booking_id (required)
      - name       (required)
      - email      (required)
      - phone      (required) digits-only
      - reason     (optional) stored in notes

    Behavior:
      - Find booking by ID and verify name/email/phone match booking.client
      - Enforce business rule (e.g., 2-hour cutoff) using BookingManager
      - Set status="CANCELLED", set cancellation_time, append reason -> notes
      - notifications/signals.py will send emails on status change
    """
    booking_id = (request.POST.get("booking_id") or "").strip()
    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    reason = (request.POST.get("reason") or "").strip()

    # Validate required inputs in server (browser also validates)
    if not booking_id or not name or not email or not phone:
        return JsonResponse(
            {"ok": False, "message": "All required fields must be filled."},
            status=400,
        )

    # Phone: restrict to digits-only; keep validation in sync with booking flow
    if not phone.isdigit():
        return JsonResponse(
            {"ok": False, "message": "Phone must include digits only."},
            status=400,
        )

    # Parse booking ID as int
    try:
        bid_int = int(booking_id)
    except ValueError:
        return JsonResponse({"ok": False, "message": "Invalid Booking ID."}, status=400)

    # Find the booking or 404
    booking = get_object_or_404(Booking, pk=bid_int)

    # Confirm details match the booking record (case-insensitive for name/email; exact digits for phone)
    if booking.client.name.strip().lower() != name.lower():
        return JsonResponse(
            {"ok": False, "message": "Provided name does not match this booking."},
            status=400,
        )
    if booking.client.email.strip().lower() != email.lower():
        return JsonResponse(
            {"ok": False, "message": "Provided email does not match this booking."},
            status=400,
        )
    if (booking.client.phone or "").strip() != phone:
        return JsonResponse(
            {"ok": False, "message": "Provided phone does not match this booking."},
            status=400,
        )

    # Already cancelled?
    if booking.status == "CANCELLED":
        return JsonResponse(
            {"ok": False, "message": "This booking is already cancelled."},
            status=400,
        )

    # Enforce policy via BookingManager (e.g., 2-hour cutoff)
    manager = BookingManager()
    try:
        # Many implementations of cancel_booking will update status, etc.
        # We call it for policy; then ensure our fields are set for signals.
        manager.cancel_booking(booking, cutoff_minutes=120)

        # Ensure status/cancellation_time are set (if manager didn't do so)
        if hasattr(booking, "status") and booking.status != "CANCELLED":
            booking.status = "CANCELLED"
        if hasattr(booking, "cancellation_time") and booking.cancellation_time is None:
            booking.cancellation_time = timezone.now()

        # Optionally append reason to notes for staff visibility (non-destructive)
        if reason:
            booking.notes = (booking.notes or "") + f"\n[Cancel reason] {reason}"

        # Persist changes; signals on Booking post_save will send emails
        booking.save(update_fields=["status", "cancellation_time", "notes"])

        return JsonResponse({"ok": True, "message": "Your booking has been cancelled."})
    except ValueError as e:
        # Raised when violating business rule (e.g., within 2 hours cutoff)
        return JsonResponse({"ok": False, "message": str(e)}, status=400)
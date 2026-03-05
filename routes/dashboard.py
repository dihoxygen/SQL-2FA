# routes/dashboard.py
# The home page the user lands on after logging in.
# Shows three summary queues: my requests, assigned to me, needs approver.

from flask import Blueprint, render_template, session
from sqlalchemy import text
from db import sql2fa_engine
from helpers import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def home():
    """
    Runs three queries against the sql2fa schema and passes
    the results to the dashboard template.

    Each query returns a list of dictionaries (thanks to .mappings().all()).
    That means in the template you can write {{ row.request_id }}
    instead of {{ row[0] }}.
    """
    operator_id = session['operator_id']

    with sql2fa_engine.connect() as conn:

        # QUEUE 1: My Requests -- requests this operator created.
        # Only shows non-terminal statuses (not Executed, Cancelled, Manager DML).
        my_requests = conn.execute(
            text("""
                SELECT r.request_id, r.requestor_id, r.current_status, s.status as status_description,
                       r.current_requested_sql, r.request_created_on
                FROM sql2fa."REQUESTS" r
                JOIN sql2fa."STATUS_CODES" s ON r.current_status = s.status_code
                WHERE r.requestor_id = :op_id
                  AND r.current_status NOT IN ('C', 'M', 'S')
                ORDER BY r.request_created_on DESC
                LIMIT 10
            """),
            {"op_id": operator_id},
        ).mappings().all()

        # QUEUE 2: Assigned to me as approver -- requests waiting for my review.
        assigned_to_me = conn.execute(
            text("""
                SELECT r.request_id, r.requestor_id, r.current_status, s.status as status_description,
                       r.current_requested_sql, r.request_created_on
                FROM sql2fa."REQUESTS" r
                JOIN sql2fa."STATUS_CODES" s ON r.current_status = s.status_code
                WHERE r.assigned_approver = :op_id
                  AND r.current_status NOT IN ('C', 'M', 'S')
                ORDER BY r.request_created_on DESC
                LIMIT 10
            """),
            {"op_id": operator_id},
        ).mappings().all()

        # QUEUE 3: Needs approver -- unassigned requests anyone can pick up.
        # Excludes requests this operator created (can't approve your own).
        needs_approver = conn.execute(
            text("""
                SELECT request_id, requestor_id, current_requested_sql,
                       request_created_on
                FROM sql2fa."REQUESTS"
                WHERE assigned_approver IS NULL
                  AND current_status = 'Z'
                  AND requestor_id != :op_id
                ORDER BY request_created_on DESC
                LIMIT 10
            """),
            {"op_id": operator_id},
        ).mappings().all()

    return render_template(
        'dashboard.html',
        my_requests=my_requests,
        assigned_to_me=assigned_to_me,
        needs_approver=needs_approver,
    )

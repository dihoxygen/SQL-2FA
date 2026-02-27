# routes/open_requests.py
# Shows requests that have no approver assigned yet.
# Any operator can "accept" a request, which assigns them as the approver.

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import text
from db import sql2fa_engine
from helpers import login_required

open_requests_bp = Blueprint('open_requests', __name__)


@open_requests_bp.route('/open-requests')
@login_required
def list_open():
    """
    Shows all requests where assigned_approver IS NULL and status = 'Z'.
    These are requests waiting for someone to volunteer as approver.
    Excludes the current operator's own requests (you can't approve your own).
    """
    operator_id = session['operator_id']
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = """
        SELECT request_id, requestor_id, current_requested_sql,
               request_created_on, request_reason, request_potential_issues
        FROM sql2fa."REQUESTS"
        WHERE assigned_approver IS NULL
          AND current_status = 'Z'
          AND requestor_id != :op_id
    """
    params = {"op_id": operator_id}

    if date_from:
        query += " AND request_created_on >= :date_from"
        params["date_from"] = date_from
    if date_to:
        query += " AND request_created_on <= :date_to"
        params["date_to"] = date_to

    query += " ORDER BY request_created_on DESC"

    with sql2fa_engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()

    return render_template(
        'open_requests/list.html',
        rows=rows,
        date_from=date_from,
        date_to=date_to,
    )


@open_requests_bp.route('/open-requests/<request_id>')
@login_required
def accept_view(request_id):
    """
    Read-only view of a request. The potential approver can see all the
    details (SQL, purpose, issues) before deciding to accept.
    All fields are displayed but not editable.
    """
    with sql2fa_engine.connect() as conn:
        req = conn.execute(
            text('SELECT * FROM sql2fa."REQUESTS" WHERE request_id = :rid'),
            {"rid": request_id},
        ).mappings().fetchone()

    return render_template('open_requests/accept.html', req=req)


@open_requests_bp.route('/open-requests/<request_id>/accept', methods=['POST'])
@login_required
def accept(request_id):
    """
    The operator clicks "Accept Request".
    This calls assign_approver(), which:
      1. Sets assigned_approver to the current operator's ID.
      2. Changes the status to 'R' (Approver Review).
      3. Logs the event in REQUEST_EVENTS.

    After accepting, the request moves from "Open Requests" to
    "Approvals Assigned to Me" for this operator.
    """
    operator_id = session['operator_id']

    with sql2fa_engine.connect() as conn:
        conn.execute(
            text("SELECT sql2fa.assign_approver(:rid, :op_id, 'R')"),
            {"rid": request_id, "op_id": operator_id},
        )
        conn.commit()  # Without commit, the changes would be rolled back!

    flash('Request accepted! It now appears in your Approvals queue.', 'success')
    return redirect(url_for('approvals.assigned_to_me'))

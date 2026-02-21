# routes/approvals.py
# Handles the approver's workflow: viewing assigned requests,
# inspecting details, approving, and denying.

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import text
from db import sql2fa_engine
from helpers import login_required

approvals_bp = Blueprint('approvals', __name__)


@approvals_bp.route('/approvals')
@login_required
def assigned_to_me():
    """
    Lists all requests assigned to the current operator as approver.
    Similar to my_requests but filtered by assigned_approver instead of requestor_id.
    """
    operator_id = session['operator_id']
    status_filter = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = """
        SELECT request_id, requestor_id, current_status,
               current_requested_sql, request_created_on
        FROM sql2fa."REQUESTS"
        WHERE assigned_approver = :op_id
    """
    params = {"op_id": operator_id}

    if status_filter:
        query += " AND current_status = :status"
        params["status"] = status_filter
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
        'approvals/assigned_to_me.html',
        rows=rows,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


@approvals_bp.route('/approvals/<request_id>')
@login_required
def detail(request_id):
    """
    Approver detail view: shows the request info, full event history,
    and Approve/Deny buttons.

    The buttons are only shown when the status is "reviewable" --
    i.e., the request is waiting for the approver's decision.
    We check this by looking at the status code: if it's one of the
    statuses where a review decision makes sense (Z, R, EA, EJ, EP, B),
    we show the buttons.
    """
    with sql2fa_engine.connect() as conn:
        req = conn.execute(
            text('SELECT * FROM sql2fa."REQUESTS" WHERE request_id = :rid'),
            {"rid": request_id},
        ).mappings().fetchone()

        events = conn.execute(
            text("""
                SELECT * FROM sql2fa."REQUEST_EVENTS"
                WHERE request_id = :rid
                ORDER BY event_seq
            """),
            {"rid": request_id},
        ).mappings().all()

    # Statuses where the approver can make a decision.
    # These are statuses where the request is "in review" in some form.
    reviewable_statuses = ('Z', 'R', 'EA', 'EJ', 'EP', 'B')
    can_review = req['current_status'] in reviewable_statuses

    return render_template(
        'approvals/detail.html',
        req=req,
        events=events,
        can_review=can_review,
    )


@approvals_bp.route('/approvals/<request_id>/approve', methods=['GET', 'POST'])
@login_required
def approve(request_id):
    """
    GET  -> Show the approval form (just an Approval Notes textarea).
    POST -> Call approver_actions() with status 'A' (Approved).
    """
    operator_id = session['operator_id']

    if request.method == 'POST':
        notes = request.form.get('approver_notes', '')

        with sql2fa_engine.connect() as conn:
            conn.execute(
                text("SELECT sql2fa.approver_actions(:rid, :op_id, 'A', :notes)"),
                {"rid": request_id, "op_id": operator_id, "notes": notes},
            )
            conn.commit()

        flash('Request approved!', 'success')
        return redirect(url_for('approvals.detail', request_id=request_id))

    # GET: show the approval form
    return render_template('approvals/approve.html', request_id=request_id)


@approvals_bp.route('/approvals/<request_id>/deny', methods=['GET', 'POST'])
@login_required
def deny(request_id):
    """
    GET  -> Show the denial form (reason dropdown + notes textarea).
    POST -> Call denial_actions() with status 'D', the denial code, and notes.

    The denial_code comes from a dropdown with predefined reasons.
    This standardizes why things get denied so patterns can be identified.
    """
    operator_id = session['operator_id']

    if request.method == 'POST':
        denial_code = request.form['denial_code']
        denier_notes = request.form.get('denier_notes', '')

        with sql2fa_engine.connect() as conn:
            conn.execute(
                text("SELECT sql2fa.denial_actions(:rid, :op_id, 'D', :code, :notes)"),
                {
                    "rid": request_id,
                    "op_id": operator_id,
                    "code": denial_code,
                    "notes": denier_notes,
                },
            )
            conn.commit()

        flash('Request denied.', 'info')
        return redirect(url_for('approvals.detail', request_id=request_id))

    # GET: show the deny form
    return render_template('approvals/deny.html', request_id=request_id)

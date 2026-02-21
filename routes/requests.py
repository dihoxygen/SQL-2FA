from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import text
from db import sql2fa_engine, prod_engine
from helpers import login_required  # Shared decorator -- defined once in helpers.py

requests_bp = Blueprint('requests', __name__)


# ---------------------------------------------------------------------------
# Create New Request
# ---------------------------------------------------------------------------
@requests_bp.route('/requests/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        operator_id = session['operator_id']
        sql_text = request.form['dml_statement']
        target_date = request.form['target_date']

        with sql2fa_engine.connect() as conn:
            result = conn.execute(
                text("SELECT sql2fa.create_new_request(:requestor_id, :sql, 'Z', :target_date)"),
                {
                    "requestor_id": operator_id,
                    "sql": sql_text,
                    "target_date": target_date,
                }
            )
            request_id = result.scalar()
            conn.commit()

        return redirect(url_for('requests.confirmed', request_id=request_id))

    return render_template('requests/create.html')


# ---------------------------------------------------------------------------
# Confirmation after creating a request
# ---------------------------------------------------------------------------
@requests_bp.route('/requests/confirmed/<request_id>')
@login_required
def confirmed(request_id):
    return render_template('requests/confirmation.html', request_id=request_id)


# ---------------------------------------------------------------------------
# My Requests list (with optional filters)
# ---------------------------------------------------------------------------
@requests_bp.route('/requests/mine')
@login_required
def my_requests():
    operator_id = session['operator_id']
    status_filter = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = """
        SELECT request_id, current_status, current_requested_sql,
               request_created_on, requested_target_date
        FROM sql2fa."REQUESTS"
        WHERE requestor_id = :operator_id
    """
    params = {"operator_id": operator_id}

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
        'requests/my_requests.html',
        rows=rows,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# Requestor Detail View
# ---------------------------------------------------------------------------
@requests_bp.route('/requests/<request_id>')
@login_required
def detail(request_id):
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

        status_flags = conn.execute(
            text("""
                SELECT request_can_be_edited, request_can_be_cancelled, request_can_be_executed
                FROM sql2fa."STATUS_CODES"
                WHERE status_code = :code
            """),
            {"code": req["current_status"]},
        ).mappings().fetchone()

    return render_template(
        'requests/detail.html',
        req=req,
        events=events,
        can_edit=status_flags["request_can_be_edited"],
        can_cancel=status_flags["request_can_be_cancelled"],
        can_execute=status_flags["request_can_be_executed"],
    )


# ---------------------------------------------------------------------------
# Execute DML (the "2FA moment")
# ---------------------------------------------------------------------------
@requests_bp.route('/requests/<request_id>/execute', methods=['POST'])
@login_required
def execute(request_id):
    operator_id = session['operator_id']

    with sql2fa_engine.connect() as conn:
        result = conn.execute(
            text("SELECT sql2fa.execute_start(:rid, :op, 'E')"),
            {"rid": request_id, "op": operator_id},
        )
        dml_to_run = result.scalar()
        conn.commit()

    try:
        with prod_engine.connect() as prod_conn:
            exec_result = prod_conn.execute(text(dml_to_run))
            row_count = exec_result.rowcount
            prod_conn.commit()

        with sql2fa_engine.connect() as conn:
            result = conn.execute(
                text("SELECT sql2fa.execute_success(:rid, :op, :rc)"),
                {"rid": request_id, "op": operator_id, "rc": row_count},
            )
            conn.commit()

        flash(f"Execute DML Successful! Rows affected: {row_count}", "success")

    except Exception as e:
        with sql2fa_engine.connect() as conn:
            conn.execute(
                text("SELECT sql2fa.execute_failure(:rid, :exec_id, :reason, :eid, 'N')"),
                {
                    "rid": request_id,
                    "exec_id": None,
                    "reason": str(e),
                    "eid": None,
                },
            )
            conn.commit()

        flash(f"Error! There was an issue running the SQL: {e}", "error")

    return redirect(url_for('requests.detail', request_id=request_id))


# ---------------------------------------------------------------------------
# Edit DML
# ---------------------------------------------------------------------------
@requests_bp.route('/requests/<request_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(request_id):
    operator_id = session['operator_id']

    if request.method == 'POST':
        new_sql = request.form['dml_statement']
        edit_notes = request.form.get('edit_notes', '')

        with sql2fa_engine.connect() as conn:
            conn.execute(
                text("SELECT sql2fa.edit_actions(:rid, :op, 'EA', :sql, :notes)"),
                {
                    "rid": request_id,
                    "op": operator_id,
                    "sql": new_sql,
                    "notes": edit_notes,
                },
            )
            conn.commit()

        return redirect(url_for('requests.detail', request_id=request_id))

    with sql2fa_engine.connect() as conn:
        req = conn.execute(
            text('SELECT * FROM sql2fa."REQUESTS" WHERE request_id = :rid'),
            {"rid": request_id},
        ).mappings().fetchone()

    return render_template('requests/edit.html', req=req)


# ---------------------------------------------------------------------------
# Cancel DML
# ---------------------------------------------------------------------------
@requests_bp.route('/requests/<request_id>/cancel', methods=['POST'])
@login_required
def cancel(request_id):
    operator_id = session['operator_id']

    with sql2fa_engine.connect() as conn:
        conn.execute(
            text("SELECT sql2fa.edit_actions(:rid, :op, 'C')"),
            {"rid": request_id, "op": operator_id},
        )
        conn.commit()

    flash("Request cancelled.", "info")
    return redirect(url_for('requests.my_requests'))

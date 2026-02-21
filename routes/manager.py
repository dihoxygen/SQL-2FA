# routes/manager.py
# Manager oversight: a broad view of all requests across all operators,
# plus the ability to run Manager DML against prod.

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import text
from db import sql2fa_engine, prod_engine  # Manager DML also needs prod_engine
from helpers import login_required

manager_bp = Blueprint('manager', __name__)


@manager_bp.route('/manager')
@login_required
def manager_dashboard():
    """
    Shows ALL requests (not just the current operator's).
    Supports multiple filters: status, date range, search by ID.
    This is the broad oversight view from your wireframe.
    """
    status_filter = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search_id = request.args.get('search_id')

    query = """
        SELECT r.request_id, r.requestor_id, r.assigned_approver,
               r.current_status, r.current_requested_sql,
               r.request_created_on, r.requested_target_date
        FROM sql2fa."REQUESTS" r
        WHERE 1=1
    """
    # "WHERE 1=1" is a trick: it's always true, so it does nothing on its own.
    # But it lets every filter below start with "AND" uniformly,
    # so you don't need special logic for the first filter.
    params = {}

    if status_filter:
        query += " AND r.current_status = :status"
        params["status"] = status_filter
    if date_from:
        query += " AND r.request_created_on >= :date_from"
        params["date_from"] = date_from
    if date_to:
        query += " AND r.request_created_on <= :date_to"
        params["date_to"] = date_to
    if search_id:
        # CAST is needed because request_id is a UUID but the user
        # might type a partial string. Casting to text lets us use LIKE.
        query += " AND CAST(r.request_id AS text) LIKE :search_id"
        params["search_id"] = f"%{search_id}%"

    query += " ORDER BY r.request_created_on DESC"

    with sql2fa_engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()

    return render_template(
        'manager/dashboard.html',
        rows=rows,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        search_id=search_id,
    )


@manager_bp.route('/manager/<request_id>')
@login_required
def manager_detail(request_id):
    """
    Manager's detail view of any request. Shows the full audit trail.
    Has a "Run Manager DML" button.
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

    return render_template(
        'manager/detail.html',
        req=req,
        events=events,
    )


@manager_bp.route('/manager/<request_id>/dml', methods=['GET', 'POST'])
@login_required
def manager_dml(request_id):
    """
    GET  -> Show the Manager DML form (SQL textarea + reason textarea).
    POST -> Execute the manager's SQL against prod, then log it.

    This follows the same try/except pattern as the requestor's execute route:
    run the SQL on prod_engine, catch errors, log the result on sql2fa_engine.
    """
    if request.method == 'POST':
        manager_sql = request.form['manager_sql']
        reason = request.form.get('reason', '')

        try:
            # Run the manager's SQL against production
            with prod_engine.connect() as prod_conn:
                prod_conn.execute(text(manager_sql))
                prod_conn.commit()

            # Log the manager DML in the sql2fa schema
            with sql2fa_engine.connect() as conn:
                conn.execute(
                    text("""
                        SELECT sql2fa.execute_manager_dml(
                            :rid, :op_id, :sql, :reason, :exec_id
                        )
                    """),
                    {
                        "rid": request_id,
                        "op_id": session['operator_id'],
                        "sql": manager_sql,
                        "reason": reason,
                        "exec_id": None,
                    },
                )
                conn.commit()

            flash('Manager DML executed successfully.', 'success')

        except Exception as e:
            flash(f'Error executing Manager DML: {e}', 'error')

        return redirect(url_for('manager.manager_detail', request_id=request_id))

    # GET: show the form
    with sql2fa_engine.connect() as conn:
        req = conn.execute(
            text('SELECT * FROM sql2fa."REQUESTS" WHERE request_id = :rid'),
            {"rid": request_id},
        ).mappings().fetchone()

    return render_template('manager/dml_form.html', req=req)

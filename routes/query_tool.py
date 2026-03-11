import csv
import io
import json

import sqlparse
from flask import (
    Blueprint, Response, render_template, request, redirect,
    url_for, session, flash
)
from sqlalchemy import text

from db import prod_engine
from helpers import login_required

query_tool_bp = Blueprint('query_tool', __name__)

RESULT_LIMIT = 1000

OPERATOR_MAP = {
    'eq':      '=',
    'neq':     '!=',
    'lt':      '<',
    'gt':      '>',
    'lte':     '<=',
    'gte':     '>=',
    'in':      'IN',
    'not_in':  'NOT IN',
}

FORBIDDEN_KEYWORDS = {
    'INSERT', 'UPDATE', 'DELETE', 'MERGE',
    'DROP', 'ALTER', 'TRUNCATE', 'CREATE',
    'GRANT', 'REVOKE',
}


def _get_tables_metadata():
    """Return {table_name: [col1, col2, ...]} for the prod schema."""
    with prod_engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name, column_name "
            "FROM information_schema.columns "
            "WHERE table_schema = 'prod' "
            "ORDER BY table_name, ordinal_position"
        ))
        tables = {}
        for row in rows.mappings():
            tables.setdefault(row['table_name'], []).append(row['column_name'])
    return tables


def _validate_freeform_sql(sql_text):
    """Validate that sql_text is a single SELECT statement.

    Returns (is_valid, error_message).
    """
    stripped = sql_text.strip().rstrip(';').strip()
    if not stripped:
        return False, "SQL text is empty."

    statements = sqlparse.parse(stripped)
    if len(statements) == 0:
        return False, "Could not parse SQL."
    if len(statements) > 1:
        return False, "Only a single SQL statement is allowed."

    stmt = statements[0]
    stmt_type = stmt.get_type()
    if stmt_type not in ('SELECT', 'UNKNOWN'):
        return False, f"Only SELECT statements are allowed (detected: {stmt_type})."

    upper = stripped.upper()
    if not (upper.startswith('SELECT') or upper.startswith('WITH')):
        return False, "Statement must begin with SELECT or WITH (CTE)."

    for token in stmt.flatten():
        if token.ttype in (sqlparse.tokens.Keyword, sqlparse.tokens.Keyword.DDL,
                           sqlparse.tokens.Keyword.DML):
            word = token.value.upper()
            if word in FORBIDDEN_KEYWORDS:
                return False, f"Forbidden keyword detected: {word}."

    return True, None


def _build_table_query(table, columns, conditions, tables_meta):
    """Build a parameterised SELECT from table-selector inputs.

    Returns (sql_string, params_dict) or raises ValueError.
    """
    if table not in tables_meta:
        raise ValueError(f"Unknown table: {table}")

    valid_cols = set(tables_meta[table])
    for c in columns:
        if c not in valid_cols:
            raise ValueError(f"Invalid column for {table}: {c}")

    col_list = ', '.join(f'"{c}"' for c in columns)
    sql = f'SELECT {col_list} FROM prod."{table}"'
    params = {}

    if conditions:
        clauses = []
        for i, cond in enumerate(conditions):
            field = cond.get('field', '')
            op_key = cond.get('operator', '')
            value = cond.get('value', '')

            if field not in valid_cols:
                raise ValueError(f"Invalid condition field: {field}")
            if op_key not in OPERATOR_MAP:
                raise ValueError(f"Invalid operator: {op_key}")

            sql_op = OPERATOR_MAP[op_key]

            if op_key in ('in', 'not_in'):
                values = [v.strip() for v in value.split(',') if v.strip()]
                if not values:
                    raise ValueError("IN / NOT IN requires at least one value.")
                placeholders = []
                for j, v in enumerate(values):
                    key = f'val_{i}_{j}'
                    placeholders.append(f':{key}')
                    params[key] = v
                clauses.append(f'"{field}" {sql_op} ({", ".join(placeholders)})')
            else:
                key = f'val_{i}'
                params[key] = value
                clauses.append(f'"{field}" {sql_op} :{key}')

        sql += ' WHERE ' + ' AND '.join(clauses)

    sql += f' LIMIT {RESULT_LIMIT}'
    return sql, params


def _execute_readonly(sql_str, params=None):
    """Execute a read-only query against prod and return (columns, rows).

    Raises RuntimeError on failure.
    """
    with prod_engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        result = conn.execute(text(sql_str), params or {})
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchall()]
        conn.rollback()
    return columns, rows


# ── Page ─────────────────────────────────────────────────────────────

@query_tool_bp.route('/query-tool')
@login_required
def query_tool():
    tables_meta = _get_tables_metadata()
    return render_template(
        'query/query_tool.html',
        tables_meta=tables_meta,
        tables_json=json.dumps(tables_meta),
        columns=None,
        rows=None,
        active_tab='table',
        executed_sql='',
        export_params_json='',
    )


# ── Table Selector Execution ─────────────────────────────────────────

@query_tool_bp.route('/query-tool/execute-table', methods=['POST'])
@login_required
def execute_table():
    tables_meta = _get_tables_metadata()

    table = request.form.get('table', '')
    columns_raw = request.form.getlist('columns')
    conditions_json = request.form.get('conditions_json', '[]')

    if not table:
        flash('Please select a table.', 'error')
        return redirect(url_for('query_tool.query_tool'))

    if not columns_raw:
        flash('Please select at least one column.', 'error')
        return redirect(url_for('query_tool.query_tool'))

    try:
        conditions = json.loads(conditions_json)
    except json.JSONDecodeError:
        flash('Invalid conditions data.', 'error')
        return redirect(url_for('query_tool.query_tool'))

    try:
        sql_str, params = _build_table_query(table, columns_raw, conditions, tables_meta)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('query_tool.query_tool'))

    try:
        result_columns, result_rows = _execute_readonly(sql_str, params)
    except Exception as e:
        flash(f'Query error: {e}', 'error')
        return redirect(url_for('query_tool.query_tool'))

    export_params = {
        'mode': 'table',
        'table': table,
        'columns': columns_raw,
        'conditions': conditions,
    }

    return render_template(
        'query/query_tool.html',
        tables_meta=tables_meta,
        tables_json=json.dumps(tables_meta),
        columns=result_columns,
        rows=result_rows,
        active_tab='table',
        executed_sql=sql_str,
        export_params_json=json.dumps(export_params),
        selected_table=table,
        selected_columns=columns_raw,
        selected_conditions=conditions,
    )


# ── Freeform SQL Execution ───────────────────────────────────────────

@query_tool_bp.route('/query-tool/execute-freeform', methods=['POST'])
@login_required
def execute_freeform():
    tables_meta = _get_tables_metadata()
    sql_text = request.form.get('sql_text', '').strip()

    if not sql_text:
        flash('Please enter a SQL statement.', 'error')
        return redirect(url_for('query_tool.query_tool'))

    valid, error = _validate_freeform_sql(sql_text)
    if not valid:
        flash(error, 'error')
        return render_template(
            'query/query_tool.html',
            tables_meta=tables_meta,
            tables_json=json.dumps(tables_meta),
            columns=None,
            rows=None,
            active_tab='freeform',
            executed_sql='',
            export_params_json='',
            freeform_sql=sql_text,
        )

    limited = sql_text.rstrip(';').strip()
    upper = limited.upper()
    if 'LIMIT' not in upper.split('--')[0].split('/*')[0]:
        limited += f' LIMIT {RESULT_LIMIT}'

    try:
        result_columns, result_rows = _execute_readonly(limited)
    except Exception as e:
        flash(f'Query error: {e}', 'error')
        return render_template(
            'query/query_tool.html',
            tables_meta=tables_meta,
            tables_json=json.dumps(tables_meta),
            columns=None,
            rows=None,
            active_tab='freeform',
            executed_sql='',
            export_params_json='',
            freeform_sql=sql_text,
        )

    export_params = {
        'mode': 'freeform',
        'sql_text': sql_text,
    }

    return render_template(
        'query/query_tool.html',
        tables_meta=tables_meta,
        tables_json=json.dumps(tables_meta),
        columns=result_columns,
        rows=result_rows,
        active_tab='freeform',
        executed_sql=limited,
        export_params_json=json.dumps(export_params),
        freeform_sql=sql_text,
    )


# ── CSV Export ───────────────────────────────────────────────────────

@query_tool_bp.route('/query-tool/export', methods=['POST'])
@login_required
def export_csv():
    export_json = request.form.get('export_params', '{}')
    try:
        export_params = json.loads(export_json)
    except json.JSONDecodeError:
        flash('Invalid export parameters.', 'error')
        return redirect(url_for('query_tool.query_tool'))

    mode = export_params.get('mode')

    try:
        if mode == 'table':
            tables_meta = _get_tables_metadata()
            sql_str, params = _build_table_query(
                export_params['table'],
                export_params['columns'],
                export_params.get('conditions', []),
                tables_meta,
            )
            result_columns, result_rows = _execute_readonly(sql_str, params)
        elif mode == 'freeform':
            sql_text = export_params.get('sql_text', '')
            valid, error = _validate_freeform_sql(sql_text)
            if not valid:
                flash(error, 'error')
                return redirect(url_for('query_tool.query_tool'))
            limited = sql_text.rstrip(';').strip()
            upper = limited.upper()
            if 'LIMIT' not in upper.split('--')[0].split('/*')[0]:
                limited += f' LIMIT {RESULT_LIMIT}'
            result_columns, result_rows = _execute_readonly(limited)
        else:
            flash('Unknown export mode.', 'error')
            return redirect(url_for('query_tool.query_tool'))
    except Exception as e:
        flash(f'Export error: {e}', 'error')
        return redirect(url_for('query_tool.query_tool'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(result_columns)
    writer.writerows(result_rows)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=query_results.csv'},
    )

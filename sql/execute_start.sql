CREATE OR REPLACE FUNCTION sql2fa.execute_start (
    req_request_id uuid,
    r_requestor_id char(4),
    execute_status sql2fa.status_codes,
    OUT execute_sql text -- returns sql text to be used in application logic (and hence the prod table)
)
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE prev_sql text; execute_sql text;

BEGIN

    --GENERATE EXECUTE_ID

    --RETURN PREVIOUS SQL INTO PREV_SQL VARIABLE TO USE IN REQUEST_EVENTS
    SELECT
        current_requested_sql INTO prev_sql
    WHERE request_id = req_request_id;

    --UPDATE STATUS AND NEW SQL
    UPDATE sql2fa."REQUESTS"
    SET
        current_status = execute_status,
        execute_id = execute_id
    WHERE
        request_id = req_request_id
    RETURNING current_requested_sql, prev_requested_sql INTO execute_sql, prev_sql; --passing execute_sql to be used in request_events

    --LOG EDIT
    INSERT INTO sql2fa."REQUEST_EVENTS" (
        request_id,
        event_seq,
        current_status,
        status_change_dt,
        prev_sql_text,
        current_sql_text,
        status_changed_by_operator_id
    )
    VALUES
    (
        req_request_id,
        (select coalesce(max(event_seq), 0) + 1 from sql2fa."REQUEST_EVENTS" 
        where request_id = req_request_id),
        execute_status,
        now(),
        prev_sql,
        execute_sql,
        edit_notes,
        r_requestor_id
    );

END;
$$;

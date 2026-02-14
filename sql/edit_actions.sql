CREATE OR REPLACE FUNCTION sql2fa.edit_actions (
    req_request_id uuid,
    r_requestor_id char(4),
    requestor_action sql2fa.status_codes,
    new_sql text,
    edit_notes text DEFAULT ' '
) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE prev_sql text;
    curr_sql text;

BEGIN

    --RETURN PREVIOUS SQL INTO PREV_SQL VARIABLE TO USE IN REQUEST_EVENTS
    SELECT
        current_requested_sql INTO prev_sql
    FROM sql2fa."REQUESTS"
    WHERE request_id = req_request_id;

    --UPDATE STATUS AND NEW SQL
    UPDATE sql2fa."REQUESTS"
    SET
        current_status = requestor_action,
        current_requested_sql = new_sql --Setting Current_requested_sql as argument passed in function call
    WHERE
        request_id = req_request_id
    RETURNING current_requested_sql INTO curr_sql; --passing curr_sql to be used in request_events

    --LOG EDIT
    INSERT INTO sql2fa."REQUEST_EVENTS" (
        request_id,
        event_seq,
        current_status,
        status_change_dt,
        prev_sql_text,
        current_sql_text,
        requestor_edit_notes,
        status_changed_by_operator_id
    )
    VALUES
    (
        req_request_id,
        (select coalesce(max(event_seq), 0) + 1 from sql2fa."REQUEST_EVENTS" 
        where request_id = req_request_id),
        requestor_action,
        now(),
        prev_sql,
        curr_sql,
        edit_notes,
        r_requestor_id
    );

END;
$$;

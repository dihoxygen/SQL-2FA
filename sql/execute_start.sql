CREATE OR REPLACE FUNCTION sql2fa.execute_start (
    req_request_id uuid,
    r_requestor_id char(4),
    execute_status sql2fa.status_codes,
    OUT execute_sql text, -- returns the sql text to be used in the application logic
    OUT exec_id uuid --returns the execute_id to be used in the application logic
)
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/

/*Variables*/
DECLARE prev_sql text;

BEGIN

    exec_id := gen_random_uuid();

    --UPDATE STATUS AND ASSIGN EXECUTE_ID
    UPDATE sql2fa."REQUESTS"
    SET
        current_status = execute_status,
        execute_id = exec_id
    WHERE
        request_id = req_request_id
    RETURNING current_requested_sql INTO execute_sql;

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
        (select prev_sql_text from sql2fa."REQUEST_EVENTS" WHERE request_id = req_request_id order by event_seq desc limit 1),
        execute_sql,
        r_requestor_id
    );

END

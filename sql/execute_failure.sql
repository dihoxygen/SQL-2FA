CREATE OR REPLACE FUNCTION sql2fa.execute_failure (
    req_request_id uuid,
    reason_for_failure text,
    fail_status sql2fa.status_codes,
    execute_uuid uuid -- the execute_id of the request created in the execute_start function
)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE curr_sql text;
BEGIN

    UPDATE sql2fa."REQUESTS"
    SET
        current_status = fail_status
    WHERE
        request_id = req_request_id
    RETURNING current_requested_sql INTO curr_sql;



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
        fail_status,
        now(),
        (select current_sql_text 
        from sql2fa."REQUEST_EVENTS"
        where request_id = req_request_id
        order by event_seq DESC
        limit 1),
        curr_sql,
        'SYST'
    );


    INSERT INTO sql2fa."REQUEST_EXECUTIONS" (
        request_id,
        execute_id,
        counter,
        error_message
    )
    VALUES
    (
        req_request_id,
        execute_uuid,
        (select coalesce(max(counter), 0) + 1 from sql2fa."REQUEST_EXECUTIONS" where request_id = req_request_id),
        reason_for_failure
    );
END;
$$;

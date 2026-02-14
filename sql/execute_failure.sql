CREATE OR REPLACE FUNCTION sql2fa.execute_failure (
    OUT req_request_id uuid,
    exec_id uuid,
    reason_for_failure text,
    OUT execute_id uuid,
    fail_status sql2fa.status_codes
)
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE curr_sql text;
BEGIN

    --UPDATE REQUEST STATUS TO FAILURE: CODE = N
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
        current_requested_sql,
        status_changed_by_operator_id
    )
    VALUES
    (
        req_request_id,
        (select coalesce(max(event_seq), 0) + 1 from sql2fa."REQUEST_EVENTS" 
        where request_id = req_request_id),
        fail_status,
        now(),
        (select prev_sql_text 
        from sql2fa."REQUEST_EVENTS"
        where request_id = req_request_id
        order by event_seq DESC
        limit 1),
        curr_sql,
        'SYST' -- SYST IS THE DEFAULT OPERATOR ID FOR SYSTEM-GENERATED EVENTS
    );

END;
$$;

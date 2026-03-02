CREATE OR REPLACE FUNCTION sql2fa.execute_success (
    req_request_id uuid,
    execute_uuid uuid,
    r_requestor_id char(4),
    record_count int,
    success_status sql2fa.status_codes,
    manager_dml text DEFAULT ' ',
    reason_for_manager_dml text DEFAULT ' '
)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE curr_sql text;
BEGIN

    UPDATE sql2fa."REQUESTS"
    SET
        execute_id = execute_uuid,
        current_status = success_status
    WHERE
        request_id = req_request_id
    RETURNING current_requested_sql INTO curr_sql;

    INSERT INTO sql2fa."REQUEST_EXECUTIONS" (
        request_id,
        execute_id,
        counter,
        execute_record_count,
        manager_dml,
        reason_for_manager_dml,
        date_executed
    )
    VALUES
    (
        req_request_id,
        execute_uuid,
        (select coalesce(max(counter), 0) + 1 from sql2fa."REQUEST_EXECUTIONS" 
        where execute_id = execute_uuid),
        record_count,
        manager_dml,
        reason_for_manager_dml,
        CURRENT_DATE
    );

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
        success_status,
        now(),
        (select current_sql_text 
        from sql2fa."REQUEST_EVENTS"
        where request_id = req_request_id
        order by event_seq DESC
        limit 1),
        curr_sql,
        r_requestor_id
    );

END;
$$;

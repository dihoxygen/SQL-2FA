CREATE OR REPLACE FUNCTION sql2fa.execute_success (
    OUT req_request_id uuid,
    r_requestor_id char(4),
    record_count int,
    manager_dml text DEFAULT ' ',
    reason_for_manager_dml text DEFAULT ' ',
    OUT execute_id uuid -- returns sql text to be used in application logic (and hence the prod table)
)
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE exec_id uuid;

BEGIN

    --GENERATE EXECUTE_ID
    execute_id := gen_random_uuid();

    UPDATE sql2fa."REQUESTS"
    SET
        execute_id = execute_id
    WHERE
        request_id = req_request_id
    RETURNING execute_id INTO exec_id;

    --INSERT INTO EXECUTION_EVENTS
    INSERT INTO sql2fa."REQUEST_EVENTS" (
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
        exec_id,
        (select coalesce(max(event_seq), 0) + 1 from sql2fa."EXECUTION_EVENTS" 
        where excute_id = execute_id),
        record_count,
        manager_dml,
        reason_for_manager_dml,
        trunc(now())
    );

END;
$$;

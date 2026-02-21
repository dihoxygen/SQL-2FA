CREATE OR REPLACE FUNCTION sql2fa.create_new_request (
    c_requestor_id character(4),
    c_current_requested_sql text,
    c_current_status sql2fa.status_codes,
    c_requested_target_date date
) RETURNS uuid --storing uuid created in new request to populate related table
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE c_request_id uuid; c_op_changed_by char(4);

BEGIN

    --REQUESTS
    INSERT INTO sql2fa."REQUESTS" (
        requestor_id,
        current_requested_sql,
        current_status,
        request_created_on,
        requested_target_date
    )
    VALUES (
        c_requestor_id,
        UPPER(TRIM(c_current_requested_sql)), --UPPER() AND TRIM FUNCTION TO STANDARDIZE SQL
        c_current_status,
        now(),
        c_requested_target_date
    )
    RETURNING request_id, requestor_id INTO c_request_id, c_op_changed_by;

    --REQUEST_EVENTS
    INSERT INTO sql2fa."REQUEST_EVENTS" (
        request_id,
        event_seq,
        current_status,
        status_change_dt,
        prev_sql_text,
        current_sql_text,
        status_changed_by_operator_id
    )
    VALUES (
        c_request_id,
        0,
        c_current_status,
        now(),
        ' ',
        UPPER(TRIM(c_current_requested_sql)),
        c_requestor_id
    );

    RETURN c_request_id;
    
END;
$$;

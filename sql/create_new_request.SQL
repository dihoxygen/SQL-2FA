CREATE OR REPLACE FUNCTION sql2fa.create_new_request (
    c_requestor_id character(4),
    c_current_requested_sql text,
    c_current_status sql2fa.status_codes,
    c_requested_target_date date,
    c_request_reason text,
    c_request_potential_issues text
) RETURNS uuid --storing uuid created in new request to populate related table
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE c_request_id uuid; c_op_changed_by character(4);
BEGIN

    --REQUESTS
    INSERT INTO sql2fa."REQUESTS" (
        requestor_id,
        current_requested_sql,
        current_status,
        request_created_on,
        requested_target_date,
        request_reason,
        request_potential_issues
    )
    VALUES (
        c_requestor_id,
        UPPER(TRIM(c_current_requested_sql)), --UPPER() AND TRIM FUNCTION TO STANDARDIZE SQL
        c_current_status,
        now(),
        c_requested_target_date,
        c_request_reason,
        c_request_potential_issues
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
        ' ', --default value for initial event, can be updated when status changes
        UPPER(TRIM(c_current_requested_sql)),
        c_requestor_id
    ); --need to change this datatype to default ' '

    RETURN c_request_id;
    
END;
$$;

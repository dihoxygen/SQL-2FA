CREATE OR REPLACE FUNCTION sql2fa.assign_approver (
    a_request_id uuid,
    a_approver_id char(4),
    a_current_status sql2fa.status_codes
) RETURNS void --storing uuid created in new request to populate related table
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE curr_sql text;

BEGIN

    --REQUESTS
    UPDATE sql2fa."REQUESTS"
    SET
        assigned_approver = a_approver_id,
        current_status = a_current_status
    WHERE
        request_id = a_request_id
    RETURNING current_requested_sql INTO curr_sql;

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
        a_request_id,
        (select coalesce(max(event_seq),0)+1 from sql2fa."REQUEST_EVENTS" where request_id = a_request_id),
        a_current_status,
        now(),
        (select prev_sql_text from sql2fa."REQUEST_EVENTS"
        where request_id = req_request_id
        order by event_seq DESC
        limit 1),
        curr_sql,
        a_approver_id
    );

END;
$$;

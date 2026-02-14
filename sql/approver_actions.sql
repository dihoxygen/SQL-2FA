CREATE OR REPLACE FUNCTION sql2fa.approver_actions (
    req_request_id uuid,
    a_approver_id char(4),
    approver_decision sql2fa.status_codes,
    a_approver_notes text DEFAULT ' '
) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
/*Variables*/
DECLARE curr_sql text;

BEGIN

    --STATUS UPDATE
    UPDATE sql2fa."REQUESTS"
    SET
        current_status = approver_decision
    WHERE
        request_id = req_request_id
    RETURNING current_requested_sql INTO curr_sql;

    --LOG APPROVAL
    /*Enforce Approval Status Logic in the application logic*/
    INSERT INTO sql2fa."REQUEST_EVENTS" (
        request_id,
        event_seq,
        current_status,
        status_change_dt,
        prev_sql_text,
        current_sql_text,
        approver_notes,
        status_changed_by_operator_id
    )
    VALUES (
        req_request_id,
        (select coalesce(max(event_seq),0)+1 from sql2fa."REQUEST_EVENTS" where request_id = req_request_id),
        approver_decision,
        now(),
        (select prev_sql_text from sql2fa."REQUEST_EVENTS"
        where request_id = req_request_id
        order by event_seq DESC
        limit 1),
        curr_sql,
        a_approver_notes,
        a_approver_id
    );

END;
$$;

create or replace function sql2fa.execute_failure (
    out req_request_id uuid,
    exec_id uuid,
    reason_for_failure text,
    out execute_id uuid,
    fail_status sql2fa.status_codes
)
language plpgsql security definer as $$
/*Variables*/
declare curr_sql text;
begin
   
    --UPDATE REQUEST STATUS TO FAILURE: CODE = N
    update sql2fa."REQUESTS"
    set
        current_status = fail_status
    where
        request_id = req_request_id
        returning current_requested_sql into curr_sql;

    insert into sql2fa."REQUEST_EVENTS" (
        request_id,
        event_seq,
        current_status,
        status_change_dt,
        prev_sql_text,
        current_requested_sql,
        status_changed_by_operator_id
    )
    values
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
end;
$$;
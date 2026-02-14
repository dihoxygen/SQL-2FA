create
or replace function sql2fa.edit_actions (
    req_request_id uuid,
    r_requestor_id char(4),
    requestor_action sql2fa.status_codes,
    cancel_notes text default ' '
) returns void language plpgsql security definer as $$
/*Variables*/
declare curr_sql text;

begin
--STATUS UPDATE
update sql2fa."REQUESTS"
set
    current_status = requestor_action
where
    request_id = req_request_id returning current_requested_sql into curr_sql;

--passing curr_sql to be used in request_events
--LOG CANCELLATION
insert into
    sql2fa."REQUEST_EVENTS" (
        request_id,
        event_seq,
        current_status,
        status_change_dt,
        old_sql_text,
        new_sql_text,
        requestor_edit_notes,
        status_changed_by_operator_id
    )
values
    (
        req_request_id,
        (select coalesce(max(event_seq), 0) + 1 from sql2fa."REQUEST_EVENTS" 
        where request_id = req_request_id),
        requestor_action,
        now (),
        (select prev_sql_text from sql2fa."REQUEST_EVENTS"
        where request_id = req_request_id
        order by event_seq DESC
        limit 1),
        curr_sql,
        edit_notes,
        r_requestor_id
    );

end;$$
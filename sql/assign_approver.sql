create or replace function sql2fa.assign_approver(a_request_id uuid, a_approver_id char(4), a_current_status sql2fa.status_codes)

returns void --storing uuid created in new request to populate related table
language plpgsql
security definer as $$
declare curr_sql text;

/*Variables*/
declare curr_sql text;
begin
    --REQUESTS 
    update sql2fa."REQUESTS"
    set assigned_approver= a_approver_id, current_status = a_current_status
    where request_id = a_request_id
    returning current_requested_sql into curr_sql;


    --REQUEST_EVENTS
    insert into sql2fa."REQUEST_EVENTS" (request_id, event_seq, current_status, status_change_dt, old_sql_text, status_changed_by_operator_id)
    values (a_request_id, (select coalesce(max(event_seq),0)+1 from sql2fa."REQUEST_EVENTS" where request_id = a_request_id), a_current_status, now(), curr_sql, a_approver_id);

end;

$$

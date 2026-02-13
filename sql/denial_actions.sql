create or replace function sql2fa.denial_actions(req_request_id uuid, a_approver_id char(4), approver_decision sql2fa.status_codes, 
d_denial_code varchar, d_denier_notes text)
returns void
language plpgsql
security definer as $$
/*Variables*/
declare curr_sql text;

begin
    --STATUS UPDATE
    update sql2fa."REQUESTS"
    set current_status = approver_decision
    where request_id = req_request_id
    returning current_requested_sql into curr_sql;


    --LOG DENIAL 
    /*Denial reasons and Denier Notes should be enforced with this status in the application logic*/
    insert into sql2fa."REQUEST_EVENTS" (request_id, event_seq, current_status, status_change_dt, old_sql_text, denial_code, denier_notes, status_changed_by_operator_id)
    values (req_request_id, (select coalesce(max(event_seq),0)+1 from sql2fa."REQUEST_EVENTS" where request_id = req_request_id), approver_decision, now(), curr_sql,
    d_denial_code, d_denier_notes, a_approver_id);


end; $$






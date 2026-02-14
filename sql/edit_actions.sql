create or replace function sql2fa.edit_actions(
    req_request_id uuid, 
    r_requestor_id char(4), 
    requestor_action sql2fa.status_codes, 
    new_sql text, 
    edit_notes text default ' '
) returns void language plpgsql security definer as $$
/*Variables*/
declare prev_sql text; curr_sql text;

begin
    --RETURN PREVIOUS SQL INTO PREV_SQL VARIABLE TO USE IN REQUEST_EVENTS
    select current_requested_sql
    into prev_sql
    where request_id = req_request_id;
    --UPDATE STATUS AND NEW SQL
    update sql2fa."REQUESTS"
    set current_status = requestor_action, current_requested_sql = new_sql --Setting Current_requested_sql as argument passed in function call
    where request_id = req_request_id
    returning current_requested_sql into curr_sql; --passing curr_sql to be used in request_events

    --LOG EDIT
    insert into sql2fa."REQUEST_EVENTS" (request_id, event_seq, current_status, status_change_dt, old_sql_text, new_sql_text, requestor_edit_notes, status_changed_by_operator_id)
    values (req_request_id, (select coalesce(max(event_seq),0)+1 from sql2fa."REQUEST_EVENTS" where request_id = req_request_id), requestor_action, now(), prev_sql, curr_sql,
    edit_notes, r_requestor_id);


end; $$
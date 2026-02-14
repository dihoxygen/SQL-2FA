create or replace function sql2fa.create_new_request (
  c_requestor_id character(4),
  c_current_requested_sql text,
  c_current_status sql2fa.status_codes,
  c_requested_target_date date
) returns void --storing uuid created in new request to populate related table
language plpgsql security definer as $$
/*Variables*/
declare c_request_id uuid; c_op_changed_by char(4);

begin
--REQUESTS
insert into sql2fa."REQUESTS" (requestor_id, current_requested_sql, current_status, request_created_on, requested_target_date)
values (c_requestor_id, UPPER(TRIM(c_current_requested_sql)), c_current_status, now(), c_requested_target_date)--UPPER() AND TRIM FUNCTION TO STANDARDIZE SQL
returning request_id, requestor_id into c_request_id, c_op_changed_by;
--REQUEST_EVENTS
insert into sql2fa."REQUEST_EVENTS" (request_id, event_seq, current_status, status_change_dt, current_sql_text, status_changed_by_operator_id)
values (c_request_id, 0, c_current_status, now(), UPPER(TRIM(c_current_requested_sql)), c_requestor_id);--need to change this datatype to default ' '

end;
$$

create
or replace function sql2fa.execute_success (
    out req_request_id uuid,
    r_requestor_id char(4),
    record_count int,
    manager_dml text default ' ',
    reason_for_manager_dml text default ' ',
    out execute_id uuid-- returns sql text to be used in application logic (and hence the prod table)
)   language plpgsql security definer as $$
/*Variables*/
declare exec_id uuid;

begin

--GENERATE EXECUTE_ID
    execute_id := gen_random_uuid();


    update sql2fa."REQUESTS"
    set
        execute_id = execute_id
    where
        request_id = req_request_id
    returning execute_id into exec_id;


    --INSERT INTO EXECUTION_EVENTS
    insert into sql2fa."REQUEST_EVENTS" (
        request_id,
        execute_id,
        counter,
        execute_record_count,
        manager_dml,
        reason_for_manager_dml,
        date_executed

    )
    values
    (   req_request_id,
        exec_id,
        (select coalesce(max(event_seq), 0) + 1 from sql2fa."EXECUTION_EVENTS" 
        where excute_id = execute_id),
        record_count,
        manager_dml,
        reason_for_manager_dml,
        trunc(now())
        );

end;

$$
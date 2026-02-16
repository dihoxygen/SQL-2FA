/*For the purpose of this MVP, the manager DML is only used to log what the 
manager DML would've been executed if this process was implemented in the system.
However for this MVP, we will give manager read_write access to write to prod. 
*/
create or replace function sql2fa.execute_manager_dml(
    req_request_id uuid,
    r_requestor_id char(4),
    manager_dml text,
    reason_for_manager_dml text,
    OUT execute_id uuid -- returns sql text to be used in application logic (and hence the prod table)
)
returns void
language plpgsql security definer as $$
begin
    -- execute the manager dml
    execute manager_dml;
end;

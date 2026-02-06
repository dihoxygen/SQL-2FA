/*SQL 2FA - SQL Functions*/
---BODY OF FUNTIONS HANDLED BY SUPABASE---

-- CREATE NEW REQUEST RECORD
BEGIN
INSERT INTO sql2fa."REQUESTS" (requestor_id, requestor_manager, current_requested_sql, current_status,
request_created_on, requested_target_date)

VALUES (new.requestor_id, new.requestor_manager, new.current_requested_sql, new.current_status, new.request_created_on, new.requested_target_date);

RETURN new;


END;

-- ADD NEW EVENT
BEGIN
  IF (TG_OP = 'INSERT') THEN

    INSERT INTO sql2fa."REQUESTS" (requestor_id, requestor_manager, current_requested_sql, current_status,
    request_created_on, requested_target_date)

    VALUES (new.requestor_id, new.requestor_manager, new.current_requested_sql, new.current_status, new.request_created_on, new.requested_target_date);
    RETURN NEW;

  IF (TG_OP = 'UPDATE')
END;
-- 

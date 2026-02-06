/*
-- SQL 2FA CHANGE SCHEMA 
*/

/*UUID Generator*/

create extension if not exists pgcrypto;

/*Types*/
CREATE TYPE denial as ENUM ('SQL incorrectly written', 'Change will impact production process', 'Unclear/Unneccessary business need', 'Other');
CREATE TYPE status_codes as ENUM ('Z', 'R', 'A', 'E', 'M', 'C', 'D', 'B', 'EA', 'EJ', 'EP', 'AR', 'N');
CREATE TYPE status_descriptions as ENUM ('Requested', 'Approver Review (Review)', 'Approved', 'Executed', 'Manager DML Executed', 'Canceled', 'Denied', 'Denial Edit (Review)', 'Edit for Review with Approver (Review)'
, 'Edit for Review with No Approver (Review)', 'Edit Post Approval (Review)', 'Approval for Edited Request', 'Error Executing (Review Status)');
/*Tables*/


CREATE TABLE "REQUESTS" (
  "request_id" uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
  "requestor_id" char(4) NOT NULL,
  "assigned_approver" char(4), --nullable since requests can be generated without an assigned approver
  "requestor_manager" char(4), --nullable since some managers may not have an assigned manager. Not indicative of a realistic system but fits this system
  "current_requested_sql" text NOT NULL,
  "current_status" status_codes NOT NULL,
  "request_created_on" timestamptz NOT NULL DEFAULT now(),
  "requested_target_date" date,
  "canceled_notes" text
);

CREATE TABLE "Denial_Reasons" (
  "reason_id" denial PRIMARY KEY NOT NULL,
  "reason_category" varchar,
  "reason_label" varchar,
  "reason_description" text,
  "is_active" boolean
);

CREATE TABLE "REQUEST_EVENTS" (
  "request_id" uuid NOT NULL,
  "event_seq" int,
  "current_status" status_codes, 
  "status_change_dt" timestamptz NOT NULL DEFAULT now(),
  "old_sql_text" text NOT NULL, --since every request has a sql required then this too must be not nullable
  "new_sql_text" text,
  "approver_notes" text,
  "denial_reason" denial,
  "denier_notes" text,
  "requestor_edit_notes" text,
  "status_changed_by_operator_id" char(4) NOT NULL,
  "error_msg" text,
  PRIMARY KEY ("request_id", "event_seq"
));

CREATE TABLE "STATUS_CODES" (
  "status_code" status_codes PRIMARY KEY,
  "status" status_descriptions,
  "request_can_be_edited" boolean,
  "request_can_be_canceled" boolean,
  "request_can_be_executed" boolean
);

CREATE TABLE "OPERATOR" (
  "operator_id" char(4) PRIMARY KEY,
  "title" varchar(60),
  "operator_fname" varchar(24),
  "operator_lname" varchar(24),
  "password_hash" text,
  "manager_id" char(4)
);

CREATE TABLE "REQUEST_EXECUTIONS" (
  "request_id" uuid,
  "execute_id" uuid,
  "counter" int,
  "execute_record_count" int,
  "manager_dml" text,
  "reason_for_manager_dml" text,
  "date_executed" date,
  PRIMARY KEY ("request_id", "execute_id", "counter")
);

ALTER TABLE "REQUEST_EVENTS" ADD FOREIGN KEY ("request_id") REFERENCES "REQUESTS" ("request_id");

ALTER TABLE "REQUESTS" ADD FOREIGN KEY ("requestor_id") REFERENCES "OPERATOR" ("operator_id");

ALTER TABLE "REQUESTS" ADD FOREIGN KEY ("assigned_approver") REFERENCES "OPERATOR" ("operator_id");

ALTER TABLE "REQUESTS" ADD FOREIGN KEY ("current_status") REFERENCES "STATUS_CODES" ("status_code");

ALTER TABLE "REQUEST_EVENTS" ADD FOREIGN KEY ("current_status") REFERENCES "STATUS_CODES" ("status_code");

ALTER TABLE "OPERATOR" ADD FOREIGN KEY ("manager_id") REFERENCES "OPERATOR" ("operator_id");

ALTER TABLE "REQUEST_EXECUTIONS" ADD FOREIGN KEY ("request_id") REFERENCES "REQUESTS" ("request_id");

ALTER TABLE "REQUEST_EVENTS" ADD FOREIGN KEY ("denial_reason") REFERENCES "Denial_Reasons" ("reason_id");

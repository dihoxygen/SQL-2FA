-- ==========================================
-- Production-like schema in `prod` (PostgreSQL)
-- ==========================================

create schema if not exists prod;

-- ----------------------------
-- Lookup tables
-- ----------------------------

create table if not exists prod.acct_type (
  code         varchar(2) primary key,
  description  text,
  to_acct_type varchar(2),
  constraint acct_type_to_acct_type_fk
    foreign key (to_acct_type) references prod.acct_type(code)
);

create table if not exists prod.record_type (
  code        varchar(2) primary key,
  description text
);

create table if not exists prod.tran_code (
  code        char(6)     not null,
  acct_type   varchar(2)  not null,
  record_type varchar(2)  not null,
  description text,
  posting_tc  char(6),
  constraint tran_code_pk primary key (code, acct_type, record_type),
  constraint tran_code_acct_type_fk foreign key (acct_type) references prod.acct_type(code),
  constraint tran_code_record_type_fk foreign key (record_type) references prod.record_type(code)
);

create table if not exists prod.account_master (
  account_number char(18)   not null,
  acct_type      varchar(2) not null,
  holder_fname   text,
  holder_lname   text,
  constraint account_master_pk primary key (account_number, acct_type),
  constraint account_master_acct_type_fk foreign key (acct_type) references prod.acct_type(code)
);

-- ----------------------------
-- Fact table
-- ----------------------------

create table if not exists prod.transactions (
  item_num        uuid        not null,
  root_trans_num  uuid        not null,
  run_no          int         not null,
  date_captured   date        not null,
  amount_captured numeric(12,2),
  tran_code       char(6)     not null,
  acct_type       varchar(2)  not null,
  record_type     varchar(2)  not null,
  account_no      char(18)    not null,

  constraint transactions_pk
    primary key (item_num, root_trans_num, run_no, date_captured),

  constraint transactions_acct_type_fk
    foreign key (acct_type) references prod.acct_type(code),

  -- Composite FK required because prod.tran_code PK is (code, acct_type, record_type)
  constraint transactions_tran_code_fk
    foreign key (tran_code, acct_type, record_type)
    references prod.tran_code(code, acct_type, record_type),

  constraint transactions_record_type_fk
    foreign key (record_type) references prod.record_type(code),

  -- Composite FK required because prod.account_master PK is (account_number, acct_type)
  constraint transactions_account_master_fk
    foreign key (account_no, acct_type)
    references prod.account_master(account_number, acct_type)
);

-- ----------------------------
-- Helpful indexes (optional)
-- ----------------------------

create index if not exists idx_transactions_account
  on prod.transactions(account_no, acct_type);

create index if not exists idx_transactions_code
  on prod.transactions(tran_code, acct_type, record_type);

create index if not exists idx_transactions_date
  on prod.transactions(date_captured);

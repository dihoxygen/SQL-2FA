-- ==========================================
-- Production-like schema in `prod` (PostgreSQL)
-- ==========================================

CREATE SCHEMA IF NOT EXISTS prod;

-- ----------------------------
-- Lookup tables
-- ----------------------------

CREATE TABLE IF NOT EXISTS prod.acct_type (
    code         varchar(2) PRIMARY KEY,
    description  text,
    to_acct_type varchar(2),
    CONSTRAINT acct_type_to_acct_type_fk
        FOREIGN KEY (to_acct_type) REFERENCES prod.acct_type(code)
);

CREATE TABLE IF NOT EXISTS prod.record_type (
    code        varchar(2) PRIMARY KEY,
    description text
);

CREATE TABLE IF NOT EXISTS prod.tran_code (
    code        char(6)     NOT NULL,
    acct_type   varchar(2)  NOT NULL,
    record_type varchar(2)  NOT NULL,
    description text,
    posting_tc  char(6),
    CONSTRAINT tran_code_pk PRIMARY KEY (code, acct_type, record_type),
    CONSTRAINT tran_code_acct_type_fk FOREIGN KEY (acct_type) REFERENCES prod.acct_type(code),
    CONSTRAINT tran_code_record_type_fk FOREIGN KEY (record_type) REFERENCES prod.record_type(code)
);

CREATE TABLE IF NOT EXISTS prod.account_master (
    account_number char(18)   NOT NULL,
    acct_type      varchar(2) NOT NULL,
    holder_fname   text,
    holder_lname   text,
    CONSTRAINT account_master_pk PRIMARY KEY (account_number, acct_type),
    CONSTRAINT account_master_acct_type_fk FOREIGN KEY (acct_type) REFERENCES prod.acct_type(code)
);

-- ----------------------------
-- Fact table
-- ----------------------------

CREATE TABLE IF NOT EXISTS prod.transactions (
    item_num        uuid        NOT NULL,
    root_trans_num  uuid        NOT NULL,
    run_no          int         NOT NULL,
    date_captured   date        NOT NULL,
    amount_captured numeric(12,2),
    tran_code       char(6)     NOT NULL,
    acct_type       varchar(2)  NOT NULL,
    record_type     varchar(2)  NOT NULL,
    account_no      char(18)    NOT NULL,

    CONSTRAINT transactions_pk
        PRIMARY KEY (item_num, root_trans_num, run_no, date_captured),

    CONSTRAINT transactions_acct_type_fk
        FOREIGN KEY (acct_type) REFERENCES prod.acct_type(code),

    -- Composite FK required because prod.tran_code PK is (code, acct_type, record_type)
    CONSTRAINT transactions_tran_code_fk
        FOREIGN KEY (tran_code, acct_type, record_type)
        REFERENCES prod.tran_code(code, acct_type, record_type),

    CONSTRAINT transactions_record_type_fk
        FOREIGN KEY (record_type) REFERENCES prod.record_type(code),

    -- Composite FK required because prod.account_master PK is (account_number, acct_type)
    CONSTRAINT transactions_account_master_fk
        FOREIGN KEY (account_no, acct_type)
        REFERENCES prod.account_master(account_number, acct_type)
);

-- ----------------------------
-- Helpful indexes (optional)
-- ----------------------------

CREATE INDEX IF NOT EXISTS idx_transactions_account
    ON prod.transactions(account_no, acct_type);

CREATE INDEX IF NOT EXISTS idx_transactions_code
    ON prod.transactions(tran_code, acct_type, record_type);

CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON prod.transactions(date_captured);


CREATE TABLE promotion (
    id serial PRIMARY KEY,
    bonus_min real NOT NULL CHECK bonus_min >= 0,
    bonus_txt character varying(30) NOT NULL,
    active boolean NOT NULL,
    description text,
    end_date date,
    deposit_min real NOT NULL CHECK deposit_min >= 0,
    deposit_txt character varying(50) NOT NULL,
    timing_text character varying(30) NOT NULL,
    kyc boolean NOT NULL,
    max_slots integer,
    phisical_card boolean NOT NULL,
    special_requirements character varying(50),
    guide text NOT NULL,
    photo_id text,
    platform character varying(30),
    max_slots_txt character varying(30),
    fees character varying(30),
    warnings text
)


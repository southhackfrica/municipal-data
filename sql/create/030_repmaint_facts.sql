-- Table: public.repmaint_facts

-- DROP TABLE public.repmaint_facts;

CREATE TABLE public.repmaint_facts
(
  demarcation_code text REFERENCES scorecard_geography (geo_code),
  period_code text,
  item_code text REFERENCES repmaint_items (code),
  amount bigint,
  id serial,
  financial_year integer,
  period_length text,
  financial_period integer,
  amount_type_code text,
  CONSTRAINT repmaint_facts_pkey PRIMARY KEY (id),
  CONSTRAINT repmaint_facts_unique_demarcation_period_item UNIQUE (demarcation_code, period_code, item_code)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.repmaint_facts
  OWNER TO municipal_finance;

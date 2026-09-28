--
-- PostgreSQL database dump
--


-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: keyword_match_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.keyword_match_rules (
    id integer NOT NULL,
    modality character varying(10) NOT NULL,
    rule_type character varying(20) NOT NULL,
    keywords character varying(500) NOT NULL,
    dst_value character varying(100),
    priority integer NOT NULL,
    enable integer NOT NULL,
    remark character varying(200),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: keyword_match_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.keyword_match_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: keyword_match_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.keyword_match_rules_id_seq OWNED BY public.keyword_match_rules.id;


--
-- Name: lexicon_suggestion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lexicon_suggestion (
    id integer NOT NULL,
    suggestion_type character varying(30) NOT NULL,
    modality character varying(20),
    content_json text NOT NULL,
    reason text,
    status character varying(20) NOT NULL,
    applied_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: lexicon_suggestion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lexicon_suggestion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lexicon_suggestion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lexicon_suggestion_id_seq OWNED BY public.lexicon_suggestion.id;


--
-- Name: match_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_cache (
    id integer NOT NULL,
    text_hash character varying(64) NOT NULL,
    modality character varying(20) NOT NULL,
    original_text text NOT NULL,
    result_json text NOT NULL,
    confidence double precision NOT NULL,
    source character varying(30) NOT NULL,
    rule_version character varying(80),
    hit_count integer DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    confirmed_at timestamp without time zone,
    expires_at timestamp without time zone
);


--
-- Name: match_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.match_cache_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: match_cache_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.match_cache_id_seq OWNED BY public.match_cache.id;


--
-- Name: match_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_feedback (
    id integer NOT NULL,
    text_hash character varying(64) NOT NULL,
    modality character varying(20) NOT NULL,
    original_text text NOT NULL,
    engine_result_json text,
    engine_tier character varying(20),
    feedback_type character varying(30) NOT NULL,
    suggested_fix text,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    resolved_at timestamp without time zone
);


--
-- Name: match_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.match_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: match_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.match_feedback_id_seq OWNED BY public.match_feedback.id;


--
-- Name: mms_eval_details; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mms_eval_details (
    id integer NOT NULL,
    task_id integer NOT NULL,
    check_item text NOT NULL,
    modality character varying(10),
    expected_code character varying(50),
    expected_name character varying(200),
    actual_code character varying(50),
    actual_name character varying(200),
    confidence numeric(5,3),
    response_time numeric(10,2),
    is_matched boolean,
    is_correct boolean,
    match_type character varying(20),
    failure_reason character varying(50),
    failure_detail text,
    reviewed boolean DEFAULT false,
    reviewer character varying(100),
    review_note text,
    review_time timestamp without time zone,
    suggested_action character varying(50),
    suggestion_data jsonb,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: mms_eval_details_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mms_eval_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mms_eval_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mms_eval_details_id_seq OWNED BY public.mms_eval_details.id;


--
-- Name: mms_eval_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mms_eval_tasks (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    test_file_path character varying(500),
    sample_size integer,
    modality character varying(10),
    status character varying(20) DEFAULT 'pending'::character varying,
    progress integer DEFAULT 0,
    total_count integer DEFAULT 0,
    matched_count integer DEFAULT 0,
    correct_count integer DEFAULT 0,
    wrong_count integer DEFAULT 0,
    no_match_count integer DEFAULT 0,
    match_rate numeric(5,2),
    accuracy numeric(5,2),
    precision_score numeric(5,2),
    recall_score numeric(5,2),
    f1_score numeric(5,2),
    avg_confidence numeric(5,3),
    avg_response_time numeric(10,2),
    dict_version character varying(50),
    dict_count integer,
    phrase_count integer,
    created_at timestamp without time zone DEFAULT now(),
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_by character varying(100),
    tags character varying(200)[]
);


--
-- Name: mms_eval_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mms_eval_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mms_eval_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mms_eval_tasks_id_seq OWNED BY public.mms_eval_tasks.id;


--
-- Name: mms_lexicon_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mms_lexicon_versions (
    id integer NOT NULL,
    version character varying(50) NOT NULL,
    description text,
    medical_dict_count integer,
    phrase_map_count integer,
    ambiguity_rule_count integer,
    changelog text,
    added_words integer DEFAULT 0,
    updated_words integer DEFAULT 0,
    deleted_words integer DEFAULT 0,
    match_rate numeric(5,2),
    accuracy numeric(5,2),
    f1_score numeric(5,2),
    is_active boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    created_by character varying(100)
);


--
-- Name: mms_lexicon_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mms_lexicon_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mms_lexicon_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mms_lexicon_versions_id_seq OWNED BY public.mms_lexicon_versions.id;


--
-- Name: mms_optimization_suggestions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mms_optimization_suggestions (
    id integer NOT NULL,
    task_id integer NOT NULL,
    suggestion_type character varying(50) NOT NULL,
    priority integer DEFAULT 5,
    word character varying(200),
    type character varying(50),
    source_phrase character varying(200),
    target_phrase character varying(200),
    step character varying(50),
    affected_count integer,
    example_cases text[],
    status character varying(20) DEFAULT 'pending'::character varying,
    applied_at timestamp without time zone,
    reviewed_by character varying(100),
    review_note text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: mms_optimization_suggestions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mms_optimization_suggestions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mms_optimization_suggestions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mms_optimization_suggestions_id_seq OWNED BY public.mms_optimization_suggestions.id;


--
-- Name: nlp_ambiguity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nlp_ambiguity (
    id integer NOT NULL,
    src_body character varying(100),
    src_process character varying(100),
    dst_body character varying(100) NOT NULL,
    dst_process character varying(100) NOT NULL,
    version character varying(10) NOT NULL,
    modality character varying(50),
    enable integer NOT NULL
);


--
-- Name: nlp_ambiguity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nlp_ambiguity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nlp_ambiguity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nlp_ambiguity_id_seq OWNED BY public.nlp_ambiguity.id;


--
-- Name: nlp_medical_dict; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nlp_medical_dict (
    id integer NOT NULL,
    word character varying(200) NOT NULL,
    type character varying(20) NOT NULL,
    enable integer NOT NULL
);


--
-- Name: nlp_medical_dict_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nlp_medical_dict_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nlp_medical_dict_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nlp_medical_dict_id_seq OWNED BY public.nlp_medical_dict.id;


--
-- Name: nlp_phrase_map; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nlp_phrase_map (
    id integer NOT NULL,
    modality character varying(10) NOT NULL,
    src_word character varying(100) NOT NULL,
    dst_word character varying(100),
    step character varying(100) NOT NULL,
    version character varying(10) NOT NULL,
    enable integer NOT NULL
);


--
-- Name: nlp_phrase_map_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nlp_phrase_map_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nlp_phrase_map_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nlp_phrase_map_id_seq OWNED BY public.nlp_phrase_map.id;


--
-- Name: procedure_dictionary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.procedure_dictionary (
    id integer NOT NULL,
    semantic_id character varying(20) NOT NULL,
    name_en character varying(500) NOT NULL,
    name_zh character varying(500) NOT NULL,
    modality character varying(50),
    body_part character varying(100),
    contrast_used boolean DEFAULT false,
    radiation_level character varying(50),
    exam_duration integer,
    preparation_required boolean DEFAULT false,
    standard_code character varying(50),
    icd10_code character varying(20),
    cpt_code character varying(20),
    description_en text,
    description_zh text,
    is_active boolean DEFAULT true,
    data_source character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: procedure_dictionary_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.procedure_dictionary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: procedure_dictionary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.procedure_dictionary_id_seq OWNED BY public.procedure_dictionary.id;


--
-- Name: procedure_match_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.procedure_match_results (
    procedure_id integer NOT NULL,
    matched boolean NOT NULL,
    tier character varying(20) NOT NULL,
    confidence double precision DEFAULT '0'::double precision NOT NULL,
    source character varying(30) NOT NULL,
    standards_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    reason_code character varying(50),
    detail text,
    rule_version character varying(80) NOT NULL,
    evaluated_at timestamp without time zone DEFAULT now() NOT NULL,
    effective_modality character varying(32)
);


--
-- Name: TABLE procedure_match_results; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.procedure_match_results IS 'alembic:20260808_1500';


--
-- Name: standard_check_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.standard_check_items (
    id integer NOT NULL,
    item_code character varying(20) NOT NULL,
    item_name character varying(255) NOT NULL,
    modality character varying(20) NOT NULL,
    modality_code character varying(20),
    body_part_l1 character varying(50),
    body_part_l1_code character varying(50),
    body_part_l2 character varying(50),
    body_part_l2_code character varying(50),
    body_part_l3 character varying(50),
    body_part_l3_code character varying(50),
    scan_method character varying(50),
    scan_method_code character varying(50),
    post_processing character varying(50),
    post_processing_code character varying(50),
    source character varying(100),
    version character varying(20),
    coverage_status character varying(20) NOT NULL,
    linked_procedure_id integer,
    link_rule character varying(30),
    review_status character varying(20),
    llm_confidence double precision,
    supplement_status character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    position_name character varying(255),
    position_code character varying(100),
    device_type_name character varying(255),
    body_part_code character varying(20),
    insurance_code character varying(50),
    insurance_ext_code character varying(20),
    insurance_name character varying(200),
    insurance_item_code character varying(50),
    province character varying(50) DEFAULT '江西'::character varying,
    body_position text,
    scan_scope text,
    contrast_agent text,
    image_region text,
    image_focus text,
    scan_method_detail text,
    scan_param text,
    coil text,
    base_sequence text,
    compose_sequence text,
    clinical_indication text,
    clinical_significance text,
    organs text,
    anatomical_structure text,
    technical_notes text,
    image_grade text,
    image_score text
);


--
-- Name: COLUMN standard_check_items.position_code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.standard_check_items.position_code IS 'alembic:20260808_1500;restore-varchar=50';


--
-- Name: standard_check_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.standard_check_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: standard_check_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.standard_check_items_id_seq OWNED BY public.standard_check_items.id;


--
-- Name: technical_detail_candidate_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.technical_detail_candidate_revisions (
    id bigint NOT NULL,
    candidate_id bigint NOT NULL,
    revision_no integer NOT NULL,
    before_json jsonb NOT NULL,
    after_json jsonb NOT NULL,
    edited_by character varying(100) NOT NULL,
    edit_notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: technical_detail_candidate_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.technical_detail_candidate_revisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: technical_detail_candidate_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.technical_detail_candidate_revisions_id_seq OWNED BY public.technical_detail_candidate_revisions.id;


--
-- Name: technical_detail_candidates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.technical_detail_candidates (
    id bigint NOT NULL,
    target_item_id integer NOT NULL,
    target_item_code character varying(64) NOT NULL,
    target_item_name character varying(500) NOT NULL,
    target_version character varying(50) NOT NULL,
    modality character varying(32) NOT NULL,
    generation_method character varying(64) NOT NULL,
    candidate_json jsonb NOT NULL,
    field_sources_json jsonb NOT NULL,
    conflicts_json jsonb NOT NULL,
    confidence numeric(5,4) NOT NULL,
    source_item_ids_json jsonb NOT NULL,
    source_fingerprint character varying(64) NOT NULL,
    algorithm_version character varying(64) NOT NULL,
    rationale text NOT NULL,
    status character varying(32) DEFAULT 'pending_review'::character varying NOT NULL,
    reviewer character varying(100),
    review_notes text,
    reviewed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    has_manual_edits boolean DEFAULT false NOT NULL,
    last_edited_by character varying(100),
    last_edited_at timestamp without time zone,
    CONSTRAINT ck_technical_detail_candidate_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_technical_detail_candidate_status CHECK (((status)::text = ANY (ARRAY[('pending_review'::character varying)::text, ('approved'::character varying)::text, ('rejected'::character varying)::text, ('applied'::character varying)::text, ('superseded'::character varying)::text])))
);


--
-- Name: technical_detail_candidates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.technical_detail_candidates_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: technical_detail_candidates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.technical_detail_candidates_id_seq OWNED BY public.technical_detail_candidates.id;


--
-- Name: technical_detail_provenance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.technical_detail_provenance (
    id bigint NOT NULL,
    target_item_id integer NOT NULL,
    source_kind character varying(32) NOT NULL,
    source_system character varying(100) NOT NULL,
    source_table character varying(160) NOT NULL,
    source_record_key character varying(160),
    import_batch character varying(100) NOT NULL,
    match_method character varying(100) NOT NULL,
    field_names_json jsonb NOT NULL,
    evidence_json jsonb NOT NULL,
    source_notes text,
    publication_id bigint,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: technical_detail_provenance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.technical_detail_provenance_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: technical_detail_provenance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.technical_detail_provenance_id_seq OWNED BY public.technical_detail_provenance.id;


--
-- Name: technical_detail_publications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.technical_detail_publications (
    id bigint NOT NULL,
    candidate_id bigint NOT NULL,
    target_item_id integer NOT NULL,
    target_item_code character varying(64) NOT NULL,
    before_json jsonb NOT NULL,
    after_json jsonb NOT NULL,
    source_fingerprint character varying(64) NOT NULL,
    algorithm_version character varying(64) NOT NULL,
    published_by character varying(100) NOT NULL,
    publish_notes text,
    published_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status character varying(32) DEFAULT 'published'::character varying NOT NULL,
    rolled_back_by character varying(100),
    rollback_reason text,
    rolled_back_at timestamp without time zone,
    CONSTRAINT ck_technical_detail_publication_status CHECK (((status)::text = ANY (ARRAY[('published'::character varying)::text, ('rolled_back'::character varying)::text])))
);


--
-- Name: technical_detail_publications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.technical_detail_publications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: technical_detail_publications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.technical_detail_publications_id_seq OWNED BY public.technical_detail_publications.id;


--
-- Name: unmatched_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unmatched_registry (
    id integer NOT NULL,
    procedure_id integer NOT NULL,
    modality character varying(16),
    reason_code character varying(32) NOT NULL,
    detail character varying(255),
    status character varying(16) NOT NULL,
    handled_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: unmatched_registry_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.unmatched_registry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: unmatched_registry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.unmatched_registry_id_seq OWNED BY public.unmatched_registry.id;


--
-- Name: keyword_match_rules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.keyword_match_rules ALTER COLUMN id SET DEFAULT nextval('public.keyword_match_rules_id_seq'::regclass);


--
-- Name: lexicon_suggestion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lexicon_suggestion ALTER COLUMN id SET DEFAULT nextval('public.lexicon_suggestion_id_seq'::regclass);


--
-- Name: match_cache id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_cache ALTER COLUMN id SET DEFAULT nextval('public.match_cache_id_seq'::regclass);


--
-- Name: match_feedback id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_feedback ALTER COLUMN id SET DEFAULT nextval('public.match_feedback_id_seq'::regclass);


--
-- Name: mms_eval_details id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_eval_details ALTER COLUMN id SET DEFAULT nextval('public.mms_eval_details_id_seq'::regclass);


--
-- Name: mms_eval_tasks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_eval_tasks ALTER COLUMN id SET DEFAULT nextval('public.mms_eval_tasks_id_seq'::regclass);


--
-- Name: mms_lexicon_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_lexicon_versions ALTER COLUMN id SET DEFAULT nextval('public.mms_lexicon_versions_id_seq'::regclass);


--
-- Name: mms_optimization_suggestions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_optimization_suggestions ALTER COLUMN id SET DEFAULT nextval('public.mms_optimization_suggestions_id_seq'::regclass);


--
-- Name: nlp_ambiguity id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_ambiguity ALTER COLUMN id SET DEFAULT nextval('public.nlp_ambiguity_id_seq'::regclass);


--
-- Name: nlp_medical_dict id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_medical_dict ALTER COLUMN id SET DEFAULT nextval('public.nlp_medical_dict_id_seq'::regclass);


--
-- Name: nlp_phrase_map id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_phrase_map ALTER COLUMN id SET DEFAULT nextval('public.nlp_phrase_map_id_seq'::regclass);


--
-- Name: procedure_dictionary id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procedure_dictionary ALTER COLUMN id SET DEFAULT nextval('public.procedure_dictionary_id_seq'::regclass);


--
-- Name: standard_check_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.standard_check_items ALTER COLUMN id SET DEFAULT nextval('public.standard_check_items_id_seq'::regclass);


--
-- Name: technical_detail_candidate_revisions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_candidate_revisions ALTER COLUMN id SET DEFAULT nextval('public.technical_detail_candidate_revisions_id_seq'::regclass);


--
-- Name: technical_detail_candidates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_candidates ALTER COLUMN id SET DEFAULT nextval('public.technical_detail_candidates_id_seq'::regclass);


--
-- Name: technical_detail_provenance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_provenance ALTER COLUMN id SET DEFAULT nextval('public.technical_detail_provenance_id_seq'::regclass);


--
-- Name: technical_detail_publications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_publications ALTER COLUMN id SET DEFAULT nextval('public.technical_detail_publications_id_seq'::regclass);


--
-- Name: unmatched_registry id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unmatched_registry ALTER COLUMN id SET DEFAULT nextval('public.unmatched_registry_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: keyword_match_rules keyword_match_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.keyword_match_rules
    ADD CONSTRAINT keyword_match_rules_pkey PRIMARY KEY (id);


--
-- Name: lexicon_suggestion lexicon_suggestion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lexicon_suggestion
    ADD CONSTRAINT lexicon_suggestion_pkey PRIMARY KEY (id);


--
-- Name: match_cache match_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_cache
    ADD CONSTRAINT match_cache_pkey PRIMARY KEY (id);


--
-- Name: match_feedback match_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_feedback
    ADD CONSTRAINT match_feedback_pkey PRIMARY KEY (id);


--
-- Name: mms_eval_details mms_eval_details_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_eval_details
    ADD CONSTRAINT mms_eval_details_pkey PRIMARY KEY (id);


--
-- Name: mms_eval_tasks mms_eval_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_eval_tasks
    ADD CONSTRAINT mms_eval_tasks_pkey PRIMARY KEY (id);


--
-- Name: mms_lexicon_versions mms_lexicon_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_lexicon_versions
    ADD CONSTRAINT mms_lexicon_versions_pkey PRIMARY KEY (id);


--
-- Name: mms_lexicon_versions mms_lexicon_versions_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_lexicon_versions
    ADD CONSTRAINT mms_lexicon_versions_version_key UNIQUE (version);


--
-- Name: mms_optimization_suggestions mms_optimization_suggestions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_optimization_suggestions
    ADD CONSTRAINT mms_optimization_suggestions_pkey PRIMARY KEY (id);


--
-- Name: nlp_ambiguity nlp_ambiguity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_ambiguity
    ADD CONSTRAINT nlp_ambiguity_pkey PRIMARY KEY (id);


--
-- Name: nlp_medical_dict nlp_medical_dict_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_medical_dict
    ADD CONSTRAINT nlp_medical_dict_pkey PRIMARY KEY (id);


--
-- Name: nlp_phrase_map nlp_phrase_map_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_phrase_map
    ADD CONSTRAINT nlp_phrase_map_pkey PRIMARY KEY (id);


--
-- Name: procedure_dictionary procedure_dictionary_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procedure_dictionary
    ADD CONSTRAINT procedure_dictionary_pkey PRIMARY KEY (id);


--
-- Name: procedure_dictionary procedure_dictionary_semantic_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procedure_dictionary
    ADD CONSTRAINT procedure_dictionary_semantic_id_key UNIQUE (semantic_id);


--
-- Name: procedure_match_results procedure_match_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procedure_match_results
    ADD CONSTRAINT procedure_match_results_pkey PRIMARY KEY (procedure_id);


--
-- Name: standard_check_items standard_check_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.standard_check_items
    ADD CONSTRAINT standard_check_items_pkey PRIMARY KEY (id);


--
-- Name: technical_detail_candidate_revisions technical_detail_candidate_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_candidate_revisions
    ADD CONSTRAINT technical_detail_candidate_revisions_pkey PRIMARY KEY (id);


--
-- Name: technical_detail_candidates technical_detail_candidates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_candidates
    ADD CONSTRAINT technical_detail_candidates_pkey PRIMARY KEY (id);


--
-- Name: technical_detail_provenance technical_detail_provenance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_provenance
    ADD CONSTRAINT technical_detail_provenance_pkey PRIMARY KEY (id);


--
-- Name: technical_detail_publications technical_detail_publications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_publications
    ADD CONSTRAINT technical_detail_publications_pkey PRIMARY KEY (id);


--
-- Name: unmatched_registry unmatched_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unmatched_registry
    ADD CONSTRAINT unmatched_registry_pkey PRIMARY KEY (id);


--
-- Name: keyword_match_rules uq_keyword_match_rule_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.keyword_match_rules
    ADD CONSTRAINT uq_keyword_match_rule_key UNIQUE (modality, rule_type, keywords);


--
-- Name: nlp_ambiguity uq_nlp_ambiguity_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_ambiguity
    ADD CONSTRAINT uq_nlp_ambiguity_key UNIQUE (src_body, src_process, version, modality);


--
-- Name: nlp_medical_dict uq_nlp_medical_dict_word; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_medical_dict
    ADD CONSTRAINT uq_nlp_medical_dict_word UNIQUE (word);


--
-- Name: nlp_phrase_map uq_nlp_phrase_map_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nlp_phrase_map
    ADD CONSTRAINT uq_nlp_phrase_map_key UNIQUE (modality, src_word, step, version);


--
-- Name: standard_check_items uq_standard_items_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.standard_check_items
    ADD CONSTRAINT uq_standard_items_code UNIQUE (item_code);


--
-- Name: technical_detail_candidates uq_technical_detail_candidate_target_algorithm; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_candidates
    ADD CONSTRAINT uq_technical_detail_candidate_target_algorithm UNIQUE (target_item_id, algorithm_version);


--
-- Name: technical_detail_provenance uq_technical_detail_provenance_source_batch; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_provenance
    ADD CONSTRAINT uq_technical_detail_provenance_source_batch UNIQUE (target_item_id, source_table, import_batch);


--
-- Name: technical_detail_candidate_revisions uq_technical_detail_revision_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_candidate_revisions
    ADD CONSTRAINT uq_technical_detail_revision_number UNIQUE (candidate_id, revision_no);


--
-- Name: idx_keyword_match_rules_modality_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_keyword_match_rules_modality_type ON public.keyword_match_rules USING btree (modality, rule_type);


--
-- Name: idx_match_cache_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_match_cache_expires ON public.match_cache USING btree (expires_at);


--
-- Name: idx_match_cache_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_match_cache_lookup ON public.match_cache USING btree (text_hash, modality);


--
-- Name: idx_mms_eval_details_failure_reason; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_eval_details_failure_reason ON public.mms_eval_details USING btree (failure_reason);


--
-- Name: idx_mms_eval_details_is_correct; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_eval_details_is_correct ON public.mms_eval_details USING btree (is_correct);


--
-- Name: idx_mms_eval_details_reviewed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_eval_details_reviewed ON public.mms_eval_details USING btree (reviewed);


--
-- Name: idx_mms_eval_details_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_eval_details_task_id ON public.mms_eval_details USING btree (task_id);


--
-- Name: idx_mms_eval_tasks_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_eval_tasks_created_at ON public.mms_eval_tasks USING btree (created_at);


--
-- Name: idx_mms_eval_tasks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_eval_tasks_status ON public.mms_eval_tasks USING btree (status);


--
-- Name: idx_mms_opt_suggestions_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_opt_suggestions_priority ON public.mms_optimization_suggestions USING btree (priority);


--
-- Name: idx_mms_opt_suggestions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_opt_suggestions_status ON public.mms_optimization_suggestions USING btree (status);


--
-- Name: idx_mms_opt_suggestions_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mms_opt_suggestions_task_id ON public.mms_optimization_suggestions USING btree (task_id);


--
-- Name: idx_nlp_ambiguity_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nlp_ambiguity_lookup ON public.nlp_ambiguity USING btree (src_body, modality, version);


--
-- Name: idx_nlp_phrase_map_modality_step; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nlp_phrase_map_modality_step ON public.nlp_phrase_map USING btree (modality, step);


--
-- Name: idx_procedures_modality; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_procedures_modality ON public.procedure_dictionary USING btree (modality);


--
-- Name: idx_procedures_name_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_procedures_name_unique ON public.procedure_dictionary USING btree (name_en, name_zh);


--
-- Name: idx_procedures_semantic_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_procedures_semantic_id ON public.procedure_dictionary USING btree (semantic_id);


--
-- Name: idx_standard_items_body_part_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_standard_items_body_part_code ON public.standard_check_items USING btree (body_part_code);


--
-- Name: idx_standard_items_insurance_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_standard_items_insurance_code ON public.standard_check_items USING btree (insurance_code);


--
-- Name: idx_standard_items_modality_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_standard_items_modality_version ON public.standard_check_items USING btree (modality, version);


--
-- Name: idx_standard_items_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_standard_items_version ON public.standard_check_items USING btree (version);


--
-- Name: ix_keyword_match_rules_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_keyword_match_rules_id ON public.keyword_match_rules USING btree (id);


--
-- Name: ix_keyword_match_rules_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_keyword_match_rules_priority ON public.keyword_match_rules USING btree (priority);


--
-- Name: ix_match_cache_rule_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_match_cache_rule_version ON public.match_cache USING btree (rule_version);


--
-- Name: ix_nlp_ambiguity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_nlp_ambiguity_id ON public.nlp_ambiguity USING btree (id);


--
-- Name: ix_nlp_medical_dict_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_nlp_medical_dict_id ON public.nlp_medical_dict USING btree (id);


--
-- Name: ix_nlp_phrase_map_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_nlp_phrase_map_id ON public.nlp_phrase_map USING btree (id);


--
-- Name: ix_procedure_match_results_matched; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procedure_match_results_matched ON public.procedure_match_results USING btree (matched);


--
-- Name: INDEX ix_procedure_match_results_matched; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.ix_procedure_match_results_matched IS 'alembic:20260808_1500';


--
-- Name: ix_procedure_match_results_rule_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procedure_match_results_rule_version ON public.procedure_match_results USING btree (rule_version);


--
-- Name: INDEX ix_procedure_match_results_rule_version; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.ix_procedure_match_results_rule_version IS 'alembic:20260808_1500';


--
-- Name: ix_standard_check_items_body_part_l1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_standard_check_items_body_part_l1 ON public.standard_check_items USING btree (body_part_l1);


--
-- Name: ix_standard_check_items_coverage_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_standard_check_items_coverage_status ON public.standard_check_items USING btree (coverage_status);


--
-- Name: ix_standard_check_items_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_standard_check_items_id ON public.standard_check_items USING btree (id);


--
-- Name: ix_standard_check_items_item_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_standard_check_items_item_code ON public.standard_check_items USING btree (item_code);


--
-- Name: ix_standard_check_items_item_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_standard_check_items_item_name ON public.standard_check_items USING btree (item_name);


--
-- Name: ix_standard_check_items_modality; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_standard_check_items_modality ON public.standard_check_items USING btree (modality);


--
-- Name: ix_standard_check_items_review_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_standard_check_items_review_status ON public.standard_check_items USING btree (review_status);


--
-- Name: ix_technical_detail_candidates_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_detail_candidates_status ON public.technical_detail_candidates USING btree (status, modality, target_version);


--
-- Name: ix_technical_detail_candidates_target_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_detail_candidates_target_code ON public.technical_detail_candidates USING btree (target_item_code);


--
-- Name: ix_technical_detail_provenance_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_detail_provenance_item ON public.technical_detail_provenance USING btree (target_item_id, is_active);


--
-- Name: ix_technical_detail_provenance_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_detail_provenance_source ON public.technical_detail_provenance USING btree (source_kind, source_table);


--
-- Name: ix_technical_detail_publications_candidate; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_detail_publications_candidate ON public.technical_detail_publications USING btree (candidate_id, published_at);


--
-- Name: ix_technical_detail_publications_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_detail_publications_target ON public.technical_detail_publications USING btree (target_item_id, status);


--
-- Name: ix_technical_detail_revisions_candidate; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technical_detail_revisions_candidate ON public.technical_detail_candidate_revisions USING btree (candidate_id, revision_no);


--
-- Name: ix_unmatched_registry_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_unmatched_registry_id ON public.unmatched_registry USING btree (id);


--
-- Name: ix_unmatched_registry_procedure_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_unmatched_registry_procedure_id ON public.unmatched_registry USING btree (procedure_id);


--
-- Name: ix_unmatched_registry_reason_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_unmatched_registry_reason_code ON public.unmatched_registry USING btree (reason_code);


--
-- Name: ix_unmatched_registry_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_unmatched_registry_status ON public.unmatched_registry USING btree (status);


--
-- Name: uq_match_feedback_text_hash_modality; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_match_feedback_text_hash_modality ON public.match_feedback USING btree (text_hash, modality);


--
-- Name: procedure_dictionary trg_acrac_vector_sync; Type: TRIGGER; Schema: public; Owner: -
--

-- Deliberately excluded: ACRAC vector outbox trigger belongs to the main project.
-- Its clinical_recommendations/vector_sync_outbox dependencies are not MMS-owned.


--
-- Name: technical_detail_provenance fk_technical_detail_provenance_item; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_provenance
    ADD CONSTRAINT fk_technical_detail_provenance_item FOREIGN KEY (target_item_id) REFERENCES public.standard_check_items(id) ON DELETE CASCADE;


--
-- Name: technical_detail_provenance fk_technical_detail_provenance_publication; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_provenance
    ADD CONSTRAINT fk_technical_detail_provenance_publication FOREIGN KEY (publication_id) REFERENCES public.technical_detail_publications(id);


--
-- Name: technical_detail_publications fk_technical_detail_publication_candidate; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_publications
    ADD CONSTRAINT fk_technical_detail_publication_candidate FOREIGN KEY (candidate_id) REFERENCES public.technical_detail_candidates(id);


--
-- Name: technical_detail_candidate_revisions fk_technical_detail_revision_candidate; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technical_detail_candidate_revisions
    ADD CONSTRAINT fk_technical_detail_revision_candidate FOREIGN KEY (candidate_id) REFERENCES public.technical_detail_candidates(id) ON DELETE CASCADE;


--
-- Name: mms_eval_details mms_eval_details_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_eval_details
    ADD CONSTRAINT mms_eval_details_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.mms_eval_tasks(id) ON DELETE CASCADE;


--
-- Name: mms_optimization_suggestions mms_optimization_suggestions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mms_optimization_suggestions
    ADD CONSTRAINT mms_optimization_suggestions_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.mms_eval_tasks(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--



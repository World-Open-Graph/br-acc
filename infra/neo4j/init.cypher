// BR-ACC Neo4j Schema — Constraints and Indexes
// Applied on database initialization

// ── Uniqueness Constraints ──────────────────────────────
CREATE CONSTRAINT person_cpf_unique IF NOT EXISTS
  FOR (p:Person) REQUIRE p.cpf IS UNIQUE;

CREATE CONSTRAINT partner_id_unique IF NOT EXISTS
  FOR (p:Partner) REQUIRE p.partner_id IS UNIQUE;

CREATE CONSTRAINT company_cnpj_unique IF NOT EXISTS
  FOR (c:Company) REQUIRE c.cnpj IS UNIQUE;

CREATE CONSTRAINT contract_contract_id_unique IF NOT EXISTS
  FOR (c:Contract) REQUIRE c.contract_id IS UNIQUE;

CREATE CONSTRAINT sanction_sanction_id_unique IF NOT EXISTS
  FOR (s:Sanction) REQUIRE s.sanction_id IS UNIQUE;

CREATE CONSTRAINT public_office_id_unique IF NOT EXISTS
  FOR (po:PublicOffice) REQUIRE po.office_id IS UNIQUE;

CREATE CONSTRAINT investigation_id_unique IF NOT EXISTS
  FOR (i:Investigation) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT amendment_id_unique IF NOT EXISTS
  FOR (a:Amendment) REQUIRE a.amendment_id IS UNIQUE;

CREATE CONSTRAINT health_cnes_code_unique IF NOT EXISTS
  FOR (h:Health) REQUIRE h.cnes_code IS UNIQUE;

CREATE CONSTRAINT finance_id_unique IF NOT EXISTS
  FOR (f:Finance) REQUIRE f.finance_id IS UNIQUE;

CREATE CONSTRAINT embargo_id_unique IF NOT EXISTS
  FOR (e:Embargo) REQUIRE e.embargo_id IS UNIQUE;

CREATE CONSTRAINT education_school_id_unique IF NOT EXISTS
  FOR (e:Education) REQUIRE e.school_id IS UNIQUE;

CREATE CONSTRAINT convenio_id_unique IF NOT EXISTS
  FOR (c:Convenio) REQUIRE c.convenio_id IS UNIQUE;

CREATE CONSTRAINT laborstats_id_unique IF NOT EXISTS
  FOR (l:LaborStats) REQUIRE l.stats_id IS UNIQUE;

CREATE CONSTRAINT offshore_entity_id_unique IF NOT EXISTS
  FOR (o:OffshoreEntity) REQUIRE o.offshore_id IS UNIQUE;

CREATE CONSTRAINT offshore_officer_id_unique IF NOT EXISTS
  FOR (o:OffshoreOfficer) REQUIRE o.offshore_officer_id IS UNIQUE;

CREATE CONSTRAINT global_pep_id_unique IF NOT EXISTS
  FOR (g:GlobalPEP) REQUIRE g.pep_id IS UNIQUE;

CREATE CONSTRAINT cvm_proceeding_id_unique IF NOT EXISTS
  FOR (c:CVMProceeding) REQUIRE c.pas_id IS UNIQUE;

CREATE CONSTRAINT expense_id_unique IF NOT EXISTS
  FOR (e:Expense) REQUIRE e.expense_id IS UNIQUE;

CREATE CONSTRAINT expulsion_id_unique IF NOT EXISTS
  FOR (e:Expulsion) REQUIRE e.expulsion_id IS UNIQUE;

CREATE CONSTRAINT leniency_id_unique IF NOT EXISTS
  FOR (l:LeniencyAgreement) REQUIRE l.leniency_id IS UNIQUE;

CREATE CONSTRAINT pep_record_id_unique IF NOT EXISTS
  FOR (p:PEPRecord) REQUIRE p.pep_id IS UNIQUE;

CREATE CONSTRAINT barred_ngo_id_unique IF NOT EXISTS
  FOR (b:BarredNGO) REQUIRE b.ngo_id IS UNIQUE;

CREATE CONSTRAINT gov_card_expense_id_unique IF NOT EXISTS
  FOR (g:GovCardExpense) REQUIRE g.expense_id IS UNIQUE;

CREATE CONSTRAINT gov_travel_id_unique IF NOT EXISTS
  FOR (t:GovTravel) REQUIRE t.travel_id IS UNIQUE;

CREATE CONSTRAINT tax_waiver_id_unique IF NOT EXISTS
  FOR (t:TaxWaiver) REQUIRE t.waiver_id IS UNIQUE;

CREATE CONSTRAINT bcb_penalty_id_unique IF NOT EXISTS
  FOR (b:BCBPenalty) REQUIRE b.penalty_id IS UNIQUE;

CREATE CONSTRAINT legal_case_id_unique IF NOT EXISTS
  FOR (l:LegalCase) REQUIRE l.case_id IS UNIQUE;

CREATE CONSTRAINT international_sanction_id_unique IF NOT EXISTS
  FOR (s:InternationalSanction) REQUIRE s.sanction_id IS UNIQUE;

CREATE CONSTRAINT declared_asset_id_unique IF NOT EXISTS
  FOR (d:DeclaredAsset) REQUIRE d.asset_id IS UNIQUE;

CREATE CONSTRAINT holding_rel_id_unique IF NOT EXISTS
  FOR (h:Holding) REQUIRE h.holding_id IS UNIQUE;

CREATE CONSTRAINT bid_id_unique IF NOT EXISTS
  FOR (b:Bid) REQUIRE b.bid_id IS UNIQUE;

CREATE CONSTRAINT fund_cnpj_unique IF NOT EXISTS
  FOR (f:Fund) REQUIRE f.fund_cnpj IS UNIQUE;

CREATE CONSTRAINT dou_act_id_unique IF NOT EXISTS
  FOR (d:DOUAct) REQUIRE d.act_id IS UNIQUE;

CREATE CONSTRAINT municipal_finance_id_unique IF NOT EXISTS
  FOR (m:MunicipalFinance) REQUIRE m.finance_id IS UNIQUE;

CREATE CONSTRAINT party_membership_id_unique IF NOT EXISTS
  FOR (pm:PartyMembership) REQUIRE pm.membership_id IS UNIQUE;

CREATE CONSTRAINT labor_movement_id_unique IF NOT EXISTS
  FOR (lm:LaborMovement) REQUIRE lm.movement_id IS UNIQUE;

CREATE CONSTRAINT cpi_id_unique IF NOT EXISTS
  FOR (c:CPI) REQUIRE c.cpi_id IS UNIQUE;

CREATE CONSTRAINT inquiry_id_unique IF NOT EXISTS
  FOR (i:Inquiry) REQUIRE i.inquiry_id IS UNIQUE;

CREATE CONSTRAINT inquiry_requirement_id_unique IF NOT EXISTS
  FOR (r:InquiryRequirement) REQUIRE r.requirement_id IS UNIQUE;

CREATE CONSTRAINT inquiry_session_id_unique IF NOT EXISTS
  FOR (s:InquirySession) REQUIRE s.session_id IS UNIQUE;

CREATE CONSTRAINT municipal_bid_id_unique IF NOT EXISTS
  FOR (b:MunicipalBid) REQUIRE b.municipal_bid_id IS UNIQUE;

CREATE CONSTRAINT municipal_contract_id_unique IF NOT EXISTS
  FOR (c:MunicipalContract) REQUIRE c.municipal_contract_id IS UNIQUE;

CREATE CONSTRAINT municipal_bid_item_id_unique IF NOT EXISTS
  FOR (i:MunicipalBidItem) REQUIRE i.municipal_item_id IS UNIQUE;

CREATE CONSTRAINT municipal_gazette_act_id_unique IF NOT EXISTS
  FOR (a:MunicipalGazetteAct) REQUIRE a.municipal_gazette_act_id IS UNIQUE;

CREATE CONSTRAINT judicial_case_id_unique IF NOT EXISTS
  FOR (j:JudicialCase) REQUIRE j.judicial_case_id IS UNIQUE;

CREATE CONSTRAINT source_document_id_unique IF NOT EXISTS
  FOR (s:SourceDocument) REQUIRE s.doc_id IS UNIQUE;

CREATE CONSTRAINT ingestion_run_id_unique IF NOT EXISTS
  FOR (r:IngestionRun) REQUIRE r.run_id IS UNIQUE;

CREATE CONSTRAINT temporal_violation_id_unique IF NOT EXISTS
  FOR (t:TemporalViolation) REQUIRE t.violation_id IS UNIQUE;

// ── Indexes ─────────────────────────────────────────────
CREATE INDEX person_name IF NOT EXISTS
  FOR (p:Person) ON (p.name);

CREATE INDEX person_name_uf IF NOT EXISTS
  FOR (p:Person) ON (p.name, p.uf);

CREATE INDEX person_author_key IF NOT EXISTS
  FOR (p:Person) ON (p.author_key);

CREATE INDEX person_sq_candidato IF NOT EXISTS
  FOR (p:Person) ON (p.sq_candidato);

CREATE INDEX person_cpf_middle6 IF NOT EXISTS
  FOR (p:Person) ON (p.cpf_middle6);

CREATE INDEX person_cpf_partial IF NOT EXISTS
  FOR (p:Person) ON (p.cpf_partial);

CREATE INDEX partner_name IF NOT EXISTS
  FOR (p:Partner) ON (p.name);

CREATE INDEX partner_doc_partial IF NOT EXISTS
  FOR (p:Partner) ON (p.doc_partial);

CREATE INDEX partner_name_doc_partial IF NOT EXISTS
  FOR (p:Partner) ON (p.name, p.doc_partial);

CREATE INDEX company_razao_social IF NOT EXISTS
  FOR (c:Company) ON (c.razao_social);

CREATE INDEX contract_value IF NOT EXISTS
  FOR (c:Contract) ON (c.value);

CREATE INDEX contract_object IF NOT EXISTS
  FOR (c:Contract) ON (c.object);

CREATE INDEX sanction_type IF NOT EXISTS
  FOR (s:Sanction) ON (s.type);

CREATE INDEX election_year IF NOT EXISTS
  FOR (e:Election) ON (e.year);

CREATE INDEX election_composite IF NOT EXISTS
  FOR (e:Election) ON (e.year, e.cargo, e.uf, e.municipio);

CREATE INDEX amendment_function IF NOT EXISTS
  FOR (a:Amendment) ON (a.function);

CREATE INDEX company_cnae_principal IF NOT EXISTS
  FOR (c:Company) ON (c.cnae_principal);

CREATE INDEX contract_contracting_org IF NOT EXISTS
  FOR (c:Contract) ON (c.contracting_org);

CREATE INDEX contract_date IF NOT EXISTS
  FOR (c:Contract) ON (c.date);

CREATE INDEX sanction_date_start IF NOT EXISTS
  FOR (s:Sanction) ON (s.date_start);

CREATE INDEX amendment_value_committed IF NOT EXISTS
  FOR (a:Amendment) ON (a.value_committed);

// ── Finance Indexes ───────────────────────────────────
CREATE INDEX finance_type IF NOT EXISTS
  FOR (f:Finance) ON (f.type);

CREATE INDEX finance_value IF NOT EXISTS
  FOR (f:Finance) ON (f.value);

CREATE INDEX finance_date IF NOT EXISTS
  FOR (f:Finance) ON (f.date);

CREATE INDEX finance_source IF NOT EXISTS
  FOR (f:Finance) ON (f.source);

// ── Embargo Indexes ───────────────────────────────────
CREATE INDEX embargo_uf IF NOT EXISTS
  FOR (e:Embargo) ON (e.uf);

CREATE INDEX embargo_biome IF NOT EXISTS
  FOR (e:Embargo) ON (e.biome);

// ── Health Indexes ────────────────────────────────────
CREATE INDEX health_name IF NOT EXISTS
  FOR (h:Health) ON (h.name);

CREATE INDEX health_uf IF NOT EXISTS
  FOR (h:Health) ON (h.uf);

CREATE INDEX health_municipio IF NOT EXISTS
  FOR (h:Health) ON (h.municipio);

CREATE INDEX health_atende_sus IF NOT EXISTS
  FOR (h:Health) ON (h.atende_sus);

// ── Education Indexes ───────────────────────────────────
CREATE INDEX education_name IF NOT EXISTS
  FOR (e:Education) ON (e.name);

// ── Convenio Indexes ────────────────────────────────────
CREATE INDEX convenio_date_published IF NOT EXISTS
  FOR (c:Convenio) ON (c.date_published);

// ── LaborStats Indexes ──────────────────────────────────
CREATE INDEX laborstats_uf IF NOT EXISTS
  FOR (l:LaborStats) ON (l.uf);

CREATE INDEX laborstats_cnae_subclass IF NOT EXISTS
  FOR (l:LaborStats) ON (l.cnae_subclass);

// ── OffshoreEntity Indexes ───────────────────────────────
CREATE INDEX offshore_entity_name IF NOT EXISTS
  FOR (o:OffshoreEntity) ON (o.name);

CREATE INDEX offshore_entity_jurisdiction IF NOT EXISTS
  FOR (o:OffshoreEntity) ON (o.jurisdiction);

// ── OffshoreOfficer Indexes ─────────────────────────────
CREATE INDEX offshore_officer_name IF NOT EXISTS
  FOR (o:OffshoreOfficer) ON (o.name);

// ── GlobalPEP Indexes ───────────────────────────────────
CREATE INDEX global_pep_name IF NOT EXISTS
  FOR (g:GlobalPEP) ON (g.name);

CREATE INDEX global_pep_country IF NOT EXISTS
  FOR (g:GlobalPEP) ON (g.country);

// ── CVMProceeding Indexes ───────────────────────────────
CREATE INDEX cvm_proceeding_date IF NOT EXISTS
  FOR (c:CVMProceeding) ON (c.date);

// ── Expense Indexes ─────────────────────────────────────
CREATE INDEX expense_deputy_id IF NOT EXISTS
  FOR (e:Expense) ON (e.deputy_id);

CREATE INDEX expense_date IF NOT EXISTS
  FOR (e:Expense) ON (e.date);

CREATE INDEX expense_type IF NOT EXISTS
  FOR (e:Expense) ON (e.type);

// ── Person Deputy ID Index ──────────────────────────────
CREATE INDEX person_deputy_id IF NOT EXISTS
  FOR (p:Person) ON (p.deputy_id);

CREATE INDEX person_servidor_id IF NOT EXISTS
  FOR (p:Person) ON (p.servidor_id);

// ── PublicOffice Indexes ────────────────────────────────
CREATE INDEX public_office_org IF NOT EXISTS
  FOR (po:PublicOffice) ON (po.org);

CREATE INDEX inquiry_name IF NOT EXISTS
  FOR (i:Inquiry) ON (i.name);

CREATE INDEX inquiry_kind_house IF NOT EXISTS
  FOR (i:Inquiry) ON (i.kind, i.house);

CREATE INDEX inquiry_requirement_date IF NOT EXISTS
  FOR (r:InquiryRequirement) ON (r.date);

CREATE INDEX inquiry_session_date IF NOT EXISTS
  FOR (s:InquirySession) ON (s.date);

CREATE INDEX municipal_bid_date IF NOT EXISTS
  FOR (b:MunicipalBid) ON (b.published_at);

CREATE INDEX municipal_contract_date IF NOT EXISTS
  FOR (c:MunicipalContract) ON (c.signed_at);

CREATE INDEX municipal_gazette_date IF NOT EXISTS
  FOR (a:MunicipalGazetteAct) ON (a.published_at);

CREATE INDEX judicial_case_number IF NOT EXISTS
  FOR (j:JudicialCase) ON (j.case_number);

CREATE INDEX source_document_source_id IF NOT EXISTS
  FOR (s:SourceDocument) ON (s.source_id);

CREATE INDEX source_document_published_at IF NOT EXISTS
  FOR (s:SourceDocument) ON (s.published_at);

CREATE INDEX source_document_retrieved_at IF NOT EXISTS
  FOR (s:SourceDocument) ON (s.retrieved_at);

CREATE INDEX ingestion_run_source_id IF NOT EXISTS
  FOR (r:IngestionRun) ON (r.source_id);

CREATE INDEX ingestion_run_status IF NOT EXISTS
  FOR (r:IngestionRun) ON (r.status);

CREATE INDEX ingestion_run_started_at IF NOT EXISTS
  FOR (r:IngestionRun) ON (r.started_at);

CREATE INDEX temporal_violation_source_id IF NOT EXISTS
  FOR (t:TemporalViolation) ON (t.source_id);

CREATE INDEX temporal_violation_event_date IF NOT EXISTS
  FOR (t:TemporalViolation) ON (t.event_date);

CREATE INDEX socio_snapshot_membership_id IF NOT EXISTS
  FOR ()-[r:SOCIO_DE_SNAPSHOT]-() ON (r.membership_id);

CREATE INDEX socio_snapshot_date IF NOT EXISTS
  FOR ()-[r:SOCIO_DE_SNAPSHOT]-() ON (r.snapshot_date);

// ── PEPRecord Indexes ─────────────────────────────────────
CREATE INDEX pep_record_name IF NOT EXISTS
  FOR (p:PEPRecord) ON (p.name);

CREATE INDEX pep_record_role IF NOT EXISTS
  FOR (p:PEPRecord) ON (p.role);

CREATE INDEX pep_record_org IF NOT EXISTS
  FOR (p:PEPRecord) ON (p.org);

// ── Expulsion Indexes ─────────────────────────────────────
CREATE INDEX expulsion_date IF NOT EXISTS
  FOR (e:Expulsion) ON (e.date);

// ── LeniencyAgreement Indexes ─────────────────────────────
CREATE INDEX leniency_date IF NOT EXISTS
  FOR (l:LeniencyAgreement) ON (l.date);

// ── GovCardExpense Indexes ────────────────────────────────
CREATE INDEX gov_card_expense_date IF NOT EXISTS
  FOR (g:GovCardExpense) ON (g.date);

CREATE INDEX gov_card_expense_value IF NOT EXISTS
  FOR (g:GovCardExpense) ON (g.value);

// ── TaxWaiver Indexes ─────────────────────────────────────
CREATE INDEX tax_waiver_value IF NOT EXISTS
  FOR (t:TaxWaiver) ON (t.value);

// ── LegalCase Indexes ─────────────────────────────────────
CREATE INDEX legal_case_type IF NOT EXISTS
  FOR (l:LegalCase) ON (l.type);

CREATE INDEX legal_case_date IF NOT EXISTS
  FOR (l:LegalCase) ON (l.date);

// ── DeclaredAsset Indexes ─────────────────────────────────
CREATE INDEX declared_asset_type IF NOT EXISTS
  FOR (d:DeclaredAsset) ON (d.asset_type);

CREATE INDEX declared_asset_value IF NOT EXISTS
  FOR (d:DeclaredAsset) ON (d.asset_value);

CREATE INDEX declared_asset_year IF NOT EXISTS
  FOR (d:DeclaredAsset) ON (d.election_year);

// ── InternationalSanction Indexes ─────────────────────────
CREATE INDEX international_sanction_source IF NOT EXISTS
  FOR (s:InternationalSanction) ON (s.source);

// ── Bid Indexes ─────────────────────────────────────────────
CREATE INDEX bid_date IF NOT EXISTS
  FOR (b:Bid) ON (b.date);

CREATE INDEX bid_modality IF NOT EXISTS
  FOR (b:Bid) ON (b.modality);

// ── Fund Indexes ─────────────────────────────────────────────
CREATE INDEX fund_name IF NOT EXISTS
  FOR (f:Fund) ON (f.fund_name);

CREATE INDEX fund_type IF NOT EXISTS
  FOR (f:Fund) ON (f.fund_type);

// ── DOUAct Indexes ─────────────────────────────────────────
CREATE INDEX dou_act_date IF NOT EXISTS
  FOR (d:DOUAct) ON (d.date);

CREATE INDEX dou_act_type IF NOT EXISTS
  FOR (d:DOUAct) ON (d.act_type);

// ── GovTravel Indexes ──────────────────────────────────────
CREATE INDEX gov_travel_date IF NOT EXISTS
  FOR (t:GovTravel) ON (t.start_date);

// ── MunicipalFinance Indexes ───────────────────────────────
CREATE INDEX municipal_finance_year IF NOT EXISTS
  FOR (m:MunicipalFinance) ON (m.year);

CREATE INDEX municipal_finance_cod_ibge IF NOT EXISTS
  FOR (m:MunicipalFinance) ON (m.cod_ibge);

// ── PartyMembership Indexes ──────────────────────────────
CREATE INDEX party_membership_party IF NOT EXISTS
  FOR (pm:PartyMembership) ON (pm.party);

CREATE INDEX party_membership_uf IF NOT EXISTS
  FOR (pm:PartyMembership) ON (pm.uf);

// ── BarredNGO Indexes ────────────────────────────────────
CREATE INDEX barred_ngo_cnpj IF NOT EXISTS
  FOR (b:BarredNGO) ON (b.cnpj);

// ── LaborMovement Indexes ─────────────────────────────────
CREATE INDEX labor_movement_date IF NOT EXISTS
  FOR (lm:LaborMovement) ON (lm.movement_date);

CREATE INDEX labor_movement_type IF NOT EXISTS
  FOR (lm:LaborMovement) ON (lm.movement_type);

CREATE INDEX labor_movement_uf IF NOT EXISTS
  FOR (lm:LaborMovement) ON (lm.uf);

// ── CPI Indexes ──────────────────────────────────────────
CREATE INDEX cpi_name IF NOT EXISTS
  FOR (c:CPI) ON (c.name);

CREATE INDEX cpi_date IF NOT EXISTS
  FOR (c:CPI) ON (c.date_start);

// ── BCBPenalty Indexes ───────────────────────────────────
CREATE INDEX bcb_penalty_type IF NOT EXISTS
  FOR (b:BCBPenalty) ON (b.penalty_type);

CREATE INDEX bcb_penalty_date IF NOT EXISTS
  FOR (b:BCBPenalty) ON (b.decision_date);

// ── Fulltext Search Index ───────────────────────────────
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (n:Person|Partner|Company|Health|Education|Contract|Amendment|Convenio|Embargo|PublicOffice|OffshoreEntity|OffshoreOfficer|GlobalPEP|CVMProceeding|Expense|PEPRecord|Expulsion|LeniencyAgreement|GovCardExpense|GovTravel|TaxWaiver|LegalCase|DeclaredAsset|InternationalSanction|Bid|Fund|DOUAct|MunicipalFinance|PartyMembership|BarredNGO|BCBPenalty|LaborMovement|CPI|Inquiry|InquiryRequirement|InquirySession|MunicipalBid|MunicipalContract|MunicipalGazetteAct|JudicialCase|SourceDocument)
  ON EACH [n.name, n.razao_social, n.cpf, n.cnpj, n.doc_partial, n.doc_raw, n.cnes_code, n.object, n.contracting_org, n.convenente, n.infraction, n.org, n.function, n.jurisdiction, n.penalty_type, n.description, n.institution_name, n.subject, n.text, n.topic, n.case_number, n.url];

// ── User Constraints ────────────────────────────────────
CREATE CONSTRAINT user_email_unique IF NOT EXISTS
  FOR (u:User) REQUIRE u.email IS UNIQUE;

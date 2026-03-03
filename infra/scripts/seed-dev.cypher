// BR-ACC Dev Seed Data
// Small fixture graph that exercises all 5 analysis patterns
// Run: cypher-shell -f seed-dev.cypher

// ── Clean existing dev data ─────────────────────────────
MATCH (n) DETACH DELETE n;

// ── Persons (Politicians & Family) ──────────────────────
CREATE (p1:Person {
  cpf: '11111111111', name: 'CARLOS ALBERTO SILVA',
  patrimonio_declarado: 500000.0, is_pep: true
});
CREATE (p2:Person {
  cpf: '22222222222', name: 'MARIA SILVA COSTA',
  patrimonio_declarado: 200000.0, is_pep: false
});
CREATE (p3:Person {
  cpf: '33333333333', name: 'JOAO PEREIRA NETO',
  patrimonio_declarado: 800000.0, is_pep: true
});
CREATE (p4:Person {
  cpf: '44444444444', name: 'ANA LUCIA FERREIRA',
  patrimonio_declarado: 150000.0, is_pep: false
});
CREATE (p5:Person {
  cpf: '55555555555', name: 'ROBERTO SANTOS FILHO',
  patrimonio_declarado: 300000.0, is_pep: true
});

// ── Companies ───────────────────────────────────────────
CREATE (co1:Company {
  cnpj: '11222333000181', razao_social: 'SILVA CONSTRUCOES LTDA',
  cnae_principal: '4120400', capital_social: 8000000.0,
  uf: 'SP', municipio: 'SAO PAULO'
});
CREATE (co2:Company {
  cnpj: '22333444000192', razao_social: 'COSTA ENGENHARIA SA',
  cnae_principal: '4120400', capital_social: 3000000.0,
  uf: 'SP', municipio: 'SAO PAULO'
});
CREATE (co3:Company {
  cnpj: '33444555000103', razao_social: 'PEREIRA SERVICOS LTDA',
  cnae_principal: '8130300', capital_social: 500000.0,
  uf: 'RJ', municipio: 'RIO DE JANEIRO'
});
CREATE (co4:Company {
  cnpj: '44555666000114', razao_social: 'FERREIRA TECNOLOGIA SA',
  cnae_principal: '6201501', capital_social: 2000000.0,
  uf: 'MG', municipio: 'BELO HORIZONTE'
});
CREATE (co5:Company {
  cnpj: '55666777000125', razao_social: 'SANTOS CONSULTORIA LTDA',
  cnae_principal: '7020400', capital_social: 1500000.0,
  uf: 'SP', municipio: 'SAO PAULO'
});

// ── Family Relationships ────────────────────────────────
// CARLOS ALBERTO → married to MARIA (family link for self-dealing)
MATCH (p1:Person {cpf: '11111111111'}), (p2:Person {cpf: '22222222222'})
CREATE (p1)-[:CONJUGE_DE]->(p2);

// JOAO → parent of ANA (family link for patrimony)
MATCH (p3:Person {cpf: '33333333333'}), (p4:Person {cpf: '44444444444'})
CREATE (p3)-[:PARENTE_DE]->(p4);

// ── Company Partnerships (SOCIO_DE) ─────────────────────
// MARIA is partner of SILVA CONSTRUCOES (family company)
MATCH (p2:Person {cpf: '22222222222'}), (co1:Company {cnpj: '11222333000181'})
CREATE (p2)-[:SOCIO_DE]->(co1);

// ANA is partner of PEREIRA SERVICOS (family company)
MATCH (p4:Person {cpf: '44444444444'}), (co3:Company {cnpj: '33444555000103'})
CREATE (p4)-[:SOCIO_DE]->(co3);

// ROBERTO is partner of SANTOS CONSULTORIA
MATCH (p5:Person {cpf: '55555555555'}), (co5:Company {cnpj: '55666777000125'})
CREATE (p5)-[:SOCIO_DE]->(co5);

// ── Contracts ───────────────────────────────────────────
CREATE (c1:Contract {
  contract_id: 'CTR-001', object: 'Construcao de ponte municipal',
  name: 'CTR-001 - Construcao de ponte municipal',
  value: 2500000.0, contracting_org: 'PREFEITURA SAO PAULO', date: '2024-03-15'
});
CREATE (c2:Contract {
  contract_id: 'CTR-002', object: 'Manutencao de vias publicas',
  name: 'CTR-002 - Manutencao de vias publicas',
  value: 800000.0, contracting_org: 'PREFEITURA SAO PAULO', date: '2024-06-01'
});
CREATE (c3:Contract {
  contract_id: 'CTR-003', object: 'Servicos de limpeza hospitalar',
  name: 'CTR-003 - Servicos de limpeza hospitalar',
  value: 1200000.0, contracting_org: 'PREFEITURA RIO DE JANEIRO', date: '2024-01-10'
});
CREATE (c4:Contract {
  contract_id: 'CTR-004', object: 'Sistema de gestao publica',
  name: 'CTR-004 - Sistema de gestao publica',
  value: 3500000.0, contracting_org: 'PREFEITURA BELO HORIZONTE', date: '2024-07-20'
});
CREATE (c5:Contract {
  contract_id: 'CTR-005', object: 'Consultoria em licitacoes',
  name: 'CTR-005 - Consultoria em licitacoes',
  value: 450000.0, contracting_org: 'PREFEITURA SAO PAULO', date: '2024-09-05'
});
CREATE (c6:Contract {
  contract_id: 'CTR-006', object: 'Reforma de escola municipal',
  name: 'CTR-006 - Reforma de escola municipal',
  value: 1800000.0, contracting_org: 'PREFEITURA SAO PAULO', date: '2024-04-12'
});
CREATE (c7:Contract {
  contract_id: 'CTR-007', object: 'Pavimentacao de estradas rurais',
  name: 'CTR-007 - Pavimentacao de estradas rurais',
  value: 950000.0, contracting_org: 'PREFEITURA SAO PAULO', date: '2024-11-01'
});
CREATE (c8:Contract {
  contract_id: 'CTR-008', object: 'Fornecimento de equipamentos medicos',
  name: 'CTR-008 - Fornecimento de equipamentos medicos',
  value: 600000.0, contracting_org: 'PREFEITURA RIO DE JANEIRO', date: '2024-02-28'
});
CREATE (c9:Contract {
  contract_id: 'CTR-009', object: 'Servicos de TI - datacenter',
  name: 'CTR-009 - Servicos de TI - datacenter',
  value: 2200000.0, contracting_org: 'PREFEITURA SAO PAULO', date: '2024-08-15'
});
CREATE (c10:Contract {
  contract_id: 'CTR-010', object: 'Auditoria contabil publica',
  name: 'CTR-010 - Auditoria contabil publica',
  value: 350000.0, contracting_org: 'PREFEITURA SAO PAULO', date: '2024-10-01'
});

// ── Amendment (for self-dealing pattern) ──────────────────
CREATE (a1:Amendment {
  amendment_id: 'EMD-001', type: 'Individual', function: 'Urbanismo',
  municipality: 'SAO PAULO', uf: 'SP',
  value_committed: 2500000.0, value_paid: 2400000.0
});

// ── Pattern p01: Self-dealing amendment ─────────────────
// CARLOS authored amendment → SILVA CONSTRUCOES (wife's company) won contract
MATCH (p1:Person {cpf: '11111111111'}), (a1:Amendment {amendment_id: 'EMD-001'})
CREATE (p1)-[:AUTOR_EMENDA]->(a1);

MATCH (co1:Company {cnpj: '11222333000181'}), (c1:Contract {contract_id: 'CTR-001'})
CREATE (co1)-[:VENCEU]->(c1);

// ── Pattern p05: Patrimony incompatibility ──────────────
// JOAO declared 800K but daughter ANA's company PEREIRA has 500K capital
// + also partner in another company with high capital (via additional link)
// The 10x ratio test: family_company_capital > patrimonio * 10
// Let's make JOAO have low patrimony but high-capital family companies
// Update JOAO's patrimony to be low
MATCH (p3:Person {cpf: '33333333333'})
SET p3.patrimonio_declarado = 50000.0;

// ANA also has shares in FERREIRA TECNOLOGIA (high capital)
MATCH (p4:Person {cpf: '44444444444'}), (co4:Company {cnpj: '44555666000114'})
CREATE (p4)-[:SOCIO_DE]->(co4);

// ── Pattern p06: Sanctioned still receiving ─────────────
CREATE (s1:Sanction {
  sanction_id: 'SAN-001', type: 'CEIS', date_start: '2023-01-01',
  date_end: '2025-12-31', reason: 'Irregularidade em licitacao',
  source: 'CEIS'
});

MATCH (co3:Company {cnpj: '33444555000103'}), (s1:Sanction {sanction_id: 'SAN-001'})
CREATE (co3)-[:SANCIONADA]->(s1);

// PEREIRA SERVICOS won contract AFTER sanction date
MATCH (co3:Company {cnpj: '33444555000103'}), (c3:Contract {contract_id: 'CTR-003'})
CREATE (co3)-[:VENCEU]->(c3);

MATCH (co3:Company {cnpj: '33444555000103'}), (c8:Contract {contract_id: 'CTR-008'})
CREATE (co3)-[:VENCEU]->(c8);

// ── Pattern p10: Donation-contract loop ─────────────────
// FERREIRA TECNOLOGIA donated to ROBERTO's campaign, then won contract from his org
CREATE (e1:Election {
  election_id: 'ELE-001', year: 2022, cargo: 'PREFEITO', uf: 'MG', municipio: 'BELO HORIZONTE'
});

MATCH (p5:Person {cpf: '55555555555'}), (e1:Election {election_id: 'ELE-001'})
CREATE (p5)-[:CANDIDATO_EM]->(e1);

MATCH (co4:Company {cnpj: '44555666000114'}), (p5:Person {cpf: '55555555555'})
CREATE (co4)-[:DOOU {valor: 100000.0, year: 2022}]->(p5);

MATCH (co4:Company {cnpj: '44555666000114'}), (c4:Contract {contract_id: 'CTR-004'})
CREATE (co4)-[:VENCEU]->(c4);

// ── Pattern p12: Contract concentration ─────────────────
// SILVA CONSTRUCOES dominates SAO PAULO contracts (>30% share)
MATCH (co1:Company {cnpj: '11222333000181'}), (c2:Contract {contract_id: 'CTR-002'})
CREATE (co1)-[:VENCEU]->(c2);

MATCH (co1:Company {cnpj: '11222333000181'}), (c5:Contract {contract_id: 'CTR-005'})
CREATE (co1)-[:VENCEU]->(c5);

MATCH (co1:Company {cnpj: '11222333000181'}), (c6:Contract {contract_id: 'CTR-006'})
CREATE (co1)-[:VENCEU]->(c6);

MATCH (co1:Company {cnpj: '11222333000181'}), (c7:Contract {contract_id: 'CTR-007'})
CREATE (co1)-[:VENCEU]->(c7);

MATCH (co1:Company {cnpj: '11222333000181'}), (c9:Contract {contract_id: 'CTR-009'})
CREATE (co1)-[:VENCEU]->(c9);

MATCH (co1:Company {cnpj: '11222333000181'}), (c10:Contract {contract_id: 'CTR-010'})
CREATE (co1)-[:VENCEU]->(c10);

// COSTA ENGENHARIA gets a few SAO PAULO contracts (for comparison)
MATCH (co2:Company {cnpj: '22333444000192'}), (c2:Contract {contract_id: 'CTR-002'})
CREATE (co2)-[:VENCEU]->(c2);

// SANTOS CONSULTORIA gets one SAO PAULO contract
MATCH (co5:Company {cnpj: '55666777000125'}), (c5:Contract {contract_id: 'CTR-005'})
CREATE (co5)-[:VENCEU]->(c5);

// ── Public Offices ──────────────────────────────────────
CREATE (po1:PublicOffice {
  cpf: '11111111111', name: 'Secretario de Obras', org: 'PREFEITURA SAO PAULO',
  salary: 25000.0
});

MATCH (p1:Person {cpf: '11111111111'}), (po1:PublicOffice {cpf: '11111111111'})
CREATE (p1)-[:RECEBEU_SALARIO]->(po1);

// ── Summary ─────────────────────────────────────────────
// Nodes: 5 Person, 5 Company, 10 Contract, 1 Amendment, 1 Sanction, 1 Election, 1 PublicOffice
// Relationships: 2 family, 3 SOCIO_DE, 1 AUTOR_EMENDA, 9 VENCEU,
//   1 SANCIONADA, 1 CANDIDATO_EM, 1 DOOU, 1 RECEBEU_SALARIO
// All 5 patterns should return results with this data

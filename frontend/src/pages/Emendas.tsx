import { useEffect, useState } from "react";
import styles from "./Emendas.module.css";
import { Spinner } from "../components/common/Spinner";
import { Link } from "react-router";

interface EmendaPayment {
  transfer_id: string;
  ob: string;
  date: string;
  year: string;
  month: string;
  amendment_type: string;
  special_transfer: string;
  economic_category: string;
  value: number;
}

interface CompanyBeneficiary {
  cnpj: string;
  razao_social: string;
}

interface EmendaRecord {
  payment: EmendaPayment;
  beneficiary: CompanyBeneficiary | null;
}

interface EmendasResponse {
  data: EmendaRecord[];
  skip: number;
  limit: number;
  total_returned: number;
}

// In development we could use process.env.VITE_API_URL or a dedicated api client.
// We'll fetch from the local server.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function Emendas() {
  const [data, setData] = useState<EmendasResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchEmendas() {
      try {
        const res = await fetch(`${API_URL}/api/v1/emendas/`);
        if (!res.ok) {
          throw new Error(`Error: ${res.statusText}`);
        }
        const json = await res.json();
        setData(json);
      } catch (e: unknown) {
        setError((e instanceof Error) ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    }
    fetchEmendas();
  }, []);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(val);
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Emendas Parlamentares</h1>
        <p>Visão de alto nível dos pagamentos extraídos via Governo Transparente (Neo4j)</p>
      </header>

      {loading && (
        <div className={styles.loadingState}>
          <Spinner />
          <p>Carregando emendas...</p>
        </div>
      )}

      {error && <div className={styles.errorState}>{error}</div>}

      {!loading && !error && data && (
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Ordem Bancária (OB)</th>
                <th>Data</th>
                <th>Tipo</th>
                <th>Valor</th>
                <th>Empresa Beneficiária (CNPJ)</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((record) => (
                <tr key={record.payment.transfer_id}>
                  <td>{record.payment.ob}</td>
                  <td>{record.payment.date}</td>
                  <td>
                    <span className={styles.badge}>{record.payment.amendment_type}</span>
                  </td>
                  <td className={styles.val}>{formatCurrency(record.payment.value)}</td>
                  <td>
                    {record.beneficiary ? (
                      <div className={styles.beneficiaryInfo}>
                        <strong>{record.beneficiary.razao_social}</strong>
                        <span className={styles.cnpjLabel}>{record.beneficiary.cnpj}</span>
                      </div>
                    ) : (
                      <span className={styles.cnpjLabel}>Sem Vínculo Específico</span>
                    )}
                  </td>
                  <td>
                    {record.beneficiary?.cnpj ? (
                      <Link to={`/app/analysis/cnpj_${record.beneficiary.cnpj}`} className={styles.actionBtn}>
                        Explorar Nó
                      </Link>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

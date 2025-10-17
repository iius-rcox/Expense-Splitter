import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

interface Transaction {
  transaction_id: string;
  transaction_type: 'car' | 'receipt';
  date: string | null;
  amount: number | null;
  employee_id: string | null;
  merchant: string | null;
  is_matched: boolean;
}

interface Match {
  match_id: string;
  confidence_score: number;
  status: string;
  exported: boolean;
  car_transaction: Transaction;
  receipt_transaction: Transaction;
}

export default function MatchingPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch all transactions
  const fetchTransactions = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/extract/transactions`);
      setTransactions(response.data.transactions);
    } catch (err) {
      console.error('Error fetching transactions:', err);
    }
  };

  // Fetch all matches
  const fetchMatches = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/match/matches`);
      setMatches(response.data.matches);
    } catch (err) {
      console.error('Error fetching matches:', err);
    }
  };

  // Run matching algorithm
  const runMatching = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE}/api/match/run`);
      setMatches(response.data.matches);
      await fetchTransactions(); // Refresh to update matched status
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || 'Error running matching');
    } finally {
      setLoading(false);
    }
  };

  // Approve match
  const approveMatch = async (matchId: string) => {
    try {
      await axios.patch(`${API_BASE}/api/match/matches/${matchId}`, {
        status: 'approved'
      });
      await fetchMatches();
    } catch (err) {
      console.error('Error approving match:', err);
    }
  };

  // Export match
  const exportMatch = async (matchId: string) => {
    try {
      const response = await axios.post(`${API_BASE}/api/export/match/${matchId}`);
      alert(`Exported successfully: ${response.data.export_path}`);
      await fetchMatches();
    } catch (err) {
      console.error('Error exporting match:', err);
    }
  };

  useEffect(() => {
    fetchTransactions();
    fetchMatches();
  }, []);

  const unmatched = transactions.filter(t => !t.is_matched);
  const carUnmatched = unmatched.filter(t => t.transaction_type === 'car');
  const receiptUnmatched = unmatched.filter(t => t.transaction_type === 'receipt');

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold">Transaction Matching</h1>
          <p className="text-muted-foreground mt-2">
            Review extracted transactions and run matching algorithm
          </p>
        </header>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-card p-4 rounded-lg border">
            <div className="text-2xl font-bold">{transactions.length}</div>
            <div className="text-sm text-muted-foreground">Total Transactions</div>
          </div>
          <div className="bg-card p-4 rounded-lg border">
            <div className="text-2xl font-bold">{carUnmatched.length}</div>
            <div className="text-sm text-muted-foreground">Unmatched CAR</div>
          </div>
          <div className="bg-card p-4 rounded-lg border">
            <div className="text-2xl font-bold">{receiptUnmatched.length}</div>
            <div className="text-sm text-muted-foreground">Unmatched Receipts</div>
          </div>
          <div className="bg-card p-4 rounded-lg border">
            <div className="text-2xl font-bold">{matches.length}</div>
            <div className="text-sm text-muted-foreground">Matches Found</div>
          </div>
        </div>

        {/* Run Matching Button */}
        <div className="mb-8">
          <button
            onClick={runMatching}
            disabled={loading || carUnmatched.length === 0 || receiptUnmatched.length === 0}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Running Matching...' : 'Run Matching Algorithm'}
          </button>
          {error && (
            <div className="mt-2 text-sm text-destructive">{error}</div>
          )}
        </div>

        {/* Matches */}
        {matches.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4">Matches ({matches.length})</h2>
            <div className="space-y-4">
              {matches.map(match => (
                <div key={match.match_id} className="bg-card p-6 rounded-lg border">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <div className="text-lg font-semibold">
                        Confidence: {(match.confidence_score * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Status: {match.status}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {match.status === 'pending' && (
                        <button
                          onClick={() => approveMatch(match.match_id)}
                          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                        >
                          Approve
                        </button>
                      )}
                      {match.status === 'approved' && !match.exported && (
                        <button
                          onClick={() => exportMatch(match.match_id)}
                          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                        >
                          Export PDF
                        </button>
                      )}
                      {match.exported && (
                        <span className="px-4 py-2 bg-gray-200 text-gray-700 rounded text-sm">
                          Exported
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-6">
                    {/* CAR Transaction */}
                    <div>
                      <div className="text-sm font-semibold mb-2 text-blue-600">CAR Transaction</div>
                      <div className="space-y-1 text-sm">
                        <div><span className="font-medium">Date:</span> {match.car_transaction.date || 'N/A'}</div>
                        <div><span className="font-medium">Amount:</span> ${match.car_transaction.amount?.toFixed(2) || 'N/A'}</div>
                        <div><span className="font-medium">Employee:</span> {match.car_transaction.employee_id || 'N/A'}</div>
                        <div><span className="font-medium">Merchant:</span> {match.car_transaction.merchant || 'N/A'}</div>
                      </div>
                    </div>

                    {/* Receipt Transaction */}
                    <div>
                      <div className="text-sm font-semibold mb-2 text-green-600">Receipt Transaction</div>
                      <div className="space-y-1 text-sm">
                        <div><span className="font-medium">Date:</span> {match.receipt_transaction.date || 'N/A'}</div>
                        <div><span className="font-medium">Amount:</span> ${match.receipt_transaction.amount?.toFixed(2) || 'N/A'}</div>
                        <div><span className="font-medium">Employee:</span> {match.receipt_transaction.employee_id || 'N/A'}</div>
                        <div><span className="font-medium">Merchant:</span> {match.receipt_transaction.merchant || 'N/A'}</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unmatched Transactions */}
        {unmatched.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold mb-4">Unmatched Transactions ({unmatched.length})</h2>
            <div className="grid grid-cols-2 gap-6">
              {/* CAR */}
              <div>
                <h3 className="text-lg font-semibold mb-2 text-blue-600">CAR ({carUnmatched.length})</h3>
                <div className="space-y-2">
                  {carUnmatched.map(t => (
                    <div key={t.transaction_id} className="bg-card p-3 rounded border text-sm">
                      <div>{t.date || 'No date'} - ${t.amount?.toFixed(2) || 'N/A'}</div>
                      <div className="text-muted-foreground">{t.merchant || 'No merchant'}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Receipt */}
              <div>
                <h3 className="text-lg font-semibold mb-2 text-green-600">Receipt ({receiptUnmatched.length})</h3>
                <div className="space-y-2">
                  {receiptUnmatched.map(t => (
                    <div key={t.transaction_id} className="bg-card p-3 rounded border text-sm">
                      <div>{t.date || 'No date'} - ${t.amount?.toFixed(2) || 'N/A'}</div>
                      <div className="text-muted-foreground">{t.merchant || 'No merchant'}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

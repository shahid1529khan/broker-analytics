import React, { useState, useEffect } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ArrowUpRight, ArrowDownRight, FolderOpen, Download } from 'lucide-react';
import { apiClient } from '../api/client';
import { cn } from '../lib/utils';

export default function Dashboard() {
  const [clientId, setClientId] = useState<string>('');
  const [clients, setClients] = useState<any[]>([]);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiClient('/clients/').then(data => {
      setClients(data || []);
      if (data?.length > 0) setClientId(data[0].id);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    setData(null);
    apiClient(`/analytics/${clientId}/dashboard-summary`)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [clientId]);

  const handleDownloadExcel = async () => {
    if (!clientId) return;
    try {
      const blob = await apiClient(`/export/${clientId}/report.xlsx`);
      const url = URL.createObjectURL(blob as any);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${clientId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Failed to download Excel", e);
    }
  };

  const handleDownloadPDF = async () => {
    if (!clientId) return;
    try {
      const blob = await apiClient(`/export/${clientId}/report.pdf`);
      const url = URL.createObjectURL(blob as any);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${clientId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Failed to download PDF", e);
    }
  };

  if (loading && !data) {
    return <div className="animate-pulse">Loading dashboard...</div>;
  }
  
  if (!clientId && clients.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
        <FolderOpen className="mx-auto h-10 w-10 text-slate-400" />
        <h2 className="mt-3 text-base font-semibold text-slate-900">No clients yet</h2>
        <p className="mt-1 text-sm text-slate-500">
          Add a broker client before viewing dashboard analytics.
        </p>
      </div>
    );
  }
  
  if (!data || data.error || !data.book_size || !data.trail_income || !data.average_loan_size || !data.lender_concentration) {
    return (
      <div className="space-y-6">
        <div className="w-72">
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Select Client</label>
          <select 
            value={clientId}
            onChange={e => setClientId(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-md shadow-sm py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500"
          >
            <option value="" disabled>Select a client</option>
            {clients.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
          <FolderOpen className="mx-auto h-10 w-10 text-slate-400" />
          <h2 className="mt-3 text-base font-semibold text-slate-900">No dashboard data available</h2>
          <p className="mt-1 text-sm text-slate-500">
            Upload and process a commission statement for this client to populate analytics.
          </p>
        </div>
      </div>
    );
  }

  const latestBookEntry = data.book_size.trend_data.at(-1);
  const previousBookEntry = data.book_size.trend_data.at(-2);
  const currentBookSize = latestBookEntry?.total_balance ?? 0;
  const bookChangePct =
    latestBookEntry && previousBookEntry?.total_balance
      ? ((latestBookEntry.total_balance - previousBookEntry.total_balance) / previousBookEntry.total_balance) * 100
      : null;
  const bookChangeIsPositive = bookChangePct === null || bookChangePct >= 0;
  
  const lastTrailEntry = data.trail_income.trend_data.at(-1);
  const currentTrail = lastTrailEntry?.trail_income ?? 0;
  const momPct = lastTrailEntry?.mom_change_pct ?? 0;
  const isPositive = momPct >= 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="w-72">
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Select Client</label>
          <select 
            value={clientId}
            onChange={e => setClientId(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-md shadow-sm py-2 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500"
          >
            <option value="" disabled>Select a client</option>
            {clients.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-3">
          <button onClick={handleDownloadExcel} className="inline-flex items-center gap-2 bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-md font-medium text-sm hover:bg-slate-50 shadow-sm transition-colors">
            <Download className="w-4 h-4" /> Export Excel
          </button>
          <button onClick={handleDownloadPDF} className="inline-flex items-center gap-2 bg-slate-900 border border-transparent text-white px-4 py-2 rounded-md font-medium text-sm hover:bg-slate-800 shadow-sm transition-colors">
            <Download className="w-4 h-4" /> Generate PDF Report
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* KPI Cards */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-sm font-medium text-slate-500">Total Book Size</h3>
          <div className="mt-2 flex items-baseline gap-2">
            <p className="text-3xl font-semibold text-slate-900">
              ${(currentBookSize / 1000000).toFixed(2)}M
            </p>
            {bookChangePct !== null && (
              <span className={cn(
                "inline-flex items-center gap-1 text-sm font-medium px-2 py-0.5 rounded-full",
                bookChangeIsPositive ? "text-emerald-600 bg-emerald-50" : "text-rose-600 bg-rose-50"
              )}>
                {bookChangeIsPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                {Math.abs(bookChangePct).toFixed(1)}%
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {bookChangePct === null ? 'Upload another period to calculate movement' : data.book_size.growth_trend}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-sm font-medium text-slate-500">Trail Income</h3>
          <div className="mt-2 flex items-baseline gap-2">
            <p className="text-3xl font-semibold text-slate-900">
              ${currentTrail.toLocaleString()}
            </p>
            <span className={cn("inline-flex items-center gap-1 text-sm font-medium px-2 py-0.5 rounded-full", isPositive ? "text-emerald-600 bg-emerald-50" : "text-rose-600 bg-rose-50")}>
              {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />} {Math.abs(momPct)}%
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">MoM Growth</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-sm font-medium text-slate-500">Average Loan Size</h3>
          <div className="mt-2 flex items-baseline gap-2">
            <p className="text-3xl font-semibold text-slate-900">
              ${Math.round(data.average_loan_size.overall_average).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col">
          <h3 className="text-base font-semibold text-slate-900 mb-6">Book Growth (12 Months)</h3>
          <div className="flex-1 min-h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.book_size.trend_data}>
                <defs>
                  <linearGradient id="colorBook" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="period" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                <YAxis 
                  tickFormatter={val => `$${(val/1000000).toFixed(1)}M`} 
                  tickLine={false} 
                  axisLine={false} 
                  tick={{ fontSize: 12, fill: '#64748b' }} 
                  width={60}
                />
                <Tooltip 
                  formatter={(value: number) => [`$${value.toLocaleString()}`, "Book Size"]}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Area type="monotone" dataKey="total_balance" stroke="#0ea5e9" strokeWidth={2} fillOpacity={1} fill="url(#colorBook)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col">
          <h3 className="text-base font-semibold text-slate-900 mb-6">Trail Income Trend</h3>
          <div className="flex-1 min-h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.trail_income.trend_data}>
                <defs>
                  <linearGradient id="colorTrail" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="period" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                <YAxis 
                  tickFormatter={val => `$${val}`} 
                  tickLine={false} 
                  axisLine={false} 
                  tick={{ fontSize: 12, fill: '#64748b' }} 
                  width={60}
                />
                <Tooltip 
                  formatter={(value: number) => [`$${value.toLocaleString()}`, "Trail Income"]}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Area type="monotone" dataKey="trail_income" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorTrail)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      {/* Tables Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-base font-semibold text-slate-900">Lender Concentration</h3>
          <p className="mt-1 text-sm text-slate-500">Distribution of book size across lenders.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Lender Name</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Balance</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">% of Book</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {data.lender_concentration.ranked_table.map((row: any, i: number) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                    {row.lender_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                    ${row.total_balance.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-900">{row.percentage.toFixed(1)}%</span>
                    <div className="w-32 bg-slate-200 rounded-full h-2 overflow-hidden">
                      <div className="bg-cyan-500 h-2 rounded-full" style={{ width: `${row.percentage}%` }}></div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

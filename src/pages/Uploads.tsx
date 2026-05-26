import React, { useState, useRef, useEffect } from 'react';
import { Upload as UploadIcon, FileDown, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import { apiClient } from '../api/client';
import { supabase } from '../lib/supabase';

export default function Uploads() {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploads, setUploads] = useState<any[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  const [aggregators, setAggregators] = useState<any[]>([]);
  const [clientId, setClientId] = useState('');
  const [aggregatorId, setAggregatorId] = useState('');
  const [periodMonth, setPeriodMonth] = useState(new Date().toISOString().slice(0, 7)); // YYYY-MM
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Fetch clients and aggregators
    const fetchOptions = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) return;
        
        const clientData = await apiClient('/clients/');
        setClients(clientData || []);
        if (clientData?.length > 0) setClientId(clientData[0].id);
        
        // Fetch aggregators since there's no backend route, query Supabase
        const aggData = await apiClient('/aggregators/');
        setAggregators(aggData || []);
        if (aggData?.length > 0) setAggregatorId(aggData[0].id);

        if (clientData?.length > 0) {
          const uploadsData = await apiClient(`/uploads/?client_id=${clientData[0].id}`);
          setUploads(uploadsData || []);
        }
      } catch (error) {
        console.error('Failed to fetch options', error);
      }
    };
    fetchOptions();
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragOver(true);
  };
  const handleDragLeave = () => setIsDragOver(false);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const fetchUploads = async () => {
    if (!clientId) return;
    try {
       const data = await apiClient(`/uploads/?client_id=${clientId}`);
       setUploads(data || []);
    } catch (e) {
       console.error("Failed to fetch uploads", e);
    }
  };

  const pollUploadStatus = (id: string) => {
    pollingRef.current = setInterval(async () => {
      try {
        const data = await apiClient(`/uploads/${id}`);
        setUploads(prev => prev.map(u => u.id === id ? data : u));
        if (['completed', 'review_required', 'failed'].includes(data.status)) {
          clearInterval(pollingRef.current!);
          setUploading(false);
        }
      } catch (e) {
        clearInterval(pollingRef.current!);
        setUploading(false);
      }
    }, 2000); 
  };

  const handleFileChange = async (file: File) => {
    if (!clientId || !aggregatorId || !periodMonth) {
      alert("Please select a client, aggregator, and period before uploading.");
      return;
    }
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('client_id', clientId);
      formData.append('aggregator_id', aggregatorId);
      formData.append('period_month', periodMonth);

      const res = await apiClient('/uploads/', {
        method: 'POST',
        body: formData,
      });

      if (res?.upload_id) {
        // Add optimistic pending upload to list
        setUploads(prev => [{
           id: res.upload_id,
           file_name: file.name,
           created_at: new Date().toISOString(),
           status: 'pending',
           row_count: 0,
           flagged_row_count: 0
        }, ...prev]);
        pollUploadStatus(res.upload_id);
      } else {
        alert("Upload failed. Please check the backend logs.");
        setUploading(false);
      }
    } catch (error) {
      console.error("Upload failed", error);
      alert("Upload failed.");
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileChange(file);
  };

  return (
    <div className="max-w-4xl space-y-8">
      
      {/* Upload Zone */}
      <section>
        <div className="flex justify-between items-end mb-4">
          <h2 className="text-base font-semibold text-slate-900">New Statement Upload</h2>
          
          <div className="flex gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Client</label>
              <select 
                value={clientId} 
                onChange={e => {
                   setClientId(e.target.value);
                   apiClient(`/uploads/?client_id=${e.target.value}`).then(setUploads).catch(console.error);
                }}
                className="bg-white border border-slate-300 rounded-md py-1.5 px-3 text-sm focus:ring-cyan-500 focus:border-cyan-500"
              >
                <option value="">Select Client</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Aggregator</label>
              <select 
                value={aggregatorId} 
                onChange={e => setAggregatorId(e.target.value)}
                className="bg-white border border-slate-300 rounded-md py-1.5 px-3 text-sm focus:ring-cyan-500 focus:border-cyan-500"
              >
                <option value="">Select Aggregator</option>
                {aggregators.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Period</label>
              <input 
                type="month" 
                value={periodMonth}
                onChange={e => setPeriodMonth(e.target.value)}
                className="bg-white border border-slate-300 rounded-md py-1.5 px-3 text-sm w-32 focus:ring-cyan-500 focus:border-cyan-500"
              />
            </div>
          </div>
        </div>

        <div 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !uploading && fileInputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-xl p-10 flex flex-col items-center text-center transition-colors",
            uploading ? "opacity-50 cursor-not-allowed border-slate-300" : "cursor-pointer",
            isDragOver && !uploading ? "border-cyan-500 bg-cyan-50" : "border-slate-300 bg-white hover:border-cyan-400 hover:bg-slate-50"
          )}
        >
          <div className="w-12 h-12 bg-slate-100 rounded-full flex justify-center items-center mb-4">
            {uploading ? (
               <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-600"></div>
            ) : (
               <UploadIcon className="w-6 h-6 text-slate-500" />
            )}
          </div>
          <h3 className="text-sm font-semibold text-slate-900 mb-1">
            {uploading ? 'Uploading...' : 'Click to upload or drag and drop'}
          </h3>
          <p className="text-xs text-slate-500 mb-4">PDF, XLSX, or XLS (max. 50MB)</p>
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            accept=".pdf,.xlsx,.xls"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
              // Reset input value so same file can be uploaded again if needed
              if (fileInputRef.current) fileInputRef.current.value = '';
            }} 
          />
          <button 
            disabled={uploading}
            className="bg-white border border-slate-300 shadow-sm text-slate-700 px-4 py-2 rounded-md font-medium text-sm hover:bg-slate-50 transition-colors disabled:opacity-50"
          >
            Select File
          </button>
        </div>
      </section>

      {/* Upload History */}
      <section>
        <h2 className="text-base font-semibold text-slate-900 mb-4">Recent Uploads</h2>
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <ul className="divide-y divide-slate-200">
            {uploads.length === 0 ? (
               <li className="p-8 text-center text-slate-500 text-sm">No uploads found for this client.</li>
            ) : uploads.map(upload => (
              <li key={upload.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <FileDown className="w-5 h-5 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">{upload.file_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Uploaded {new Date(upload.created_at).toLocaleDateString()} • {upload.row_count || 0} rows processed
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  {upload.status === 'completed' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                      <CheckCircle className="w-3.5 h-3.5" /> Completed
                    </span>
                  )}
                  {upload.status === 'failed' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      <AlertCircle className="w-3.5 h-3.5" /> Failed
                    </span>
                  )}
                  {upload.status === 'review_required' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                      <AlertCircle className="w-3.5 h-3.5" /> {upload.flagged_row_count} Alerts
                    </span>
                  )}
                  {upload.status === 'pending' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                      <Clock className="w-3.5 h-3.5 animate-pulse" /> Processing
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

    </div>
  )
}

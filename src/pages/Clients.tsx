import React, { useState, useEffect } from 'react';
import { Plus, Building, User, Phone, Mail, X } from 'lucide-react';
import { apiClient } from '../api/client';

const emptyForm = {
  name: '',
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  status: 'active',
  notes: '',
};

export default function Clients() {
  const [clients, setClients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    apiClient('/clients/')
      .then(data => setClients(data || []))
      .catch(err => console.error('Failed to fetch clients', err))
      .finally(() => setLoading(false));
  }, []);

  const handleChange = (field: string, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const openCreateModal = () => {
    setForm(emptyForm);
    setError(null);
    setShowCreateModal(true);
  };

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setError('Client name is required.');
      return;
    }

    setSaving(true);
    setError(null);

    const payload = {
      ...form,
      name: form.name.trim(),
      contact_name: form.contact_name.trim() || null,
      contact_email: form.contact_email.trim() || null,
      contact_phone: form.contact_phone.trim() || null,
      notes: form.notes.trim() || null,
    };

    try {
      const created = await apiClient('/clients/', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (!created) {
        setError('Client could not be created. Please check the backend logs.');
        return;
      }

      setClients(prev => [...prev, created]);
      setShowCreateModal(false);
      setForm(emptyForm);
    } catch (err) {
      console.error('Failed to create client', err);
      setError('Client could not be created.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 pt-4 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-1/4"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
          {[1, 2, 3].map(i => <div key={i} className="h-48 bg-slate-200 rounded-xl"></div>)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Broker Clients</h2>
          <p className="text-sm text-slate-500">
            Manage the broker clients associated with your organisation.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 bg-cyan-600 text-white px-4 py-2 rounded-md font-medium text-sm hover:bg-cyan-700 shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Client
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {clients.length === 0 ? (
          <div className="col-span-full border-2 border-dashed border-slate-200 rounded-xl p-8 text-center bg-slate-50">
            <p className="text-slate-500 font-medium">
              No clients found. Add your first broker client to get started.
            </p>
          </div>
        ) : clients.map(client => (
          <div
            key={client.id}
            className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:border-cyan-300 transition-colors group"
          >
            <div className="p-6">
              <div className="w-12 h-12 bg-cyan-50 text-cyan-700 rounded-lg flex items-center justify-center mb-4 group-hover:bg-cyan-600 group-hover:text-white transition-colors">
                <Building className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 truncate">{client.name}</h3>
              <div className="mt-4 space-y-2">
                {client.contact_name && (
                  <div className="flex items-center text-sm text-slate-600">
                    <User className="w-4 h-4 mr-2 text-slate-400 shrink-0" />
                    {client.contact_name}
                  </div>
                )}
                {client.contact_phone && (
                  <div className="flex items-center text-sm text-slate-600">
                    <Phone className="w-4 h-4 mr-2 text-slate-400 shrink-0" />
                    {client.contact_phone}
                  </div>
                )}
                {client.contact_email && (
                  <div className="flex items-center text-sm text-slate-600">
                    <Mail className="w-4 h-4 mr-2 text-slate-400 shrink-0" />
                    {client.contact_email}
                  </div>
                )}
              </div>
            </div>
            <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-sm">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                client.status === 'active' ? 'bg-emerald-100 text-emerald-800' :
                client.status === 'sold' ? 'bg-slate-100 text-slate-600' :
                client.status === 'under offer' ? 'bg-amber-100 text-amber-800' :
                'bg-slate-100 text-slate-600'
              }`}>
                {client.status || 'active'}
              </span>
              {client.notes && (
                <span className="text-slate-400 text-xs truncate max-w-[120px]">{client.notes}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <h3 className="text-base font-semibold text-slate-900">Add Client</h3>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateClient} className="space-y-4 px-6 py-5">
              {error && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {error}
                </div>
              )}

              <div>
                <label htmlFor="client-name" className="block text-sm font-medium text-slate-700">
                  Client name
                </label>
                <input
                  id="client-name"
                  value={form.name}
                  onChange={e => handleChange('name', e.target.value)}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  required
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="contact-name" className="block text-sm font-medium text-slate-700">
                    Contact name
                  </label>
                  <input
                    id="contact-name"
                    value={form.contact_name}
                    onChange={e => handleChange('contact_name', e.target.value)}
                    className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  />
                </div>

                <div>
                  <label htmlFor="contact-phone" className="block text-sm font-medium text-slate-700">
                    Phone
                  </label>
                  <input
                    id="contact-phone"
                    value={form.contact_phone}
                    onChange={e => handleChange('contact_phone', e.target.value)}
                    className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="contact-email" className="block text-sm font-medium text-slate-700">
                    Email
                  </label>
                  <input
                    id="contact-email"
                    type="email"
                    value={form.contact_email}
                    onChange={e => handleChange('contact_email', e.target.value)}
                    className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  />
                </div>

                <div>
                  <label htmlFor="client-status" className="block text-sm font-medium text-slate-700">
                    Status
                  </label>
                  <select
                    id="client-status"
                    value={form.status}
                    onChange={e => handleChange('status', e.target.value)}
                    className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  >
                    <option value="active">Active</option>
                    <option value="pending documents">Pending documents</option>
                    <option value="under offer">Under offer</option>
                    <option value="sold">Sold</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="client-notes" className="block text-sm font-medium text-slate-700">
                  Notes
                </label>
                <textarea
                  id="client-notes"
                  rows={3}
                  value={form.notes}
                  onChange={e => handleChange('notes', e.target.value)}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-200 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-cyan-700 disabled:opacity-50"
                >
                  <Plus className="h-4 w-4" />
                  {saving ? 'Saving...' : 'Create Client'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

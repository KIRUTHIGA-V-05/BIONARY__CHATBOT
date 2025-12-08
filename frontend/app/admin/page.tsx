// app/admin/page.tsx
'use client';
import { useState } from 'react';
import axios from 'axios';

export default function AdminPage() {
  const [formData, setFormData] = useState({
    name_of_event: '',
    event_domain: '',
    date_of_event: '',
    description_insights: '',
    time_of_event: '',
    venue: '',
    mode_of_event: 'Offline',
    registration_fee: '0',
    speakers: '',
    perks: '',
    event_highlights: '' // We merge this in backend, but keep input for clarity
  });
  const [status, setStatus] = useState<{type: 'success' | 'error' | '', msg: string}>({type: '', msg: ''});
  const [loading, setLoading] = useState(false);

  const handleChange = (e: any) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatus({type: '', msg: ''});

    try {
      const res = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/add-event`, formData);
      setStatus({type: 'success', msg: `Success! Event ID: ${res.data.event_id}`});
      // Optional: Clear form here
    } catch (error: any) {
      const errMsg = error.response?.data?.detail || "Submission failed";
      setStatus({type: 'error', msg: errMsg});
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">Add New Event</h1>
          <a href="/" className="text-blue-600 hover:underline">Back to Search</a>
        </div>

        {status.msg && (
          <div className={`p-4 mb-6 rounded ${status.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {status.msg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Essential Fields */}
          <div className="col-span-2 md:col-span-1">
            <label className="block text-sm font-bold mb-2">Event Name *</label>
            <input name="name_of_event" required onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div className="col-span-2 md:col-span-1">
            <label className="block text-sm font-bold mb-2">Domain *</label>
            <input name="event_domain" placeholder="AI / ML" required onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div className="col-span-2 md:col-span-1">
            <label className="block text-sm font-bold mb-2">Date (YYYY-MM-DD) *</label>
            <input name="date_of_event" type="date" required onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          
          {/* Semantic Text Fields */}
          <div className="col-span-2">
            <label className="block text-sm font-bold mb-2">Description (Used for AI Search) *</label>
            <textarea name="description_insights" required onChange={handleChange} className="w-full p-2 border rounded h-24" />
          </div>
          
          {/* Optional Fields */}
          <div>
            <label className="block text-sm font-medium mb-1">Time</label>
            <input name="time_of_event" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Venue</label>
            <input name="venue" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          
          <div className="col-span-2 mt-4">
            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-green-600 text-white font-bold py-3 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? 'Generating Embeddings & Saving...' : 'Submit Event'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
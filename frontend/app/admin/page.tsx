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
    faculty_coordinators: '',
    student_coordinators: '',
    venue: '',
    mode_of_event: 'Offline',
    registration_fee: '0',
    speakers: '',
    perks: '',
    collaboration: '' // New Field
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
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/add-event`, formData);
      setStatus({type: 'success', msg: `Success! "${formData.name_of_event}" added.`});
      // Optional: Clear form or redirect
    } catch (error: any) {
      console.error(error);
      const errMsg = error.response?.data?.detail || "Submission failed";
      setStatus({type: 'error', msg: errMsg});
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto bg-white rounded-xl shadow-lg p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">Add New Event</h1>
          <a href="/" className="text-blue-600 hover:underline">Back to Chat</a>
        </div>

        {status.msg && (
          <div className={`p-4 mb-6 rounded ${status.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {status.msg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* --- Section 1: Core Details --- */}
          <div className="col-span-2 border-b pb-2 mb-2 text-lg font-semibold text-gray-700">Core Details</div>
          
          <div>
            <label className="block text-sm font-bold mb-1">Event Name *</label>
            <input name="name_of_event" required onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-bold mb-1">Domain *</label>
            <input name="event_domain" placeholder="AI / ML" required onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-bold mb-1">Date (YYYY-MM-DD) *</label>
            <input name="date_of_event" type="date" required onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Time</label>
            <input name="time_of_event" placeholder="e.g. 9 AM - 4 PM" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>

          {/* --- Section 2: Logistics --- */}
          <div className="col-span-2 border-b pb-2 mb-2 mt-4 text-lg font-semibold text-gray-700">Logistics</div>

          <div>
            <label className="block text-sm font-medium mb-1">Venue</label>
            <input name="venue" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Mode</label>
            <select name="mode_of_event" onChange={handleChange} className="w-full p-2 border rounded">
              <option value="Offline">Offline</option>
              <option value="Online">Online</option>
              <option value="Hybrid">Hybrid</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Registration Fee</label>
            <input name="registration_fee" type="number" defaultValue="0" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Collaboration</label>
            <input name="collaboration" placeholder="e.g. GDSC, IEEE or N/A" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>

          {/* --- Section 3: People --- */}
          <div className="col-span-2 border-b pb-2 mb-2 mt-4 text-lg font-semibold text-gray-700">People</div>

          <div>
            <label className="block text-sm font-medium mb-1">Faculty Coordinators</label>
            <input name="faculty_coordinators" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Student Coordinators</label>
            <input name="student_coordinators" onChange={handleChange} className="w-full p-2 border rounded" />
          </div>
          <div className="col-span-2">
            <label className="block text-sm font-medium mb-1">Speakers</label>
            <input name="speakers" placeholder="Name, Designation..." onChange={handleChange} className="w-full p-2 border rounded" />
          </div>

          {/* --- Section 4: Content (For AI) --- */}
          <div className="col-span-2 border-b pb-2 mb-2 mt-4 text-lg font-semibold text-gray-700">Content (For AI Search)</div>

          <div className="col-span-2">
            <label className="block text-sm font-bold mb-1">Description & Insights *</label>
            <textarea name="description_insights" required onChange={handleChange} className="w-full p-2 border rounded h-32" placeholder="Detailed description of what happened..." />
          </div>
          <div className="col-span-2">
            <label className="block text-sm font-medium mb-1">Perks</label>
            <textarea name="perks" onChange={handleChange} className="w-full p-2 border rounded h-20" placeholder="OD, Certificates, Food..." />
          </div>
          
          <div className="col-span-2 mt-6">
            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-blue-600 text-white font-bold py-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {loading ? 'Generating Embeddings & Saving...' : 'Submit Event to Database'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
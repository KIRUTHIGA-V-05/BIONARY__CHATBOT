// app/page.tsx
'use client';
import { useState } from 'react';
import axios from 'axios';

export default function ChatPage() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    
    setLoading(true);
    setAnswer('');
    
    try {
      const res = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
        query: query
      });
      setAnswer(res.data.answer);
    } catch (error) {
      console.error(error);
      setAnswer("Error connecting to the agent.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-8">
      <h1 className="text-4xl font-bold text-blue-600 mb-2">Bionary Search Agent</h1>
      <p className="text-gray-600 mb-8">Ask anything about past club events</p>

      <div className="w-full max-w-2xl">
        <form onSubmit={handleSearch} className="flex gap-2 mb-6">
          <input
            type="text"
            className="flex-1 p-3 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="e.g., What events covered AI?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button 
            type="submit" 
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-blue-400"
          >
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </form>

        {answer && (
          <div className="bg-white p-6 rounded-xl shadow-md border border-gray-100 prose max-w-none">
            <h3 className="text-gray-500 text-sm font-uppercase mb-2 font-bold">AGENT RESPONSE</h3>
            <div className="text-gray-800 whitespace-pre-wrap">{answer}</div>
          </div>
        )}
      </div>
      
      <div className="mt-12">
        <a href="/admin" className="text-sm text-gray-400 hover:text-gray-600 underline">Go to Admin Dashboard</a>
      </div>
    </div>
  );
}
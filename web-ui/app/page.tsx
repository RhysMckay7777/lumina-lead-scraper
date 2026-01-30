'use client';
import { useState } from 'react';

export default function Home() {
  const [url, setUrl] = useState('https://dexscreener.com/solana?rankBy=trendingScoreM5&order=desc');
  const [apiId, setApiId] = useState('');
  const [apiHash, setApiHash] = useState('');
  const [phone, setPhone] = useState('');
  const [command, setCommand] = useState('');

  const generateCommand = () => {
    if (!url || !apiId || !apiHash || !phone) {
      alert('Please fill all fields');
      return;
    }
    setCommand(`cd ~/lumina-lead-scraper-v2\n./run_scraper.sh "${url}" ${apiId} ${apiHash} "${phone}"`);
  };

  const examples = [
    { name: 'Trending 5min', url: 'https://dexscreener.com/solana?rankBy=trendingScoreM5&order=desc' },
    { name: 'High Volume', url: 'https://dexscreener.com/solana?rankBy=volume&order=desc' },
    { name: 'New + Liquid', url: 'https://dexscreener.com/solana?minLiq=10000&maxAge=7' },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4 sm:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2">🚀 Lead Scraper v2</h1>
            <p className="text-gray-600">DEXScreener → Telegram → DMs</p>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">DEXScreener URL</label>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="https://dexscreener.com/solana?..."
              />
              <div className="mt-2 flex gap-2 flex-wrap">
                {examples.map(ex => (
                  <button key={ex.name} onClick={() => setUrl(ex.url)}
                    className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200">
                    {ex.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">API ID</label>
                <input type="text" value={apiId} onChange={(e) => setApiId(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="12345678" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">API Hash</label>
                <input type="text" value={apiHash} onChange={(e) => setApiHash(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="abcdef..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Phone</label>
                <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="+44..." />
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">💡 Get credentials: <a href="https://my.telegram.org/apps" target="_blank" className="underline font-medium">my.telegram.org/apps</a></p>
            </div>

            <button onClick={generateCommand}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold py-4 px-6 rounded-lg hover:from-blue-700 hover:to-indigo-700 shadow-lg transition-all">
              Generate Command
            </button>

            {command && (
              <div className="bg-gray-900 text-green-400 p-6 rounded-lg font-mono text-sm">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-gray-400">Run this:</span>
                  <button onClick={() => navigator.clipboard.writeText(command)}
                    className="text-xs bg-gray-700 px-3 py-1 rounded hover:bg-gray-600">Copy</button>
                </div>
                <pre className="whitespace-pre-wrap break-all">{command}</pre>
              </div>
            )}

            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="font-semibold text-gray-900 mb-3">What It Does:</h3>
              <ul className="space-y-2 text-gray-700 text-sm">
                <li>1. Scrapes 150 tokens (~8 min)</li>
                <li>2. Joins Telegram groups (~1-2h)</li>
                <li>3. Finds admins (~30 min)</li>
                <li>4. Sends DMs (~1-2h)</li>
              </ul>
              <p className="mt-4 pt-4 border-t text-sm text-gray-600">
                <strong>Time:</strong> 3-4 hours • <strong>Output:</strong> leads_TIMESTAMP.csv
              </p>
            </div>

            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">40-60%</div>
                <div className="text-xs text-gray-600">Telegram</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-green-600">100%</div>
                <div className="text-xs text-gray-600">Twitter</div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">100%</div>
                <div className="text-xs text-gray-600">Website</div>
              </div>
            </div>

            <div className="text-center pt-4 border-t">
              <a href="https://github.com/RhysMckay7777/lumina-lead-scraper" target="_blank"
                className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                📚 GitHub Docs →
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

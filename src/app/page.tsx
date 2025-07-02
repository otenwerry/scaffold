"use client";
import React, { useRef, useEffect, useState } from "react";
import { supabase } from '@/app/lib/supabaseClient';

export default function Home() {
  const [text, setText] = useState('');
  const [errMsg, setErrMsg] = useState<string|null>(null);
  //const [sentences,setSentences] =useState<string[]>([]);
  const [history, setHistory] = useState<{ sentence: string; wordCount: number }[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Call the word count API
    let wordCount = 0;
    try {
      const res = await fetch('/api/count', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence: text }),
      });
      if (!res.ok) throw new Error('Failed to count words');
      const data = await res.json();
      wordCount = data.word_count;
    } catch (err: any) {
      setErrMsg('Error counting words');
      return;
    }

    const { data, error } = await supabase
      .from('entries2')
      .insert([{ content: text }]);

    if (error) {
      setErrMsg(error.message);
    } else {
      setErrMsg(null);
      setHistory([...history, { sentence: text, wordCount }]);
      setText('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
      console.log('Saved:', data);
    }
  };

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    }
  };

  useEffect(() => {
    adjustHeight();
  }, []);

  return (
    <div className="min-h-screen flex items-start justify-center p-8 pt-56">
      <div className="w-full max-w-md text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-8 font-sans tracking-tight">
          Entropy Editor
        </h1>
        <form onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            placeholder="Enter text here..."
            rows={1}
            value={text}
            onChange={e => { setText(e.target.value); adjustHeight(); }}
            className="w-full px-4 py-3 text-lg border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none overflow-hidden"
          />
          <button
            type="submit"
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded transition duration-150 hover:scale-95"
          >
            Submit
          </button>
          {errMsg && (
            <div className="mt-2 text-red-600 text-sm font-medium">{errMsg}</div>
          )}
        </form>
        {history.length > 0 && (
          <div className="mt-8 text-left">
            <h2 className="text-lg font-semibold mb-2">History:</h2>
            <div className="space-y-2">
              {history.map((entry, idx) => (
                <div key={idx} className="p-4 bg-gray-100 rounded border border-gray-200">
                  <div>{entry.sentence}</div>
                  <div className="text-sm text-gray-600">Words: {entry.wordCount}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
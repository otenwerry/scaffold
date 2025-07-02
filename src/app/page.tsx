"use client";
import { useState, useRef, useEffect } from "react";
import { supabase } from "@/app/lib/supabaseClient";

// what's an interface?
interface Entry {
  content: string;
  entropy_score: number;
}

export default function Home() {
  const [text, setText] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [errMsg, setErrMsg] = useState<string|null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 1) Call your Python API to get the score
    const res = await fetch("/api/compute_entropy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text }),
    });
    const { entropy_score } = await res.json();

    // 2) Insert into Supabase, including the score
    const { data: insertedRows, error } = await supabase
      .from("entries2")
      .insert([{ content: text, entropy_score }])
      .select("*");

    if (error) {
      setErrMsg(error.message);
      return;
    }
    if (!insertedRows || insertedRows.length === 0) {
      setErrMsg("No row returned after insert");
      return;
    }

    // 3) Update local history state
    setEntries((prev) => [...prev, insertedRows[0]]);
    setText('');
    setErrMsg(null);
  };

  return (
    <div className="min-h-screen flex items-start justify-center p-8 pt-56">
      <div className="w-full max-w-md text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-8 font-sans tracking-tight">
          Entropy Editor
        </h1>
        <form onSubmit={handleSubmit} className="space-y-4">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="w-full border rounded p-2"
        placeholder="Enter text here…"
      />
      <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
        Submit
      </button>

      {errMsg && <p className="text-red-600">{errMsg}</p>}

      <h2 className="mt-6 font-bold">History:</h2>
      {entries.map((entry, i) => (
        <div
          key={i}
          className="p-4 mb-2 bg-gray-100 rounded border border-gray-200"
        >
          <p className="font-medium">{entry.content}</p>
          <p className="text-sm text-gray-600">
            {entry.entropy_score.toFixed(2)} bits/token
          </p>
        </div>
      ))}
    </form>
      </div>
    </div>
  );
    /*
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
        {sentences.length > 0 && (
          <div className="mt-8 text-left">
            <h2 className="text-lg font-semibold mb-2">History:</h2>
            <div className="space-y-2">
              {sentences.map((sentence, idx) => (
                <div key={idx} className="p-4 bg-gray-100 rounded border border-gray-200">
                  {sentence}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
    */
}

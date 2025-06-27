import type { NextApiRequest, NextApiResponse } from 'next';
import { supabase } from '../lib/supabaseClient';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).end();

  const { content } = req.body as { content: string };

  const { data, error } = await supabase
    .from('entries2')
    .insert([{ content}]);

  if (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }

  res.status(200).json({ entry: data![0] });
}
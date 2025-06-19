-- Create the text_compressions table
CREATE TABLE IF NOT EXISTS text_compressions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  original_text TEXT NOT NULL,
  original_bits_per_token DECIMAL(10,4) NOT NULL,
  original_total_bits DECIMAL(10,4) NOT NULL,
  simplified_text TEXT NOT NULL,
  simplified_bits_per_token DECIMAL(10,4) NOT NULL,
  simplified_total_bits DECIMAL(10,4) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create an index on created_at for better query performance
CREATE INDEX IF NOT EXISTS idx_text_compressions_created_at ON text_compressions(created_at DESC);

-- Enable Row Level Security (RLS) - for now, allow all operations
ALTER TABLE text_compressions ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations (for testing purposes)
CREATE POLICY "Allow all operations" ON text_compressions
  FOR ALL USING (true) WITH CHECK (true); 
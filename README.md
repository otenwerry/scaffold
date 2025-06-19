# Text Entropy Analyzer

A web application that analyzes text entropy using GPT-2 language model and provides simplified versions with reduced entropy.

## Features

- **Text Entropy Analysis**: Calculate bits per token using GPT-2 language model
- **Text Simplification**: Generate less wordy versions of input text
- **Comparison**: Compare original vs simplified text entropy
- **Data Storage**: Store all analyses in Supabase database
- **Real-time Processing**: Process text through Python backend

## Setup

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env.local` file in the root directory:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 3. Set up Supabase Database

Run the SQL commands in `supabase_setup.sql` in your Supabase SQL editor to create the required table.

### 4. Start the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## How It Works

1. **Input**: User enters text in the textarea
2. **Processing**: Text is sent to the API which:
   - Processes original text through `entropy.py` using GPT-2
   - Generates a simplified version by removing common words
   - Processes simplified text through `entropy.py`
   - Stores results in Supabase
3. **Output**: Displays both original and simplified text with their entropy metrics

## API Endpoints

- `POST /api/compress` - Process text and return entropy analysis

## Database Schema

The `text_compressions` table stores:
- Original text and its entropy metrics
- Simplified text and its entropy metrics
- Timestamp of analysis

## Technologies Used

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Backend**: Next.js API routes, Python (torch, transformers)
- **Database**: Supabase (PostgreSQL)
- **ML Model**: GPT-2 for entropy calculation

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

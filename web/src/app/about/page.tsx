import Header from "../../components/Header";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import Link from "next/link";

export default function About() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start h-screen px-4 pt-20 md:pt-25">
        <Card>
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">About</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
          <strong>What is Scaffold? </strong>Scaffold is a voice AI for knowledge work. It hears what you say, sees your screen, and responds out loud in real time.
          </CardContent>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
          <strong>Why we built this: </strong>AI <Link href="https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/" target="_blank" className="text-blue-500 hover:text-blue-700">slows down</Link> the average software engineer, and students are learning less every day. A good TA doesn&apos;t take the computer and start writing for you; they look over your shoulder and prod you along. In like manner, Scaffold keeps the thinking in your voice and inside your head.
          </CardContent>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
          Scaffold also helps you move faster than traditional chatbots. Instead of typing out a detailed prompt and parsing through long paragraphs, verbalize your thinking and immediately hear a concise answer.
          </CardContent>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
          Ultimately, we&apos;re trying to build the perfect AI experience for knowledge work. We want to automate away needless frustrations while remembering that some types of friction make you smarter and more productive in the long run. We want you to feel like you&apos;re in direct control of your work, but with a brilliant assistant to guide you. (If there&apos;s something your ideal assistant would do, <Link href="https://forms.gle/5MTK88AkJx8NLUVt8" target="_blank" className="text-blue-500 hover:text-blue-700">let us know</Link>!)
          </CardContent>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
            <strong>System requirements:</strong> Scaffold only works on Macs with Apple Silicon right now. Intel/Windows support is coming soon. <br /><br />
            <strong>Privacy: </strong>Scaffold only looks at your screen when you finish asking a question, and doesn&apos;t save your data. 
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
import Header from "../../components/Header";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import Link from "next/link";

export default function About() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start h-screen px-4 pt-20">
        <Card>
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">About</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          <strong>Why we built this: </strong>AI <Link href="https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/" target="_blank" className="text-blue-500 hover:text-blue-700">slows down</Link> the average software engineer and students are learning less every day.
          Scaffold helps you move faster than traditional chatbots. Instead of typing out a detailed prompt and parsing through long paragraphs, verbalize your thinking and immediately hear an answer.
          </CardContent>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          At the same time, Scaffold won&apos;t let you get ahead of yourself. No slop generation, no massive codebases you don&apos;t understand. A good TA doesn&apos;t take the computer and start writing for you; they look over your shoulder and prod you along. In like manner, Scaffold keeps the thinking in your voice and inside your head. 
          </CardContent>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
            <strong>System requirements:</strong> Scaffold only works on Macs with Apple Silicon right now. Intel/Windows support is coming soon. <br /><br />
            <strong>Privacy: </strong>Scaffold only looks at your screen when you finish asking a question, and doesn&apos;t save or share your data. 
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
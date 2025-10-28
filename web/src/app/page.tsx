import Header from "../components/Header";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="min-h-screen relative">
      <Header />
      
      <div className="wireframe-bg"></div>
      <div className="wireframe-grid"></div>
      <div className="wireframe-element"></div>
      <div className="wireframe-element"></div>
      <div className="wireframe-element"></div>
      
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="text-center space-y-8 max-w-4xl mx-auto">
          <h1 className="text-6xl md:text-8xl font-bold text-black leading-tight">
            Scaffold
          </h1>

          <p className="text-xl md:text-2xl text-black max-w-2xl mx-auto leading-relaxed">
            Stay in control while getting the most out of AI.
          </p>

          <p className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          AI slows down the average software engineer. Students are getting dumber every day.
          Scaffold helps you move faster than traditional chatbots. Instead of typing out a detailed prompt and parsing through long paragraphs, verbalize your thinking and immediately hear an answer.
          </p>
          
          <p className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          At the same time, Scaffold won’t let you get ahead of yourself. No slop generation, no massive codebases you don’t understand. A good TA doesn’t take the computer and start writing for you, they look over your shoulder and prod you along. In like manner, Scaffold keeps the thinking inside your head. 
          </p>
          <p className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-center">
          Move faster and keep thinking with Scaffold.
          </p>
          
          
          <div className="space-y-6 pt-8">
            <Button 
              asChild
              className="futuristic-button text-white text-lg px-8 py-4 h-auto"
            >
              <a href="/Tutor.dmg" download>
                Download
              </a>
            </Button>
            
            <p className="text-sm text-gray-600 max-w-md mx-auto">
              After installing, right-click the app and choose &quot;Open&quot;.
            </p>
          </div>
        </div>
      </main>

      
    </div>
  );
}

import Header from "../components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardTitle, CardContent, CardFooter, CardDescription } from "@/components/ui/card";
import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen relative">
      <Header />
      
      <div className="wireframe-bg"></div>
      
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <Card>
          <CardTitle className="text-4xl md:text-7xl font-bold text-black text-center flex flex-row items-center justify-center">
            <Image src="/bg_icon.png" alt="Scaffold" width={80} height={80} className="mr-5" />
            Scaffold
          </CardTitle>

          <CardContent className=" text-xl md:text-2xl text-black max-w-2xl mx-auto leading-relaxed">
            Stay in control while getting the most out of AI.
          </CardContent>

          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          AI slows down the average software engineer. Students are getting dumber every day.
          Scaffold helps you move faster than traditional chatbots. Instead of typing out a detailed prompt and parsing through long paragraphs, verbalize your thinking and immediately hear an answer.
          </CardContent>
          
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          At the same time, Scaffold won’t let you get ahead of yourself. No slop generation, no massive codebases you don’t understand. A good TA doesn’t take the computer and start writing for you, they look over your shoulder and prod you along. In like manner, Scaffold keeps the thinking inside your head. 
          </CardContent>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-center">
          Move faster and keep thinking with Scaffold.
          </CardContent>
          
          
          <CardFooter className="space-y-5 flex flex-col items-center justify-center">
            <Button 
              className="futuristic-button text-white text-lg px-8 py-4 h-auto"
            >
              <a href="/Tutor.dmg" download>
                Download
              </a>
            </Button>
            
            <CardDescription className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left italic">
              1. Once download is complete, open the installer by clicking on the downloaded file. <br />
              2. Drag Scaffold into the Applications folder next to it, as well as your Dock next to other apps. <br />
              3. Then, open System Settings and navigate to Privacy & Security in the side bar. <br />
              4. Add Scaffold to Accessibility, Input Monitoring, and Screen & System Audio Recording.
            </CardDescription>
          </CardFooter>
        </Card>
      </main>

      
    </div>
  );
}

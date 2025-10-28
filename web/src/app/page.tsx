import Header from "../components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardTitle, CardContent, CardFooter, CardDescription } from "@/components/ui/card";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen relative">
      <Header />
      
      <div className="wireframe-bg"></div>
      
      <main className="relative z-10 flex flex-col items-start justify-center min-h-screen px-4">
        <Card>
          <CardTitle className="text-5xl md:text-6xl font-bold text-[#2D2D2D] text-center flex flex-row items-center justify-center">
           Voice AI for knowledge work
          </CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          Scaffold hears what you say, sees your screen, and responds in real time
          </CardContent>
          <CardFooter className="space-y-5 flex flex-col items-center justify-center">
            <Button 
              className="futuristic-button text-white text-lg px-4 py-2 h-auto"
            >
              <a href="/Tutor.dmg" download>
                Try it out!!!!
              </a>
            </Button>
            
            <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
            Say hello at our <Link href="https://forms.gle/5MTK88AkJx8NLUVt8" target="_blank" className="text-blue-500 hover:text-blue-700">form</Link>! Feedback/bugs/questions are all welcome. 
            </CardContent>
          </CardFooter>
        </Card>
      </main>

      
    </div>
  );
}

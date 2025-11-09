import Header from "../components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen relative">
      <Header />
      
      <div className="wireframe-bg"></div>
      
      <main className="relative z-10 flex flex-col items-start justify-center min-h-screen px-4">
        <Card>
          <CardTitle className="text-5xl md:text-6xl font-bold text-[#2D2D2D] text-center flex flex-row items-center justify-center">
           Omniscient voice AI for thinking out loud
          </CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          Scaffold hears what you say, sees your screen, and responds verbally in real time
          </CardContent>
          <CardFooter className="space-y-5 flex flex-col items-center justify-center">
            <Button 
              className="futuristic-button text-white text-lg px-4 py-2 h-auto"
            >
              <a href="/get_started">
                Try it out
              </a>
            </Button>
          </CardFooter>
        </Card>
      </main>

      
    </div>
  );
}

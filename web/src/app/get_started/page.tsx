import Header from "../../components/Header";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Footer from "../../components/Footer";
import { CardDescription } from "@/components/ui/card";

export default function GetStarted() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start h-screen px-4 pt-20 md:pt-25">
        <Card className="justify-center items-center">
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">Get Started</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
            1. Click the Download button below <br />
            2. Once download is complete, open the installer by clicking on the downloaded file <br />
            3. Drag Scaffold into the Applications folder next to it, as well as your Dock <br />
            4. Then, open System Settings and navigate to Privacy & Security in the side bar <br />
            5. Add Scaffold to Accessibility, Input Monitoring, and Screen & System Audio Recording
          </CardContent>
          <Button className="futuristic-button text-white text-lg px-4 py-2 h-auto max-w-md text-center">
            <a href="https://github.com/otenwerry/scaffold/releases/download/v1.0.2/Scaffold.dmg" download>
              Download Scaffold
            </a>
          </Button>
        </Card>
      </main>
      <Footer />
    </div>
  );
}